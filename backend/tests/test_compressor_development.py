"""Critical study invariants: source controls, annotation consistency, clustering."""
import importlib
import json
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


def test_archive_reuse_rejects_changed_settings_and_excludes_capped_outputs(bench,tmp_path):
    runner=importlib.import_module('run_compressor_development')
    artifacts=importlib.import_module('compressor_artifacts')
    spec=dict(models={'m':'digest'},options={'seed':42},think=False)
    artifacts.save(tmp_path/'manifest.json',spec)
    replies=[dict(model='m',prompt_sha256='complete',response={'done':True,'response':'A'}),
             dict(model='m',prompt_sha256='capped',response={'done':True,'done_reason':'length','response':'A'}),
             dict(model='m',prompt_sha256='failed',response={'done':True,'generation_error':'timeout'})]
    (tmp_path/'answers.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in replies))
    manifest={**spec,'source_hashes':{name:artifacts.digest(tmp_path/name) for name in ['manifest.json','answers.jsonl']}}
    assert set(runner.verified_archive_cache(tmp_path,manifest))=={('m','complete')}
    with pytest.raises(ValueError,match='settings differ'):
        runner.verified_archive_cache(tmp_path,{**manifest,'options':{'seed':43}})
    (tmp_path/'answers.jsonl').write_text('')
    with pytest.raises(ValueError,match='checksum'):
        runner.verified_archive_cache(tmp_path,manifest)


def test_neural_pair_builder_uses_ordinal_order_and_only_question_span_text(bench):
    module=importlib.import_module('neural_student_campaign')
    texts,pairs=module.ordinal_pairs([dict(question='question',spans=['one','two','three'],teacher_order=[2,0,1],
        gold='SECRET_GOLD',options=['SECRET_OPTIONS'])])
    assert texts==[('question','one'),('question','two'),('question','three')]
    assert pairs==[(2,0),(2,1),(0,1)]
    with pytest.raises(ValueError,match='permutation'):
        module.ordinal_pairs([dict(question='q',spans=['one','two'],teacher_order=[1,1])])


@pytest.mark.parametrize('neural_addition',[False,True])
def test_native_analysis_keeps_capped_answer_and_missing_usage_in_denominator(bench,tmp_path,neural_addition):
    module=importlib.import_module('review_mistral_native')
    artifacts=importlib.import_module('compressor_artifacts')
    methods=['original','no_context']+[f'{method}@{rate}' for method in
        ['teacher_prefix','teacher_atomic','student_atomic','bm25_atomic','shuffled','llml2_strict','xprovence_strict']
        for rate in [.5,.33]]
    if neural_addition:methods+=['student_neural@0.5','student_neural@0.33']
    inputs=[dict(uid='one',passage_group='family-one',gold='A'),dict(uid='two',passage_group='family-two',gold='A')]
    path=tmp_path/'inputs.jsonl'
    path.write_text(''.join(json.dumps(row)+'\n' for row in inputs))
    answers=[];variants=[]
    for row in inputs:
        for method in methods:
            answers.append(dict(uid=row['uid'],method=method,content='A',usage=None,
                rendered_prompt_tokens=10 if method=='original' else 8,
                error='Output cap reached' if row['uid']=='one' and method=='student_atomic@0.5' else None))
            variants.append(dict(uid=row['uid'],method=method,text='Evidence',context_tokens=1,budget=2,
                original_context_tokens=4,compression_seconds=.001,historical_teacher_rank_seconds=0,budget_clipped=False))
    for name,rows in [('answers.jsonl',answers),('variants.jsonl',variants)]:
        (tmp_path/name).write_text(''.join(json.dumps(row)+'\n' for row in rows))
    artifacts.save(tmp_path/'manifest.json',dict(methods=methods,source_hashes={'inputs':artifacts.digest(path)},
        scope='synthetic plumbing only',tokenizer_scope='synthetic'))
    artifacts.save(tmp_path/'state.json',dict(status='complete',answers_sha256=artifacts.digest(tmp_path/'answers.jsonl'),
        variants_sha256=artifacts.digest(tmp_path/'variants.jsonl')))
    module.review(tmp_path,path)
    report=json.loads((tmp_path/'report.json').read_text())
    metric=report['metrics']['student_atomic@0.5']
    assert metric['n']==2 and metric['accuracy']==.5 and metric['invalid']==1
    assert metric['generation_seconds_mean'] is None and metric['usage_rows']==0
    assert metric['full_prompt_retention']==.8
    assert len(report['comparisons'])==(24 if neural_addition else 18)
    assert all(r['holm_p_all_comparisons']>=r['cluster_robust_p'] for r in report['comparisons'])
