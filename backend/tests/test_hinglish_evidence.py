"""Evidence boundaries, retrieval diversity and measured cap regressions."""
import importlib
import json
from pathlib import Path

import pytest

from gateway.modules.m2_compressor.hinglish_evidence import (
    _coverage, compress_evidence, evidence_spans,
)


def count(text):
    return len(text.split())


def units(text):
    return [text[a:b] for a, b in evidence_spans(text)]


def test_abbreviated_names_and_causal_clause_are_indivisible():
    text = ('Mr. Reid ne gaadi tez chalayi. Black Beauty ke small size ki wajah se '
            'police ko Mr. Reid ki speed naapne mein difficulty hui. Police wapas gayi.')
    assert len(units(text)) == 3
    assert units(text)[1].endswith('difficulty hui.')
    assert all(unit != 'Mr.' for unit in units(text))


def test_comma_negation_and_contrast_are_not_cut_into_fragments():
    text = 'Science ek method hai. Halanki ye akela nahi hai, experiments aur observation bhi zaroori hain.'
    assert units(text) == [text]
    result = compress_evidence(text, 'Kya akela nahi hai?', 0.5, count)
    assert result.text == '' and result.budget_met
    assert not result.evidence_feasible
    assert result.selection_reason == 'no_complete_unit_fits'


def test_antecedent_dependency_closure_is_transitive():
    text = 'Ravi ne report likhi. Usne report bheji. Isliye result jaldi aaya. Meena ghar gayi.'
    assert units(text) == [text[:text.index(' Meena')], 'Meena ghar gayi.']


@pytest.mark.parametrize('literal', [
    '"Keep the first sentence. Keep this one, too."',
    '`first. second`', '```python\nx = 1.\ny = 2\n```', '[1, 2, 2, 3]',
])
def test_selected_literal_is_always_verbatim(literal):
    text = f'Literal {literal} ends here. Background facts follow later.'
    for start, end in evidence_spans(text):
        overlap = max(start, text.index(literal)) < min(end, text.index(literal) + len(literal))
        if overlap:
            assert literal in text[start:end]


def test_coverage_selects_complementary_evidence_instead_of_repeated_topic():
    text = 'Reactor power was measured. Reactor power was recorded. Cooling prevents dangerous failures.'
    question = 'Reactor power cooling failures'
    result = compress_evidence(text, question, 2 / 3, count)
    assert 'Cooling prevents dangerous failures.' in result.text
    assert sum(word in result.text for word in ('measured', 'recorded')) == 1
    assert result.budget_met
    assert result.text == '\n'.join(text[a:b] for a, b in result.source_spans)


def test_matching_variants_does_not_rewrite_output_or_merge_kya_kiya():
    text = 'Ravi ne kaam kiya. Meena ne kaam nahi kiya. Aman ghar gaya.'
    result = compress_evidence(text, 'Kisne kaam nahin kiya?', 0.5, count)
    assert result.text == 'Meena ne kaam nahi kiya.'
    features, _ = _coverage(['kiya', 'kya'], 'kiya')
    assert features == [[1.0], [0.0]]
    features, _ = _coverage(['1234', '1235', '124'], '1234')
    assert features == [[1.0], [0.0], [0.0]]


@pytest.mark.parametrize('question', ['Radar mushkil kyun tha?', 'Why was radar difficult?'])
def test_causal_questions_cover_explanations_in_both_languages(question):
    text = 'Radar mushkil tha. Car ke size ki wajah se radar reading mushkil thi. Police ghar gayi.'
    result = compress_evidence(text, question, 0.65, count)
    assert 'wajah se radar reading mushkil thi.' in result.text
    assert result.budget_met


def test_joined_token_cost_is_not_assumed_additive_or_monotonic():
    text = 'Alpha evidence. Beta evidence. Gamma evidence.'
    costs = {text: 10, '': 0, 'Alpha evidence.': 2, 'Beta evidence.': 2,
             'Gamma evidence.': 6, 'Alpha evidence.\nBeta evidence.': 7,
             'Alpha evidence.\nGamma evidence.': 4, 'Beta evidence.\nGamma evidence.': 8,
             'Alpha evidence.\nBeta evidence.\nGamma evidence.': 9}
    result = compress_evidence(text, 'Alpha Beta Gamma', 0.5, costs.__getitem__)
    assert result.text == 'Alpha evidence.\nGamma evidence.'
    assert result.actual_tokens == 4 and result.budget_met


