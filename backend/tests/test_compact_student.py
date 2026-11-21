"""Guard source-only scoring and rank metrics against silent measurement errors."""
import importlib
from pathlib import Path

import pytest

from gateway.modules.m2_compressor.student_ranker import FEATURES, rank_spans, span_features


def test_source_only_features_keep_numeric_values_distinct_and_do_not_mutate():
    spans = ['Flight 1234 landed.', 'Flight 1235 landed.']
    original = list(spans)
    model = dict(features=list(FEATURES), weights=[0, 1, 0, 0, 0, 0])
    assert rank_spans(spans, '1234', model) == [0, 1]
    assert spans == original
    assert span_features(spans, '1234')[0][1] == 1
    assert span_features(spans, '1234')[1][1] == 0


def test_checkpoint_schema_and_nonfinite_weights_are_rejected():
    with pytest.raises(ValueError, match='schema'):
        rank_spans(['Text'], 'Query', dict(features=['wrong'], weights=[1]))
    with pytest.raises(ValueError, match='weights'):
        rank_spans(['Text'], 'Query', dict(features=list(FEATURES), weights=[float('nan')]*len(FEATURES)))


def test_rank_correlation_uses_inverse_rank_positions(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    module = importlib.import_module('train_compact_student')
    # This permutation differs from its inverse; correlating raw ID lists is wrong.
    rows = [dict(teacher_order=[2, 0, 3, 1])]
    result = module.metrics(rows, lambda row: [2, 0, 3, 1])
    assert result['mean_spearman'] == pytest.approx(1)
    assert result['ndcg_at_3'] == pytest.approx(1)
    reversed_result = module.metrics(rows, lambda row: [1, 3, 0, 2])
    assert reversed_result['mean_spearman'] == pytest.approx(-1)
