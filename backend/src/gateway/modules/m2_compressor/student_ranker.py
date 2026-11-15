"""Opt-in compact lexical student. Inputs are question and source spans only."""
from __future__ import annotations

import math

from gateway.modules.m2_compressor.budgeted import _WORD, bm25_scores
from gateway.modules.m2_compressor.hinglish_evidence import _CAUSE_EVIDENCE, _CAUSE_QUERY, _terms

FEATURES = ('bm25_relative', 'query_coverage', 'trigram_overlap', 'length_share',
            'source_position', 'causal_match')


def span_features(spans: list[str], question: str) -> list[list[float]]:
    scores = bm25_scores(spans, question)
    maximum = max(scores, default=0.0) or 1.0
    query = _terms(question)
    query_grams = {w[i:i + 3] for w in query for i in range(len(w) - 2)}
    lengths = [len(_WORD.findall(span)) for span in spans]
    total_length = sum(lengths) or 1
    rows = []
    for i, span in enumerate(spans):
        terms = _terms(span)
        grams = {w[j:j + 3] for w in terms for j in range(len(w) - 2)}
        rows.append([scores[i] / maximum, len(query & terms) / max(1, len(query)),
                     len(query_grams & grams) / max(1, len(query_grams | grams)),
                     lengths[i] / total_length, i / max(1, len(spans) - 1),
                     float(bool(_CAUSE_QUERY.search(question)) and bool(_CAUSE_EVIDENCE.search(span)))])
    return rows


def rank_spans(spans: list[str], question: str, model: dict) -> list[int]:
    if model.get('features') != list(FEATURES):
        raise ValueError('Student feature schema mismatch')
    weights = model['weights']
    if len(weights) != len(FEATURES) or not all(math.isfinite(w) for w in weights):
        raise ValueError('Invalid student weights')
    scores = [sum(x * w for x, w in zip(row, weights, strict=True))
              for row in span_features(spans, question)]
    return sorted(range(len(spans)), key=lambda i: (-scores[i], i))
