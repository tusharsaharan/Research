import pytest

from gateway.modules.m2_compressor.budgeted import compress_bm25_budgeted
from gateway.modules.m2_compressor.document import bridge_document, compress_document, extract_document, unwrap_document


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


@pytest.mark.parametrize("compressor", [compress_document, extract_document, bridge_document])
def test_rate_one_is_identity_and_invalid_rates_are_rejected(compressor):
    text = '"Mars is red. Jupiter is large."'
    assert compressor(text, "Mars?", 1, count, Identity()).text == text
    with pytest.raises(ValueError):
        compressor(text, "Mars?", 0, count, Identity())


def test_bridge_keeps_linked_record_before_unrelated_lexical_matches():
    text = ('Aurora: Aurora was composed by Mina Vale. More details are unknown.\n'
            'Composer contest: The composer contest was held every winter.\n'
            'Mina Vale: Mina Vale was born in June 1940. She lived abroad.\n'
            'Other composer: The other composer was born in July 1930.')
    result = bridge_document(text, 'When was the composer of Aurora born?', 0.55, count, Identity())
    assert result.budget_met
    assert 'Aurora was composed by Mina Vale.' in result.text
    assert 'Mina Vale was born in June 1940.' in result.text
    assert 'composer contest' not in result.text


def test_bridge_retains_original_subject_lead_for_orphaned_fact():
    text = ('Town club: Town club was named after Eva. It plays at the fourth level.\n'
            'Eva: Eva was the national manager. She played for many years.\n'
            'Football: Football is a game played throughout the country with a round ball.')
    result = bridge_document(text, 'At what level does the club named after the manager play?',
                             0.7, count, Identity())
    assert result.budget_met
    assert 'Town club was named after Eva.' in result.text
    assert 'It plays at the fourth level.' in result.text
    assert 'Eva was the national manager.' in result.text


def test_bridge_untitled_prose_uses_same_extractive_result():
    text = 'Paris is in France. The Seine crosses Paris. Mars is very far away.'
    assert bridge_document(text, 'Paris?', 0.5, count, Identity()) == extract_document(
        text, 'Paris?', 0.5, count, Identity())
