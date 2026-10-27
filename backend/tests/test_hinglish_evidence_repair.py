"""Regression tests for v12 overgrouping and coverage-saturation underfilling."""
import pytest

from gateway.modules.m2_compressor.hinglish_evidence import (
    compress_evidence, evidence_spans, repaired_evidence_spans, repaired_protected_spans,
)


def count(text):
    return len(text.split())


def chunks(text):
    return [text[a:b] for a, b in repaired_evidence_spans(text)]


def test_doubled_quotes_do_not_protect_unquoted_narration():
    text = ('"""We will cut emissions,"" Hu said. He did not set a figure. '
            'Hu encouraged countries ""to avoid polluting first."" '
            'He added ""they should not take excessive obligations."""')
    parts = chunks(text)
    assert len(parts) == 4
    assert parts[1] == 'He did not set a figure.'
    assert parts[2] == 'Hu encouraged countries ""to avoid polluting first.""'
    assert ' '.join(parts) == text
    original = compress_evidence(text, 'What did Hu encourage countries to avoid?', 0.5, count)
    repaired = compress_evidence(text, 'What did Hu encourage countries to avoid?', 0.5, count, repair=True)
    assert original.text == ''  # historical v12 behavior remains reproducible
    assert 'to avoid polluting first.' in repaired.text
    assert repaired.budget_met


@pytest.mark.parametrize('quote', [
    '"Keep the first sentence. Keep the second, too."',
    '""Keep the first sentence. Keep the second, too.""',
    '"Keep the ""literal"" spelling. Preserve both sentences."',
    '“Keep the first sentence. Keep the second, too.”',
])
def test_normal_and_escaped_multi_sentence_quotations_stay_atomic(quote):
    text = f'Literal: {quote} Background facts follow. Last sentence.'
    assert chunks(text)[0] == f'Literal: {quote}'
    protected = repaired_protected_spans(text)
    a = text.index(quote)
    assert (a, a + len(quote)) in protected


def test_quotes_inside_code_do_not_swallow_surrounding_text():
    ticks = chr(96) * 3
    literal = ticks + 'python\nprint("""alpha. beta""")\n' + ticks
    text = f'Code is {literal}. Next sentence. Final sentence.'
    assert len(chunks(text)) == 3
    assert literal in chunks(text)[0]


def test_closing_quotes_and_encoding_markers_do_not_hide_boundaries():
    text = 'Hu ne kaha �pollution se bachna.� Unhone koi figure nahi diya. Mr. Reid ghar gaya.'
    assert chunks(text) == [
        'Hu ne kaha �pollution se bachna.�', 'Unhone koi figure nahi diya.', 'Mr. Reid ghar gaya.',
    ]


def test_pronoun_chains_become_separate_sentences_with_explicit_dependencies():
    text = 'Meena reviewed draft. She sent report. They read report.'
    assert len(evidence_spans(text)) == 1
    assert len(chunks(text)) == 3
    result = compress_evidence(text, 'Who sent report?', 0.4, count, repair=True, refill=True)
    assert result.text == 'She sent report.'
    assert result.dependencies_unresolved == 1
    assert result.budget_met


def test_refill_restores_available_antecedent_before_redundant_query_match():
    text = 'Meena reviewed draft. She sent report. Report details followed.'
    result = compress_evidence(text, 'sent report', 0.7, count, repair=True, refill=True)
    assert result.text == 'Meena reviewed draft.\nShe sent report.'
    assert result.dependencies_unresolved == 0
    assert result.refill_units == 1


def test_refill_does_not_stop_when_query_coverage_saturates():
    text = 'Reactor power was measured. Reactor power was confirmed. Background conditions stayed stable.'
    segmented = compress_evidence(text, 'Reactor power', 2 / 3, count, repair=True)
    refilled = compress_evidence(text, 'Reactor power', 2 / 3, count, repair=True, refill=True)
    assert segmented.text == 'Reactor power was measured.'
    assert refilled.text == 'Reactor power was measured.\nReactor power was confirmed.'
    assert refilled.actual_tokens == refilled.target_tokens
    assert refilled.refill_units == 1


def test_refill_measures_joined_cost_instead_of_adding_sentence_lengths():
    text = 'Alpha sentence. Alpha followup. Alpha evidence.'
    costs = {text: 10, '': 0, 'Alpha sentence.': 2, 'Alpha followup.': 2, 'Alpha evidence.': 6,
             'Alpha sentence.\nAlpha followup.': 7, 'Alpha sentence.\nAlpha evidence.': 4,
             'Alpha followup.\nAlpha evidence.': 8, 'Alpha sentence.\nAlpha followup.\nAlpha evidence.': 9}
    result = compress_evidence(text, 'Alpha', 0.5, costs.__getitem__, repair=True, refill=True)
    assert result.text == 'Alpha sentence.\nAlpha evidence.'
    assert result.actual_tokens == 4 and result.budget_met


def test_no_fit_does_not_cut_a_literal_or_rewrite_source():
    text = '"A deliberately long quoted sentence. Another long sentence inside the same quotation."'
    result = compress_evidence(text, 'quoted sentence', 0.2, count, repair=True, refill=True)
    assert result.text == '' and not result.evidence_feasible
    assert result.selection_reason == 'no_complete_unit_fits'


@pytest.mark.parametrize('refill', [False, True])
def test_source_offsets_and_budget_survive_quoted_hinglish(refill):
    import tiktoken
    enc = tiktoken.get_encoding('cl100k_base')
    measure = lambda text: len(enc.encode(text))
    text = '  Mr. Reid ne kaha ""gaadi chhoti thi.""  Police ko radar reading mushkil thi. Unhone speed kam ki.'
    for target in (0.15, 0.33, 0.5, 0.8):
        result = compress_evidence(text, 'Radar reading mushkil kyun thi?', target, measure, repair=True, refill=refill)
        assert result.text == '\n'.join(text[a:b] for a, b in result.source_spans)
        assert measure(result.text) == result.actual_tokens <= result.target_tokens


def test_refill_requires_explicit_repaired_method():
    with pytest.raises(ValueError, match='requires repaired'):
        compress_evidence('Text.', 'Question?', 0.5, count, refill=True)
