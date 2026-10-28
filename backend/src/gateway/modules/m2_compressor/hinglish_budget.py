"""Exploratory retrieval/clause ablations, separate from serving defaults.

Character features affect ranking only. All emitted evidence uses original
wording. Strict evaluation clipping is explicit and is NOT a safety guarantee.
"""
from __future__ import annotations

import math
import re

from gateway.modules.m2_compressor.budgeted import (
    _STOP, _WORD, bm25_scores, compress_bm25_budgeted, split_units,
)
from gateway.modules.m2_compressor.safety_span import detect_spans

_CLAUSE = re.compile(r"(?<=[;,])\s+|\s+(?=(?:but|however|whereas|although|lekin|magar|halanki)\b)", re.I)


def character_scores(units, question):
    """Fixed, training-free lexical + character-trigram relevance ablation."""
    def grams(text):
        words = [w for w in _WORD.findall(text.casefold()) if w not in _STOP and len(w) > 2]
        return {word[i:i + 3] for word in words for i in range(len(word) - 2)}

    lexical = bm25_scores(units, question)
    peak = max(lexical, default=0) or 1
    query = grams(question)
    scores = []
    for unit, score in zip(units, lexical, strict=True):
        features = grams(unit)
        similarity = len(query & features) / math.sqrt(max(1, len(query) * len(features)))
        scores.append(score / peak + 0.35 * similarity)
    return scores


def split_clauses(text):
    """Conservative surface clauses; protect quoted/code spans and short tails.

    This is a segmentation hypothesis, not a grammatical parser. Connectives
    stay with the following clause, and no words or punctuation are rewritten.
    """
    result = []
    for sentence in split_units(text):
        spans = detect_spans(sentence)
        start = 0
        for match in _CLAUSE.finditer(sentence):
            if any(match.start() < span.end and match.end() > span.start for span in spans):
                continue
            left, right = sentence[start:match.start()], sentence[match.end():]
            if len(_WORD.findall(left)) < 6 or len(_WORD.findall(right)) < 6:
                continue
            result.append(left.strip())
            start = match.end()
        result.append(sentence[start:].strip())
    return [unit for unit in result if unit]


def strict_prefix(text, budget, count):
    """Longest word-boundary prefix fitting the actual tokenizer budget.

    Count every examined candidate: token counts need not be monotonic. Empty
    output is allowed if no whole word fits. The caller records this clipping.
    """
    if count(text) <= budget:
        return text
    for match in reversed(list(re.finditer(r"\S+", text))):
        candidate = text[:match.end()].rstrip()
        if count(candidate) <= budget:
            return candidate
    return ""


def compress_ablation(passage, question, target, count, lingua, *, characters=False, clauses=False, ranker=None):
    return compress_bm25_budgeted(
        passage, question, target, count, lingua,
        sent_share=min(1.0, {0.5: 0.7, 0.33: 0.6}.get(target, target + 0.2)),
        ranker=ranker if ranker is not None else character_scores if characters else None,
        unit_splitter=split_clauses if clauses else None,
        preserve_units=clauses,
    )