@pytest.mark.parametrize('coverage', [True, False])
def test_exact_source_order_and_tiktoken_budget(coverage):
    import tiktoken
    enc = tiktoken.get_encoding('cl100k_base')
    text = ('Mr. Reid car chala rahe the. Black Beauty chhoti thi, isliye radar reading mushkil thi. '
            'Bridge purana tha. Police ne baad mein speed measure ki.')
    count_tokens = lambda value: len(enc.encode(value))
    for target in (0.01, 0.33, 0.5, 0.9):
        result = compress_evidence(text, 'Radar reading mushkil kyun thi?', target, count_tokens, coverage=coverage)
        assert result.actual_tokens == count_tokens(result.text) <= result.target_tokens
        assert result.source_spans == tuple(sorted(result.source_spans))
        assert result.text == '\n'.join(text[a:b] for a, b in result.source_spans)


def test_rate_one_returns_original_whitespace():
    text = '  Pehla sentence.\n\nDoosra sentence.  '
    assert compress_evidence(text, 'sentence', 1, count).text == text
    assert compress_evidence('', '', 0.5, count).evidence_feasible


@pytest.mark.parametrize('target', [0, -1, 1.01, float('nan'), float('inf')])
def test_invalid_target(target):
    with pytest.raises(ValueError):
        compress_evidence('Text.', 'Question?', target, count)


def test_pilot_records_opt_in_policy_without_changing_baselines(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    pilot = importlib.import_module('compressor_pilot')
    monkeypatch.setattr(pilot, 'BENCH', tmp_path)
    pilot.write_rows(tmp_path / 'longqa_squad/items.jsonl', [dict(
        id='example', context='Sentence one. Sentence two.', question='Which sentence?', answer='one')])
    out = tmp_path / 'pilot'
    pilot.prepare(1, out, methods=list(pilot.EVIDENCE_METHODS), datasets=['squad'])
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['evidence_policy']['retrieval_inputs'] == 'context and question only'
    assert set(pilot.EVIDENCE_METHODS).issubset(pilot.MODEL_FREE_METHODS)
    assert not set(pilot.EVIDENCE_METHODS) & set(pilot.DEFAULT_METHODS)
    assert not set(pilot.EVIDENCE_METHODS) & pilot.STRICT_METHODS  # no fragment clipping


@pytest.mark.parametrize('tamper', [None, 'missing', 'wrong_input', 'duplicate', 'source_changed'])
def test_audit_requires_exact_coverage_and_keeps_empty_results(monkeypatch, tmp_path, tamper):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    audit = importlib.import_module('hinglish_evidence_audit')
    inputs = tmp_path / 'inputs.jsonl'
    audit.write_rows(inputs, [dict(uid='example', item_id='example')])
    metadata = dict(shard='1/1', input_units=1, item_ids=[], methods=['candidate'], rates=[0.5, 0.33],
                    sources_sha256={str(inputs): audit.digest(inputs)}, answer_quality='pending')
    (tmp_path / 'metadata_1_1.json').write_text(json.dumps(metadata))
    records = [dict(uid='example', method='candidate', rate=rate, lang='hinglish', budget_met=True,
                    source_exact=True, text='', evidence_feasible=False, original_tokens=20,
                    actual_tokens=0, saved_original_count_matches=True) for rate in (0.5, 0.33)]
    if tamper == 'missing':
        records.pop()
    elif tamper == 'wrong_input':
        records[0]['uid'] = 'counterfeit'
    elif tamper == 'duplicate':
        records[0] = records[1]
    elif tamper == 'source_changed':
        inputs.write_text('{}\n')
    audit.write_rows(tmp_path / 'evidence_1_1.jsonl', records)
    if tamper:
        with pytest.raises(ValueError):
            audit.merge(tmp_path, 1)
    else:
        audit.merge(tmp_path, 1)
        report = json.loads((tmp_path / 'report.json').read_text())
        assert report['records'] == 2 and report['answer_quality'] == 'pending'
        assert all(g['n'] == g['empty_outputs'] == g['infeasible_evidence'] == 1
                   for g in report['groups'].values())
