"""Opt-in BM25 hybrid with measured budgets and checked preservation.

Historical hybrid settings/results are deliberately separate. A budget is a
best-effort constraint: an indivisible protected span can make it infeasible.
Callers must inspect ``budget_met`` instead of treating the requested rate as
the achieved rate. The question belongs outside the compressed passage.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from gateway.modules.m2_compressor.guarded import _guard_words, _restore_numbers
from gateway.modules.m2_compressor.llmlingua2 import MAX_FORCE_MARKERS
from gateway.modules.m2_compressor.safety_span import detect_spans, mask, reinject

_BOUNDARY = re.compile(r"(?<=[.!?।])\s+|\n[ \t]*\n(?:[ \t]*\n)*|\n(?=[ \t]*[^\n:]{1,80}:[ \t]+\S)")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_STOP = set("a an the of to in is was and or ke ki ka ko se mein me hai hain tha thi par what who which".split())


@dataclass(frozen=True)
class BudgetedCompression:
    text: str
    target_tokens: int
    actual_tokens: int
    budget_met: bool
    selected_units: int


def split_units(text: str) -> list[str]:
    """Split sentences, blank paragraphs and titled records; keep soft wraps."""
    spans = detect_spans(text)
    out, start = [], 0
    for match in _BOUNDARY.finditer(text):
        if any(match.start() < span.end and match.end() > span.start for span in spans):
            continue
        unit = text[start:match.start()].strip()
        if unit:
            out.append(unit)
        start = match.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def bm25_scores(units: list[str], question: str) -> list[float]:
    docs = [_WORD.findall(unit.casefold()) for unit in units]
    query = set(_WORD.findall(question.casefold())) - _STOP
    n = len(docs)
    avg = sum(map(len, docs)) / max(1, n)
    df = Counter(word for doc in docs for word in set(doc))
    scores = []
    for doc in docs:
        tf = Counter(doc)
        scores.append(sum(
            math.log(1 + (n - df[word] + 0.5) / (df[word] + 0.5))
            * tf[word] * 2.2 / (tf[word] + 1.2 * (0.25 + 0.75 * len(doc) / max(1, avg)))
            for word in query if word in tf
        ))
    return scores


def _occurrences(text: str, word: str) -> int:
    return len(re.findall(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text, re.IGNORECASE))


def compress_checked(text: str, question: str, rate: float, lingua) -> str:
    """Fail closed on missing guards, markers or shared question terms.

    Forcing strings is advisory in LLMLingua; verify the actual output,
    including repeated negations. Never truncate a protected span to fit.
    """
    masked, spans = mask(text)
    markers = [f"[[PS{i}]]" for i in range(len(spans))]
    query = set(_WORD.findall(question.casefold())) - _STOP
    shared = {word for word in _WORD.findall(text) if len(word) > 2 and word.casefold() in query}
    required = sorted(set(_guard_words(text)) | shared)
    if len(markers) + len(required) > MAX_FORCE_MARKERS:
        return text
    got = lingua.compress_masked([masked], [markers], rate=rate, extra_force=required)[0]
    if not got:
        return text
    if re.findall(r"\[\[PS\d+\]\]", got, re.IGNORECASE) != markers:
        return text
    final, ok = reinject(got, spans)
    if not ok:
        return text
    final = _restore_numbers(text, final)
    if any(_occurrences(final, word) != _occurrences(text, word) for word in required):
        return text
    return final


def compress_bm25_budgeted(
    passage: str,
    question: str,
    target: float,
    count: Callable[[str], int],
    lingua,
    *,
    sent_share: float | None = None,
    max_passes: int = 7,
    ranker=None,
    unit_splitter=None,
    preserve_units: bool = False,
) -> BudgetedCompression:
    """Retrieve, keep the best evidence intact where feasible, then thin.

    Count reconstructed candidates with the caller's downstream tokenizer.
    Search several keep rates, retaining the fullest candidate that fits.
    If guards prevent a fit, remove the lowest-ranked *whole* unit and retry.
    At least the highest-ranked unit survives, even for impossible budgets.
    """
    if not math.isfinite(target) or not 0 < target <= 1:
        raise ValueError("target must be in (0, 1]")
    if max_passes < 2:
        raise ValueError("max_passes must be at least 2")
    share = min(1.0, target + 0.2) if sent_share is None else sent_share
    if not math.isfinite(share) or not target <= share <= 1:
        raise ValueError("sent_share must be between target and 1")
    original_n = count(passage)
    budget = max(1, math.floor(target * original_n)) if original_n else 0
    if not passage.strip() or target == 1 or original_n <= budget:
        return BudgetedCompression(passage, budget, original_n, original_n <= budget, len(split_units(passage)))
    units = (unit_splitter or split_units)(passage)
    scores = (ranker or bm25_scores)(units, question)
    order = sorted(range(len(units)), key=lambda i: (-scores[i], i))

    def joined(indices):
        # Explicit boundaries preserve paragraph/title structure after retrieval.
        return "\n".join(units[i] for i in sorted(indices))

    if preserve_units:
        packed = []
        for index in order:
            if count(joined([*packed, index])) <= budget:
                packed.append(index)
        output = joined(packed) if packed else units[order[0]]
        actual = count(output)
        return BudgetedCompression(output, budget, actual, actual <= budget, len(packed) or 1)

    selected: list[int] = []
    for index in order:
        if not selected or count(joined([*selected, index])) <= math.floor(share * original_n):
            selected.append(index)

    best_over = (passage, original_n, len(units))
    while selected:
        coarse = joined(selected)
        if count(coarse) <= budget:
            return BudgetedCompression(coarse, budget, count(coarse), True, len(selected))
        candidates = [coarse]
        anchor = selected[0]
        preserve_anchor = count(units[anchor]) <= budget and len(selected) > 1
        mutable = [i for i in sorted(selected) if not preserve_anchor or i != anchor]
        source = joined(mutable)
        # Measure the desired rate and the minimum, then refine the fit/overshoot
        # bracket. Keep every candidate: model output need not be monotonic.
        fixed_n = count(units[anchor]) if preserve_anchor else 0
        initial = min(0.95, max(0.05, (budget - fixed_n) / max(1, count(source))))

        def evaluate(rate):
            if preserve_anchor:
                # Keep the compressed block on the same side of the anchor.
                # Compress before/after separately when the anchor is internal.
                before = [i for i in mutable if i < anchor]
                after = [i for i in mutable if i > anchor]
                if before and after:
                    left = compress_checked(joined(before), question, rate, lingua)
                    right = compress_checked(joined(after), question, rate, lingua)
                    candidate = "\n".join((left, units[anchor], right))
                else:
                    fine = compress_checked(source, question, rate, lingua)
                    candidate = "\n".join((fine, units[anchor]) if before else (units[anchor], fine))
            else:
                candidate = compress_checked(source, question, rate, lingua)
            candidates.append(candidate)
            return count(candidate)

        observations = [(initial, evaluate(initial))]
        if initial != 0.05:
            observations.append((0.05, evaluate(0.05)))
        safe = [(rate, n) for rate, n in observations if n <= budget]
        if safe:
            low, low_n = max(safe)
            upper = [(rate, n) for rate, n in observations if rate > low and n > budget]
            high, high_n = min(upper) if upper else (1.0, count(coarse))
            for _ in range(max_passes - len(observations)):
                if any(n == budget for _, n in observations):
                    break
                fraction = (budget - low_n) / max(1, high_n - low_n)
                fraction = min(0.8, max(0.2, fraction))
                rate = min(0.95, low + fraction * (high - low))
                if rate <= low or rate >= high:
                    break
                n = evaluate(rate)
                observations.append((rate, n))
                if n <= budget:
                    low, low_n = rate, n
                else:
                    high, high_n = rate, n
        measured = [(text, count(text)) for text in candidates]
        fits = [(text, n) for text, n in measured if n <= budget and text.strip()]
        if fits:
            text, n = max(fits, key=lambda item: item[1])
            return BudgetedCompression(text, budget, n, True, len(selected))
        text, n = min(measured, key=lambda item: item[1])
        if n < best_over[1]:
            best_over = text, n, len(selected)
        selected.pop()  # least relevant selected unit; never raw token truncation
    text, n, n_units = best_over
    return BudgetedCompression(text, budget, n, False, n_units)
