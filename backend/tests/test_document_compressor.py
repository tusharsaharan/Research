import pytest

from gateway.modules.m2_compressor.budgeted import compress_bm25_budgeted
from gateway.modules.m2_compressor.document import compress_document, extract_document, unwrap_document


def count(text):
    return len(text.split())


class Identity:
    def compress_masked(self, texts, *args, **kwargs):
        return texts


@pytest.mark.parametrize(("text", "expected"), [
    ('"Alpha. Beta."', 'Alpha. Beta.'),
    ('"Alpha says ""literal""."', 'Alpha says ""literal"".'),
    ('"Alpha" and "Beta"', '"Alpha" and "Beta"'),
    ('"Alpha ""', '"Alpha ""'),
    ('“Alpha. Beta.”', 'Alpha. Beta.'),
    ('“Alpha” and “Beta”', '“Alpha” and “Beta”'),
    ('Alpha "literal" Beta.', 'Alpha "literal" Beta.'),
])
def test_only_unambiguous_document_envelopes_are_removed(text, expected):
    assert unwrap_document(text) == expected


def test_document_mode_relaxes_outer_envelope_but_generic_protection_stays():
    text = '"Mars is red. Jupiter is large."'
    generic = compress_bm25_budgeted(text, "What color is Mars?", 0.5, count, Identity())
    document = compress_document(text, "What color is Mars?", 0.5, count, Identity())
    assert generic.text == text and not generic.budget_met
    assert document.budget_met and "Mars is red." in document.text


def test_extractive_keeps_entire_evidence_and_source_order_without_thinning():
    text = 'Paris is in France. The Seine crosses Paris. Mars is very far away.'
    result = extract_document(text, "What crosses Paris?", 0.7, count, Identity())
    assert result.budget_met
    assert result.text == 'Paris is in France.\nThe Seine crosses Paris.'


def test_extractive_reports_unmet_protected_unit_budget():
    text = 'The key is `important literal value that cannot be split`.'
    result = extract_document(text, "What is the key?", 0.2, count, Identity())
    assert not result.budget_met
    assert '`important literal value that cannot be split`' in result.text


@pytest.mark.parametrize("compressor", [compress_document, extract_document])
def test_rate_one_is_identity_and_invalid_rates_are_rejected(compressor):
    text = '"Mars is red. Jupiter is large."'
    assert compressor(text, "Mars?", 1, count, Identity()).text == text
    with pytest.raises(ValueError):
        compressor(text, "Mars?", 0, count, Identity())
