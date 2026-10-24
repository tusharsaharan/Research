"""Guard against misleading uncertainty and historical parser conclusions."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
    return importlib.import_module("hinglish_research_audit")


def test_repeated_questions_are_resampled_as_passage_clusters(audit):
    result = audit.paired_interval([1, -1, 1, -1], ["p", "p", "q", "q"])
    assert result == dict(n=4, n_passages=2, delta=0.0, ci95=[0.0, 0.0])


def test_estimate_weights_questions_not_equal_passage_means(audit):
    result = audit.paired_interval([1, 0, 0], ["p", "q", "q"])
    assert result["delta"] == pytest.approx(1 / 3)
    assert result["ci95"] == [0.0, 1.0]
    assert result == audit.paired_interval([1, 0, 0], ["p", "q", "q"])


def test_empty_subset_is_not_zero_effect(audit):
    assert audit.paired_interval([], []) == dict(n=0, n_passages=0, delta=None, ci95=None)
    with pytest.raises(ValueError):
        audit.paired_interval([], ["p"])


def test_passage_key_ignores_layout_but_preserves_words(audit):
    assert audit.passage_key("Same\n passage ") == audit.passage_key("Same passage")
    assert audit.passage_key("Not the same passage") != audit.passage_key("Same passage")


@pytest.mark.parametrize("content, expected", [
    ("Reasoning.\n\nB####", "B"),
    ("Reasoning.\n#### C", "C"),
    ("A#### followed by another possibility", None),
    ("B####\nThe final answer is uncertain.", None),
])
def test_historical_sensitivity_only_recovers_final_reverse_marker(audit, content, expected):
    assert audit.historical_letter_sensitivity(content) == expected
