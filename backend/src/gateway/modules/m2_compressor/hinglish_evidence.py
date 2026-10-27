"""Exploratory question-coverage packing for Roman-script Hinglish.

Only ranking uses character matches; output consists of original source spans.
Surface dependency rules are conservative heuristics, not a semantic guarantee.
No gold answer, options, language label, model or fitted parameters are inputs.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable

from gateway.modules.m2_compressor.budgeted import BudgetedCompression, _STOP, _WORD, bm25_scores
from gateway.modules.m2_compressor.safety_span import detect_spans

_BOUNDARY = re.compile(r"(?<=[.!?।])\s+|\n[ \t]*\n(?:[ \t]*\n)*")
_TITLE = re.compile(r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|Shri|Smt)|\b[A-Z])\.$", re.I)
_DEPENDENT = re.compile(
    r"^(?:but|however|whereas|although|therefore|because|instead|yet|"
    r"lekin|magar|halanki|halaanki|isliye|kyunki|kyonki|balki|"
    r"he|she|it|they|this|these|those|such|"
    r"ye|yeh|woh|vo|usne|unhone|iska|iski|iske|uska|uski|uske)\b", re.I,
)
_QUERY_STOP = _STOP | set(
    "passage paragraph according text following described given based "
    "does do did can could would should are were be been being "
    "kis kise kiska kiski kiske kaun kya kab kahan kyun kyu kyon "
    "mein mai liye ne aur ya bhi hi ek ye yeh woh vo yahan wahan "
    "kar karna karne karta karti karte raha rahi rahe hota hoti hote "
    "se is us iss oss tak toh to apne apni apna hain hai tha the thi".split()
)
_NEGATIONS = {"nahi", "nahin", "nhi", "naheen"}
_CAUSE_QUERY = re.compile(r"\b(?:why|kyun|kyu|kyon|reason|cause)\b|\b(?:kis|kya)\s+(?:wajah|karan|kaaran)\b", re.I)
_CAUSE_EVIDENCE = re.compile(
    r"\b(?:because|due to|owing to|as a result|therefore|hence|"
    r"wajah|karan|kaaran|kyunki|kyonki|isliye)\b", re.I,
)


@dataclass(frozen=True)
class EvidenceCompression(BudgetedCompression):
    source_spans: tuple[tuple[int, int], ...]
    evidence_feasible: bool
    selection_reason: str


def evidence_spans(text: str) -> list[tuple[int, int]]:
    """Keep honorifics, literals, comma clauses and leading dependencies intact.

    A leading connective/pronoun attaches to its preceding sentence, including
    transitive chains. This deliberately risks underfilling a tight budget in
    preference to outputting a known dangling fragment. Internal coreference
    and implicit relations are not resolved by these surface rules.
    """
    protected = detect_spans(text)
    spans, start = [], 0
    for match in _BOUNDARY.finditer(text):
        if any(match.start() < sp.end and match.end() > sp.start for sp in protected):
            continue
        if _TITLE.search(text[start:match.start()]):
            continue
        if text[start:match.start()].strip():
            spans.append((start, match.start()))
        start = match.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    result = []
    for start, end in spans:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if result and _DEPENDENT.match(text[start:end]):
            result[-1] = (result[-1][0], end)
        else:
            result.append((start, end))
    return result


def _terms(text: str) -> set[str]:
    # A narrowly scoped negation spelling equivalence, never a text rewrite.
    return {"nahi" if word in _NEGATIONS else word
            for word in _WORD.findall(text.casefold()) if word not in _QUERY_STOP}


def _grams(word: str) -> set[str]:
    return {word[i:i + 3] for i in range(len(word) - 2)}


def _coverage(units: list[str], question: str) -> tuple[list[list[float]], list[float]]:
    terms = [_terms(unit) for unit in units]
    query = sorted(_terms(question))
    features = []
    causal_query = bool(_CAUSE_QUERY.search(question))
    for unit, words in zip(units, terms, strict=True):
        row = []
        for word in query:
            if word in words:
                row.append(1.0)
            elif word == "nahi" or word.isdigit() or len(word) < 4:
                row.append(0.0)  # never fuzzy-match negation or a numeric value
            else:
                grams = _grams(word)
                similarities = [len(grams & _grams(other)) / max(1, len(grams | _grams(other)))
                                for other in words if len(other) >= 4 and other != "nahi"]
                row.append(0.35 * max(similarities, default=0.0))
        if causal_query:
            # Shared English/Hinglish relation feature; no answer-word lexicon.
            row.append(float(bool(_CAUSE_EVIDENCE.search(unit))))
        features.append(row)
    weights = []
    for j in range(len(query) + int(causal_query)):
        df = sum(row[j] > 0 for row in features)
        weights.append(math.log(1 + (len(units) - df + 0.5) / (df + 0.5)))
    return features, weights


def compress_evidence(
    passage: str, question: str, target: float, count: Callable[[str], int], *, coverage: bool = True,
) -> EvidenceCompression:
    """Pack intact evidence using diminishing-return question coverage.

    The BM25 control uses the identical segmentation, measured packing search
    and output policy, with additive lexical scores instead of query coverage.
    Three deterministic greedy starts (empty, best value, best density) reduce
    single-anchor lock-in. This is a heuristic, not an optimal knapsack solver.
    Every proposed joined output is counted; token lengths need not be additive
    or monotonic. If no unit fits, return an explicit empty-evidence failure,
    never an over-budget passage or a word-prefix fragment.
    """
    if not math.isfinite(target) or not 0 < target <= 1:
        raise ValueError("target must be in (0, 1]")
    original_n = count(passage)
    budget = max(1, math.floor(target * original_n)) if original_n else 0
    spans = evidence_spans(passage)
    units = [passage[start:end] for start, end in spans]

    def result(indices, reason):
        ordered = sorted(indices)
        output = "\n".join(units[i] for i in ordered)
        actual = count(output)
        return EvidenceCompression(output, budget, actual, actual <= budget, len(ordered),
                                   tuple(spans[i] for i in ordered), bool(ordered) or not passage.strip(), reason)

    if target == 1 or original_n <= budget:
        return EvidenceCompression(passage, budget, original_n, original_n <= budget, len(spans),
                                   tuple(spans), bool(spans) or not passage.strip(), "original_fits")
    if not spans:
        return result((), "empty_input")
    if coverage:
        features, weights = _coverage(units, question)

        def value(indices):
            return sum(weight * max((features[i][j] for i in indices), default=0.0)
                       for j, weight in enumerate(weights))
    else:
        lexical = bm25_scores(units, question)

        def value(indices):
            return sum(lexical[i] for i in indices)

    lengths = {}

    def length(indices):
        key = tuple(sorted(indices))
        if key not in lengths:
            lengths[key] = count("\n".join(units[i] for i in key))
        return lengths[key]

    feasible = [i for i in range(len(units)) if length((i,)) <= budget]
    if not feasible:
        return result((), "no_complete_unit_fits")
    if max(value((i,)) for i in feasible) <= 0:
        # No relevance evidence: source-order packing, explicitly reported.
        packed = []
        for i in range(len(units)):
            if length([*packed, i]) <= budget:
                packed.append(i)
        return result(packed, "no_query_overlap")

    best_value = max(feasible, key=lambda i: (value((i,)), -length((i,)), -i))
    best_density = max(feasible, key=lambda i: (value((i,)) / max(1, length((i,))), -i))
    candidates = []
    for seed in ((), (best_value,), (best_density,)):
        selected = set(seed)
        while True:
            current_value, current_length = value(selected), length(selected)
            choices = []
            for i in range(len(units)):
                if i in selected:
                    continue
                trial = selected | {i}
                trial_length = length(trial)
                gain = value(trial) - current_value
                if trial_length <= budget and gain > 1e-12:
                    choices.append((gain / max(1, trial_length - current_length), gain, -i, i))
            if not choices:
                break
            selected.add(max(choices)[-1])
        candidates.append(selected)
    selected = max(candidates, key=lambda ids: (value(ids), -length(ids), tuple(-i for i in sorted(ids))))
    return result(selected, "query_coverage" if coverage else "bm25_units")
