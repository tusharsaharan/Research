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
_SENTENCE_END = re.compile(r"""(?<=[.!?।])["”'’)\]\uFFFD]*(?P<gap>\s+)|(?P<paragraph>\n[ \t]*\n+)""")
_QUOTE_RUN = re.compile(r'"+|[“”]')


@dataclass(frozen=True)
class EvidenceCompression(BudgetedCompression):
    source_spans: tuple[tuple[int, int], ...]
    evidence_feasible: bool
    selection_reason: str
    dependencies_unresolved: int = 0
    refill_units: int = 0


def repaired_protected_spans(text: str) -> list[tuple[int, int]]:
    """Parse quote runs without treating text between doubled quotes as quoted.

    A shadow string preserves offsets while detecting other protected literals.
    ASCII runs are one delimiter; doubled quotes inside a single-quoted-width
    ASCII quotation remain escapes. Unclosed quotations protect the remainder.
    The actual source text is never decoded or normalized.
    """
    shadow = re.sub(r'["“”]', ' ', text)
    protected = [(sp.start, sp.end) for sp in detect_spans(shadow) if sp.kind != 'quoted']
    opened = None
    for match in _QUOTE_RUN.finditer(text):
        if any(a <= match.start() < b for a, b in protected):
            continue
        mark = match.group()
        if opened is None:
            if mark != '”':
                opened = (match.start(), mark)
        else:
            start, opening = opened
            if opening == '“':
                closes = mark == '”'
            else:
                closes = mark.startswith('"') and not (opening == '"' and len(mark) == 2)
            if closes:
                protected.append((start, match.end()))
                opened = None
    if opened is not None:
        protected.append((opened[0], len(text)))
    return sorted(protected)


def repaired_evidence_spans(text: str) -> list[tuple[int, int]]:
    """Sentence boundaries after closing quotes; no permanent pronoun chains.

    Literal spans and honorifics remain indivisible. Dependencies are handled
    during packing and counted when unresolved, rather than merging an entire
    pronoun chain before the budget is known.
    """
    protected = repaired_protected_spans(text)
    spans, start = [], 0
    for match in _SENTENCE_END.finditer(text):
        cut = match.start('gap') if match.group('gap') is not None else match.start()
        if any(a < cut < b for a, b in protected):
            continue
        prefix = text[start:cut].rstrip('"”’)]\uFFFD')
        if _TITLE.search(prefix):
            continue
        if text[start:cut].strip():
            spans.append((start, cut))
        start = match.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return [(a + len(text[a:b]) - len(text[a:b].lstrip()), b - len(text[a:b]) + len(text[a:b].rstrip()))
            for a, b in spans]


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
    repair: bool = False, refill: bool = False,
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
    if refill and not repair:
        raise ValueError("refill requires repaired segmentation")
    original_n = count(passage)
    budget = max(1, math.floor(target * original_n)) if original_n else 0
    spans = repaired_evidence_spans(passage) if repair else evidence_spans(passage)
    units = [passage[start:end] for start, end in spans]
    dependent = {i for i, unit in enumerate(units) if i and _DEPENDENT.match(unit)} if repair else set()

    def unresolved(indices):
        return sum(i in indices and i - 1 not in indices for i in dependent)

    def result(indices, reason, added=0):
        ordered = sorted(indices)
        output = "\n".join(units[i] for i in ordered)
        actual = count(output)
        return EvidenceCompression(output, budget, actual, actual <= budget, len(ordered),
                                   tuple(spans[i] for i in ordered), bool(ordered) or not passage.strip(), reason,
                                   unresolved(ordered), added)

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
    if not refill:
        return result(selected, "query_coverage" if coverage else "bm25_units")

    # Coverage saturates even when another sentence supplies an antecedent or
    # corroborating fact. Spend remaining space on intact supporting sentences.
    # No raw-prefix clipping: a genuinely oversized single literal stays infeasible.
    lexical = bm25_scores(units, question)
    completed = []
    for seed in candidates:
        packed, added = set(seed), 0
        while True:
            choices = []
            for i in range(len(units)):
                if i in packed:
                    continue
                trial = packed | {i}
                trial_length = length(trial)
                adjacent = i - 1 in packed or i + 1 in packed
                supporting = value((i,)) > 0 or lexical[i] > 0 or adjacent
                if trial_length > budget or not supporting:
                    continue
                restores = unresolved(packed) - unresolved(trial)
                gain = value(trial) - value(packed)
                choices.append((restores, gain, lexical[i], adjacent, trial_length, -i, i))
            if not choices:
                break
            packed.add(max(choices)[-1])
            added += 1
        completed.append((packed, added))
    selected, added = max(completed, key=lambda pair: (
        value(pair[0]), -unresolved(pair[0]), length(pair[0]), tuple(-i for i in sorted(pair[0])),
    ))
    return result(selected, "query_coverage_refill", added)
