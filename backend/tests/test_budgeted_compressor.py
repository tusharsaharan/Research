"""Deterministic preservation and downstream-budget checks; no model is loaded."""

from __future__ import annotations

import pytest

from gateway.modules.m2_compressor import budgeted


class FakeLingua:
    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def compress_masked(self, texts, markers, *, rate, extra_force):
        self.calls.append((texts, markers, rate, extra_force))
        if callable(self.response):
            return [self.response(texts[0], rate)]
        return [texts[0] if self.response is None else self.response]


def word_count(text):
    return len(text.split())


@pytest.mark.parametrize(
    "source, question, candidate",
    [
        ("The treatment is not effective.", "", "The treatment is effective."),
        ("Not tired and not cold.", "", "Not tired cold."),
        ("Please carry 7kg carefully.", "", "Carry carefully."),
        ("The telescope stayed outside overnight.", "Where is the telescope?", "Stayed outside."),
        ('"Alice" met "Bob" outside.', "", "[[PS0]] met outside."),
        ('"Alice" met "Bob" outside.', "", "[[PS1]] met [[PS0]]."),
        ('"Alice" met "Bob" outside.', "", "[[PS0]] met [[PS0]] and [[PS1]]."),
        ('"Alice" met "Bob" outside.', "", "[[PS0]] met [[PS1]] and [[PS2]]."),
    ],
    ids=["negation", "repeated-negation", "number-unit", "question-term", "missing-marker",
         "reordered-markers", "duplicate-marker", "foreign-marker"],
)
def test_checked_rejects_changed_guards_or_markers(source, question, candidate):
    lingua = FakeLingua(candidate)
    assert budgeted.compress_checked(source, question, 0.5, lingua) == source
    assert len(lingua.calls) == 1


def test_checked_accepts_compression_with_all_guards_and_question_terms():
    source = 'Please do not move 7kg from "shelf A" today.'
    lingua = FakeLingua("do not move 7kg from [[PS0]].")
    result = budgeted.compress_checked(source, "Where should I move the crate?", 0.5, lingua)
    assert result == 'do not move 7kg from "shelf A".'
    assert {"not", "move", "7kg"} <= set(lingua.calls[0][3])
    assert lingua.calls[0][1] == [["[[PS0]]"]]


@pytest.mark.parametrize("protected_spans, expected_calls", [(89, 1), (90, 0)])
def test_checked_combines_marker_and_guard_capacity(protected_spans, expected_calls):
    source = "not " + " ".join('"literal"' for _ in range(protected_spans))
    lingua = FakeLingua()
    assert budgeted.compress_checked(source, "", 0.5, lingua) == source
    assert len(lingua.calls) == expected_calls


def test_checked_refuses_more_than_ninety_distinct_number_unit_guards():
    source = " ".join(f"item{i}kg" for i in range(91))
    lingua = FakeLingua()
    assert budgeted.compress_checked(source, "", 0.5, lingua) == source
    assert not lingua.calls


def test_split_units_keeps_protected_internal_boundaries():
    quote = '"Keep this. It matters."'
    code = "```python\nvalue = 7\nprint(value)\n```"
    source = f"First sentence.\n{quote}\n{code}\nList [1, 2, 3].\nEnd."
    assert budgeted.split_units(source) == ["First sentence.", quote, code, "List [1, 2, 3].", "End."]


def test_budget_recounts_joined_text_with_nonadditive_tokenizer(monkeypatch):
    def count(text):
        return word_count(text) + 2 * text.count("\n")

    monkeypatch.setattr(budgeted, "bm25_scores", lambda units, question: [3, 2, 1])
    source = "Alpha one two. Beta three four. Gamma five six."
    lingua = FakeLingua("Beta.")
    result = budgeted.compress_bm25_budgeted(source, "", 0.6, count, lingua, sent_share=1, max_passes=2)
    assert result.target_tokens == 5
    # Alpha plus even the one-word Beta costs six tokens after joining.
    assert result.text == "Alpha one two."
    assert result.actual_tokens == count(result.text) == 3
    assert result.budget_met
    assert result.selected_units == 1
    assert lingua.calls


def test_budget_retains_fullest_measured_candidate_that_fits():
    source = "alpha beta gamma delta epsilon zeta eta theta"

    def response(text, rate):
        return " ".join(text.split()[:5 if rate >= 0.4 else 4 if rate >= 0.1 else 2])

    result = budgeted.compress_bm25_budgeted(source, "", 0.5, word_count, FakeLingua(response), max_passes=3)
    assert result.text == "alpha beta gamma delta"
    assert result.actual_tokens == result.target_tokens == 4
    assert result.budget_met


def test_infeasible_protected_unit_survives_and_reports_budget_miss():
    source = '"do not touch the only protected instruction"'
    lingua = FakeLingua("[[PS0]]")
    result = budgeted.compress_bm25_budgeted(source, "", 0.25, word_count, lingua, max_passes=2)
    assert result.text == source
    assert result.actual_tokens == word_count(source)
    assert result.actual_tokens > result.target_tokens
    assert not result.budget_met
    assert result.selected_units == 1


def test_internal_anchor_and_surrounding_context_keep_source_order(monkeypatch):
    monkeypatch.setattr(budgeted, "bm25_scores", lambda units, question: [1, 3, 2])
    source = "Before loose filler alpha. Anchor evidence stays. After loose filler beta."

    def response(text, rate):
        assert not ("Before" in text and "After" in text)
        return "Before." if "Before" in text else "After."

    lingua = FakeLingua(response)
    result = budgeted.compress_bm25_budgeted(
        source, "evidence", 0.6, word_count, lingua, sent_share=1, max_passes=2,
    )
    assert result.text == "Before.\nAnchor evidence stays.\nAfter."
    assert result.budget_met
    assert result.actual_tokens == word_count(result.text) == 5
    assert result.selected_units == 3
    assert all("Anchor" not in call[0][0] for call in lingua.calls)


@pytest.mark.parametrize("source, target", [("", 0.5), (" \n\t", 0.5), ("A few words.", 1.0)])
def test_identity_and_empty_inputs_do_not_invoke_model(source, target):
    lingua = FakeLingua()
    result = budgeted.compress_bm25_budgeted(source, "", target, word_count, lingua)
    assert result.text == source
    assert result.actual_tokens == word_count(source)
    assert result.budget_met
    assert not lingua.calls


@pytest.mark.parametrize("target", [0, -0.1, 1.01, float("nan"), float("inf"), -float("inf")])
def test_invalid_target_rejected_before_model_call(target):
    lingua = FakeLingua()
    with pytest.raises(ValueError, match="target"):
        budgeted.compress_bm25_budgeted("A passage.", "", target, word_count, lingua)
    assert not lingua.calls


@pytest.mark.parametrize("sent_share", [0.4, 1.1, float("nan"), float("inf")])
def test_invalid_sentence_share_rejected(sent_share):
    with pytest.raises(ValueError, match="sent_share"):
        budgeted.compress_bm25_budgeted("A passage.", "", 0.5, word_count, FakeLingua(), sent_share=sent_share)


@pytest.mark.parametrize("max_passes", [0, 1])
def test_insufficient_rate_search_passes_rejected(max_passes):
    with pytest.raises(ValueError, match="max_passes"):
        budgeted.compress_bm25_budgeted("A passage.", "", 0.5, word_count, FakeLingua(), max_passes=max_passes)
