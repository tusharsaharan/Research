"""Semantic retrieval inputs and packing invariants; no model downloads."""
import math

import pytest

from gateway.modules.m2_compressor.hinglish_budget import compress_ablation, strict_prefix
from gateway.modules.m2_compressor.semantic_ranker import SemanticRanker, reciprocal_ranks


class FakeEncoder:
    def __init__(self, scores):
        self.values = scores
        self.calls = []

    def scores(self, units, question):
        self.calls.append((units, question))
        return self.values


def test_semantic_ranking_selects_original_evidence_without_lexical_overlap():
    units = ['Police officers were measuring speed nearby.', 'Gaadi chhoti thi isliye radar pakad nahi saka.']
    question = 'Why was the car not detected?'
    encoder = FakeEncoder([0.1, 0.9])
    count = lambda text: len(text.split())
    result = compress_ablation(' '.join(units), question, 0.6, count, None,
                              clauses=True, ranker=SemanticRanker(encoder))
    assert result.text == units[1]
    assert count(strict_prefix(result.text, result.target_tokens, count)) <= result.target_tokens
    assert encoder.calls == [(units, question)]


def test_fusion_ties_are_permutation_invariant():
    # Equal semantic scores must not favor whichever unit appeared first.
    units = ['The answer concerns radar detection.', 'The town is very far away.']
    a = SemanticRanker(FakeEncoder([0.5, 0.5]), fused=True)(units, 'radar detection')
    b = SemanticRanker(FakeEncoder([0.5, 0.5]), fused=True)(units[::-1], 'radar detection')
    assert a == b[::-1]
    assert a[0] > a[1]
    assert reciprocal_ranks([2, 2, 1])[0] == reciprocal_ranks([2, 2, 1])[1]


@pytest.mark.parametrize('scores', [[0.5], [math.nan, 0.5], [math.inf, 0.5]])
def test_invalid_encoder_results_fail_loudly(scores):
    with pytest.raises(ValueError, match='invalid scores'):
        SemanticRanker(FakeEncoder(scores))(['first', 'second'], 'question')


def test_empty_query_or_units_does_not_call_encoder():
    encoder = FakeEncoder([])
    ranker = SemanticRanker(encoder)
    assert ranker([], 'question') == []
    assert ranker(['a sentence'], '  ') == [0]
    assert not encoder.calls
