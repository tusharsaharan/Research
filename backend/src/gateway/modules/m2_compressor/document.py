"""Opt-in document variants; generic literal-span protection stays unchanged.

A whole-document quotation envelope is packaging in this mode. Internal quotes,
code, identifiers, negations and numbers retain the normal preservation checks.
The question and answer choices must be supplied outside the passage.
"""
from __future__ import annotations

import math
import re

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


def bridge_document(passage, question, target, count, lingua):
    """Retrieve titled records and their explicit cross-references as sentences.

    Record leads identify the subject of otherwise orphaned facts. A reference
    from the best matching record to another source title receives priority over
    unrelated lexical matches. This is a label-free retrieval heuristic, not a
    guarantee that every reasoning step is present. Untitled prose uses the
    existing extractive candidate.
    """
    budget = _budget(passage, target, count)
    text = unwrap_document(passage)
    titles = re.findall(r"(?m)^([^\n:]{1,80}):[ \t]+(?=\S)", text)
    if target == 1 or len(titles) < 2:
        return extract_document(passage, question, target, count, lingua)
    units = split_units(text)
    records, owner = {}, {}
    active = None
    for index, unit in enumerate(units):
        title = next((t for t in titles if unit.startswith(t + ":")), None)
        if title is not None:
            active = index
            records[active] = dict(title=title, indices=[])
        if active is not None:
            records[active]["indices"].append(index)
            owner[index] = active
    if len(records) < 2:
        return extract_document(passage, question, target, count, lingua)
    scores = bm25_scores(units, question)
    ranked = sorted(range(len(units)), key=lambda i: (-scores[i], i))
    anchor = ranked[0]
    named = [start for start, record in records.items()
             if re.search(r"(?<!\w)" + re.escape(record["title"]) + r"(?!\w)", question, re.I)]
    if named:
        start = max(named, key=lambda start: (len(records[start]["title"].split()),
                                              max(scores[i] for i in records[start]["indices"]), -start))
        anchor = max(records[start]["indices"], key=lambda i: (scores[i], -i))
    anchor_record = owner.get(anchor)
    priority = [anchor]
    if anchor_record is not None:
        body = "\n".join(units[i] for i in records[anchor_record]["indices"])
        links = [start for start, record in records.items() if start != anchor_record
                 and re.search(r"(?<!\w)" + re.escape(record["title"]) + r"(?!\w)", body, re.I)]
        best = {start: max(records[start]["indices"], key=lambda i: (scores[i], -i)) for start in links}
        priority += [best[start] for start in sorted(links, key=lambda start: (-scores[best[start]], start))]
    priority += [index for index in ranked if index not in priority]
    selected = set()

    def joined(indices):
        return "\n".join(units[i] for i in sorted(indices))

    for index in priority:
        # Include the original lead rather than inventing an entity annotation.
        bundle = {index, owner.get(index, index)}
        candidate = selected | bundle
        if count(joined(candidate)) <= budget:
            selected = candidate
        elif not selected:
            core = joined(bundle)
            fitted = compress_bm25_budgeted(core, question, min(1, budget / max(1, count(core))),
                                           count, lingua, sent_share=1.0)
            # A fitted lead is not a whole sentence; avoid attaching more facts
            # to that potentially shortened antecedent.
            return BudgetedCompression(fitted.text, budget, fitted.actual_tokens,
                                       fitted.actual_tokens <= budget, fitted.selected_units)
    output = joined(selected)
    actual = count(output)
    return BudgetedCompression(output, budget, actual, actual <= budget, len(selected))


def structured_document(passage, question, target, count, lingua):
    """Opt-in structural policy; no dataset labels or reference answers.

    Titled multi-record context uses explicit links and original record leads.
    Other prose uses measured hybrid compression to fill the budget more fully
    than whole-sentence packing. This policy is exploratory, not a quality gate.
    """
    text = unwrap_document(passage)
    titles = re.findall(r"(?m)^([^\n:]{1,80}):[ \t]+(?=\S)", text)
    compressor = bridge_document if len(titles) >= 2 else compress_document
    return compressor(passage, question, target, count, lingua)
