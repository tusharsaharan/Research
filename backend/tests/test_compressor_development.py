"""Critical study invariants: source controls, annotation consistency, clustering."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def bench(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts/bench'))


def test_shuffle_is_source_only_deterministic_and_measured(bench):
    controls=importlib.import_module('controls')
    qwen=importlib.import_module('gateway.modules.m2_compressor.qwen_evidence')
    passage='First source sentence. Second source sentence. Third source sentence.'
    count=lambda text:len(text.split())
    a=controls.shuffled_context(passage,'id',.7,count)
    b=controls.shuffled_context(passage,'id',.7,count)
    assert a==b
    units=qwen.source_units(passage)
    assert a['text']=='\n'.join(units[i] for i in a['selected_ids'])
    assert a['actual_tokens']<=a['target_tokens']


def test_annotation_supported_option_must_match_same_gold(bench):
    review=importlib.import_module('gpu_annotation_review')
    value=dict(same_meaning='yes',answerable_same_gold='yes',natural_hinglish=3,
        english_supported_option='B',hinglish_supported_option='C',critical_translation_issue=False,notes='Mismatch')
    with pytest.raises(ValueError,match='contradicts'):
        review.validate(value,'B')


def test_clustered_statistics_refuse_one_source_family(bench):
    analysis=importlib.import_module('eval_final_paper')
    rows={'a':dict(group='one',correct={'candidate':1,'baseline':0}),
          'b':dict(group='one',correct={'candidate':0,'baseline':1})}
    with pytest.raises(ValueError,match='two independent'):
        analysis.clustered_difference(rows,'candidate','baseline')
