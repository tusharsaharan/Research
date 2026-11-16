"""Analyze all native-token Mistral development cells, retaining failed rows."""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from compressor_artifacts import digest, records, save
from eval_final_paper import clustered_difference
from grade import extract_letter


def review(data,inputs_path):
    spec=json.loads((data/'manifest.json').read_text())
    state=json.loads((data/'state.json').read_text())
    if state['status']!='complete':raise ValueError('Native campaign is not complete')
    if digest(data/'answers.jsonl')!=state['answers_sha256'] or digest(data/'variants.jsonl')!=state['variants_sha256']:
        raise ValueError('Native campaign output hash mismatch')
    if digest(inputs_path)!=spec['source_hashes']['inputs']:raise ValueError('Input source hash mismatch')
    inputs={r['uid']:r for r in records(inputs_path)}
    expected={(uid,method) for uid in inputs for method in spec['methods']}
    variants={};answers={};metrics={}
    for row in records(data/'variants.jsonl'):
        key=row['uid'],row['method']
        if key in variants:raise ValueError('Duplicate native variant')
        if row['context_tokens']>row['budget']:raise ValueError('Native context cap violation')
        variants[key]=row
    for row in records(data/'answers.jsonl'):
        key=row['uid'],row['method']
        if key in answers:raise ValueError('Duplicate native answer')
        parsed=None if row['error'] else extract_letter(row['content'])
        row['correct']=int(parsed==inputs[row['uid']]['gold']);row['parsed']=parsed
        answers[key]=row
    if set(answers)!=expected or set(variants)!=expected:raise ValueError('Incomplete paired native cells')
    for method in spec['methods']:
        selected=[answers[(uid,method)] for uid in inputs]
        texts=[variants[(uid,method)] for uid in inputs]
        usage=[a['usage'] for a in selected if a['usage']]
        metrics[method]=dict(n=len(selected),accuracy=sum(r['correct'] for r in selected)/len(selected),
            invalid=sum(r['parsed'] is None for r in selected),errors=sum(bool(r['error']) for r in selected),
            empty_contexts=sum(not r['text'] for r in texts),clipped=sum(r['budget_clipped'] for r in texts),
            context_retention=sum(r['context_tokens'] for r in texts)/sum(r['original_context_tokens'] for r in texts),
            compression_seconds_mean=float(np.mean([r['compression_seconds'] for r in texts])),
            historical_teacher_rank_seconds_mean=float(np.mean([r['historical_teacher_rank_seconds'] for r in texts])),
            generation_seconds_mean=float(np.mean([r['generation_seconds'] for r in usage])) if usage else None,
            prompt_tokens_mean=float(np.mean([r['prompt_tokens'] for r in usage])) if usage else None,
            answer_tokens_mean=float(np.mean([r['output_tokens'] for r in usage])) if usage else None,
            usage_rows=len(usage),exact_prompt_reuse_rows=sum(r.get('exact_prompt_reuse',False) for r in selected),
            actual_unique_generation_seconds=sum(r['usage']['generation_seconds'] for r in selected
                if r.get('usage') and not r.get('exact_prompt_reuse',False)))
        prompt_counts=[r.get('rendered_prompt_tokens') for r in selected]
        original_counts=[answers[(uid,'original')].get('rendered_prompt_tokens') for uid in inputs]
        metrics[method]['full_prompt_retention']=(sum(prompt_counts)/sum(original_counts)
            if all(v is not None for v in prompt_counts+original_counts) else None)
        measured=metrics[method]
        measured['compression_plus_generation_seconds_mean']=None if measured['generation_seconds_mean'] is None else (
            measured['compression_seconds_mean']+measured['historical_teacher_rank_seconds_mean']+measured['generation_seconds_mean'])
    paired={uid:dict(group=row['passage_group'],correct={method:answers[(uid,method)]['correct'] for method in spec['methods']})
            for uid,row in inputs.items()}
    comparisons=[]
    for rate in [.5,.33]:
        for candidate in [f'student_atomic@{rate}',f'teacher_atomic@{rate}',f'teacher_prefix@{rate}']:
            for baseline in [f'bm25_atomic@{rate}',f'llml2_strict@{rate}',f'xprovence_strict@{rate}']:
                comparisons.append(dict(candidate=candidate,baseline=baseline,**clustered_difference(paired,candidate,baseline)))
    maximum=0
    for i,index in enumerate(sorted(range(len(comparisons)),key=lambda k:comparisons[k]['cluster_robust_p'])):
        maximum=max(maximum,min(1,(len(comparisons)-i)*comparisons[index]['cluster_robust_p']))
        comparisons[index]['holm_p_all_comparisons']=maximum
    examples=[]
    for uid,row in inputs.items():
        if len(examples)==3:break
        if answers[(uid,'student_atomic@0.5')]['correct']!=answers[(uid,'bm25_atomic@0.5')]['correct']:
            examples.append(dict(source=row,student=variants[(uid,'student_atomic@0.5')],
                bm25=variants[(uid,'bm25_atomic@0.5')],student_answer=answers[(uid,'student_atomic@0.5')],
                bm25_answer=answers[(uid,'bm25_atomic@0.5')]))
    report=dict(status='complete',scope=spec['scope'],tokenizer_scope=spec['tokenizer_scope'],
        records=len(answers),metrics=metrics,comparisons=comparisons,examples=examples,
        manifest_sha256=digest(data/'manifest.json'),analysis_sha256=digest(Path(__file__)),
        limitations=['Exposed development data; no independent human translation validation.',
            'Teacher imitation candidate selected without a hyperparameter search; no sealed confirmation.',
            'Timing is local component accounting, not a deployment throughput benchmark; teacher rank cost is historical.',
            'Percentile intervals are exploratory; p-values adjusted over all 18 disclosed comparisons.'])
    save(data/'report.json',report)
    lines=['# Independent-family native-token development results','',spec['scope'],'',
        '| Method | Accuracy | Invalid | Context kept | Empty contexts |','|---|---:|---:|---:|---:|']
    for method,m in metrics.items():
        lines.append(f"| {method} | {m['accuracy']:.2%} | {m['invalid']} | {m['context_retention']:.2%} | {m['empty_contexts']} |")
    lines+=['','All failures remain in denominators. Full paired results, timings and multiplicity handling are in report.json.']
    (data/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='complete',answers=len(answers),comparisons=len(comparisons))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True);a=p.parse_args();review(a.data,a.inputs)
