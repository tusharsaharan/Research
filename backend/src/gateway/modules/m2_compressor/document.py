"""Opt-in document variants; generic literal-span protection stays unchanged.

A whole-document quotation envelope is packaging in this mode. Internal quotes,
code, identifiers, negations and numbers retain the normal preservation checks.
The question and answer choices must be supplied outside the passage.
"""
from __future__ import annotations

import math

from gateway.modules.m2_compressor.budgeted import (
    BudgetedCompression,
    bm25_scores,
    compress_bm25_budgeted,
    split_units,
)


def unwrap_document(text: str) -> str:
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        index = 1
        while index < len(stripped) - 1:
            if stripped[index] == '"':
                if index + 1 >= len(stripped) - 1 or stripped[index + 1] != '"':
                    return text  # separate quotations, not one document envelope
                index += 1
            index += 1
        return stripped[1:-1]
    if len(stripped) >= 2 and (stripped[0], stripped[-1]) == ("“", "”"):
        if not any(mark in stripped[1:-1] for mark in ("“", "”")):
            return stripped[1:-1]
    return text


def _budget(passage, target, count):
    if not math.isfinite(target) or not 0 < target <= 1:
        raise ValueError("target must be in (0, 1]")
    n = count(passage)
    return max(1, math.floor(target * n)) if n else 0


def compress_document(passage, question, target, count, lingua):
    """Measured hybrid, with only the outer document envelope removed."""
    budget = _budget(passage, target, count)
    if target == 1:
        return BudgetedCompression(passage, budget, count(passage), True, len(split_units(passage)))
    result = compress_bm25_budgeted(unwrap_document(passage), question, target, count, lingua)
    return BudgetedCompression(result.text, budget, result.actual_tokens, result.actual_tokens <= budget,
                               result.selected_units)


def extract_document(passage, question, target, count, lingua):
    """Pack intact relevant sentences; thin only an oversized top evidence unit.

    This avoids deleting relational details from every selected sentence in
    multi-hop contexts. It makes no completeness or answer-quality guarantee.
    """
    budget = _budget(passage, target, count)
    text = unwrap_document(passage)
    if target == 1:
        return BudgetedCompression(passage, budget, count(passage), count(passage) <= budget,
                                   len(split_units(passage)))
    if not text.strip():
        return BudgetedCompression(text, budget, count(text), count(text) <= budget, 0)
    units = split_units(text)
    scores = bm25_scores(units, question)
    order = sorted(range(len(units)), key=lambda i: (-scores[i], i))
    selected = {}

    def joined(candidate):
        return "\n".join(candidate[i] for i in sorted(candidate))

    for index in order:
        candidate = dict(selected)
        candidate[index] = units[index]
        if count(joined(candidate)) <= budget:
            selected = candidate
        elif not selected:
            rate = min(1.0, budget / max(1, count(units[index])))
            fitted = compress_bm25_budgeted(units[index], question, rate, count, lingua, sent_share=1.0)
            selected[index] = fitted.text
            if count(joined(selected)) > budget:
                break  # preserve the best evidence and report an unmet budget
    output = joined(selected)
    actual = count(output)
    return BudgetedCompression(output, budget, actual, actual <= budget, len(selected))
