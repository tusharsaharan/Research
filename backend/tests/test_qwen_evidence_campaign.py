"""Data leakage, source fidelity, failed generations and frozen-run safeguards."""
import importlib
import json
import time
from pathlib import Path

import pytest

from gateway.modules.m2_compressor.qwen_evidence import (
    pack_ranked,
    ranking_request,
    source_units,
    validate_ranking,
)


@pytest.fixture
def campaign(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
    return importlib.import_module('local_qwen_campaign')


@pytest.mark.parametrize('order', [[0, 0], [0, 2], [True, 0], [0], ['0', 1]])
def test_invalid_rank_ids_rejected(order):
    with pytest.raises(ValueError, match='complete permutation'):
        validate_ranking(json.dumps({'ranking': order}), 2)


def test_model_can_only_select_original_evidence():
    passage = 'Air travel scary ho sakta hai. Unknown fear understanding se kam hota hai.'
    units, prompt, _ = ranking_request(passage, 'Understanding kab help karta hai?')
    assert set(json.loads(prompt)) == {'question', 'spans'}
    assert json.loads(prompt)['spans'][1]['text'] == units[1]
    packed = pack_ranked(passage, units, [1, 0], 0.6, lambda t: len(t.split()))
    assert packed['text'] == units[1]
    assert packed['budget_met']
    with pytest.raises(ValueError, match='exact source'):
        pack_ranked(passage, ['Invented answer.', units[1]], [0, 1], 0.6, len)


def test_packing_restores_source_order_and_measures_newlines():
    passage = 'First span. Second span. Third span.'
    units, _, _ = ranking_request(passage, 'Which?')
    result = pack_ranked(passage, units, [2, 0, 1], 0.8, len)
    assert result['text'] == 'First span.\nThird span.'
    assert len(result['text']) <= result['target_tokens']


def test_oversized_span_has_explicit_clipping_flag():
    passage = 'One long sentence with more words than the budget.'
    units, _, _ = ranking_request(passage, 'Which?')
    result = pack_ranked(passage, units, [0], 0.2, lambda t: len(t.split()))
    assert result['detail']['budget_enforced']
    assert not result['detail']['evidence_feasible']
    assert result['text'] == 'One'


def test_person_initials_are_not_detached_from_their_actions():
    text = 'John F. Kennedy ko unhone advice di. Lyndon B. Johnson ke liye kaam kiya.'
    assert source_units(text) == ['John F. Kennedy ko unhone advice di.',
                                  'Lyndon B. Johnson ke liye kaam kiya.']


def test_quoted_clauses_remain_intact():
    text = '"Travel ke dauran window ko hamesha band rakho, lekin emergency mein darwaza khol sakte hain."'
    assert source_units(text) == [text]


def test_gold_is_never_rendered(campaign):
    row = dict(question='Question?', options=['one', 'two', 'three', 'four'], gold='SECRET')
    prompt = campaign.answer_prompt(row, 'Evidence')
    assert 'SECRET' not in prompt
    assert 'A) one' in prompt and 'D) four' in prompt


@pytest.mark.parametrize('response', [
    {'done': False, 'response': 'A'}, {'done': True, 'response': ''},
    {'done': True, 'response': 'A', 'thinking': 'reasoning'},
    {'done': True, 'response': 'A', 'done_reason': 'length'},
    {'done': True, 'response': 'A', 'prompt_eval_count': 8192},
])
def test_failed_or_truncated_answer_is_not_graded(campaign, response):
    class API:
        def json(self, *args):
            return response
    with pytest.raises(RuntimeError):
        campaign.checked_generate(API(), 'm', 'system', 'prompt', time.monotonic() + 500)


def test_time_cap_and_overlong_prompt_do_not_call_model(campaign):
    class API:
        def json(self, *args):
            pytest.fail('Should not call API')
    with pytest.raises(TimeoutError):
        campaign.checked_generate(API(), 'm', '', '', time.monotonic() + 1)
    with pytest.raises(ValueError, match='truncation'):
        campaign.checked_generate(API(), 'm', '', 'x' * 8192, time.monotonic() + 500)


def test_scaleup_keeps_invalid_raw_output_for_failure_in_denominator(campaign):
    class API:
        def json(self, *args):
            return dict(done=True, response='unfinished explanation', done_reason='length', prompt_eval_count=100)
    result = campaign.checked_generate(API(), 'm', 'system', 'prompt', time.monotonic() + 500,
                                       record_invalid=True)
    assert result['generation_error'] == 'Generation exhausted the output cap'
    assert result['response'] == 'unfinished explanation'


def test_gpu_receipt_rejects_cpu_only(campaign):
    class API:
        def json(self, *args):
            return {'models': [{'name': 'm', 'size_vram': 0}]}
    with pytest.raises(RuntimeError, match='GPU'):
        campaign.gpu_receipt(API(), 'm')


def test_partial_model_results_are_not_compared_and_duplicate_answers_fail(campaign, tmp_path):
    manifest = dict(models={'m': 'digest'}, methods=['original', 'bm25_strict@0.5'],
                    budget_scope='reference', inference='exploratory')
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    rows = [dict(uid=str(i), gold='A', context='Source') for i in range(2)]
    (tmp_path / 'inputs.jsonl').write_text('\n'.join(map(json.dumps, rows)))
    variant = dict(key='0|original', uid='0', method='original', budget_met=True, kept_ratio=1)
    (tmp_path / 'variants.jsonl').write_text(json.dumps(variant) + '\n')
    answer = dict(model='m', key='0|original', content='A', config=campaign.fingerprint(manifest),
                  prompt_tokens=20, response={})
    (tmp_path / 'answers.jsonl').write_text(json.dumps(answer) + '\n')
    campaign.report(tmp_path)
    result = json.loads((tmp_path / 'report.json').read_text())
    assert not result['complete']
    assert not result['comparisons']
    assert result['models']['m']['original']['n'] == 1
    (tmp_path / 'answers.jsonl').write_text((json.dumps(answer) + '\n') * 2)
    with pytest.raises(ValueError, match='Duplicate'):
        campaign.report(tmp_path)
