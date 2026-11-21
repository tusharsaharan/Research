"""Analyze complete paired compressor runs without dropping invalid replies.

Current accepted protocol is exposed development, not a sealed confirmation.
Produces traceable JSON/Markdown; no comparisons are made on partial coverage.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import t

from compressor_artifacts import digest, records, save
from grade import extract_letter


def clustered_difference(rows, candidate, baseline, seed=20261116):
    groups=defaultdict(lambda:[0,0])
    for uid,row in rows.items():
        group=groups[row['group']]
        group[0]+=row['correct'][candidate]-row['correct'][baseline];group[1]+=1
    delta,size=np.asarray(list(groups.values()),dtype=float).T
    if len(size)<2:raise ValueError('At least two independent source groups required')
    observed=delta.sum()/size.sum()
    rng=np.random.default_rng(seed); draws=[]
    for _ in range(50):
        indices=rng.integers(0,len(size),size=(200,len(size)))
        draws.extend((delta[indices].sum(axis=1)/size[indices].sum(axis=1)).tolist())
    se=np.sqrt(len(size)/(len(size)-1)*((delta-observed*size)**2).sum())/size.sum()
    p=float(2*t.sf(abs(observed/se),df=len(size)-1)) if se else float(observed==0)
    return dict(delta=observed,ci95=np.quantile(draws,[.025,.975]).tolist(),
                source_groups=len(size),questions=int(size.sum()),cluster_robust_p=p,
                interpretation='Paired source-passage bootstrap; exploratory and unadjusted interval.')


def evaluate(data, output):
    manifest=json.loads((data/'manifest.json').read_text())
    for name,expected in manifest['files'].items():
        if digest(data/name)!=expected:raise ValueError('Frozen input changed: '+name)
    inputs={r['uid']:r for r in records(data/'inputs.jsonl')}
    expected={(model,uid,method) for model in manifest['models'] for uid in inputs for method in manifest['methods']}
    seen={};grouped=defaultdict(list)
    for answer in records(data/'answers.jsonl'):
        key=answer['model'],answer['uid'],answer['method']
        if key not in expected or key in seen:raise ValueError('Unexpected or duplicate answer identity')
        if answer['manifest_sha256']!=digest(data/'manifest.json'):raise ValueError('Answer manifest mismatch')
        if answer['model_digest']!=manifest['models'][answer['model']]:raise ValueError('Answer model digest mismatch')
        letter=None if answer['error'] else extract_letter(answer['content'])
        answer['parsed']=letter;answer['correct']=int(letter==inputs[answer['uid']]['gold'])
        seen[key]=answer;grouped[(answer['model'],answer['method'])].append(answer)
    if set(seen)!=expected:
        save(output/'report.json',dict(status='incomplete',expected=len(expected),available=len(seen),comparisons=[],
             note='No method comparisons until complete paired coverage; missing rows are not silently deleted.'))
        return dict(status='incomplete',available=len(seen),expected=len(expected))
    metrics={};comparisons=[]
    for (model,method),answers in grouped.items():
        prompt_usage=[a['response']['prompt_eval_count'] for a in answers
                      if a['response'] and 'prompt_eval_count' in a['response']]
        answer_usage=[a['response']['eval_count'] for a in answers
                      if a['response'] and 'eval_count' in a['response']]
        metrics[model+'|'+method]=dict(n=len(answers),accuracy=sum(a['correct'] for a in answers)/len(answers),
            invalid=sum(a['parsed'] is None for a in answers),errors=sum(bool(a['error']) for a in answers),
            mean_prompt_tokens=float(np.mean(prompt_usage)) if prompt_usage else None,
            mean_answer_tokens=float(np.mean(answer_usage)) if answer_usage else None,
            rows_with_prompt_usage=len(prompt_usage),rows_with_answer_usage=len(answer_usage))
    for model in manifest['models']:
        paired={uid:dict(group=row['passage_group'],correct={method:seen[(model,uid,method)]['correct']
                for method in manifest['methods']}) for uid,row in inputs.items()}
        for rate in [.5,.33]:
            baseline=f'bm25_atomic@{rate}'
            for candidate in [f'student_atomic@{rate}',f'teacher_atomic@{rate}',f'teacher_prefix@{rate}']:
                comparisons.append(dict(model=model,candidate=candidate,baseline=baseline,
                                        **clustered_difference(paired,candidate,baseline)))
    # Holm adjustment across all disclosed comparison p-values, not selected cells.
    largest=0.0
    for i,index in enumerate(sorted(range(len(comparisons)),key=lambda i:comparisons[i]['cluster_robust_p'])):
        largest=max(largest,min(1,(len(comparisons)-i)*comparisons[index]['cluster_robust_p']))
        comparisons[index]['holm_p_all_comparisons']=largest
    report=dict(status='complete',scope=manifest['scope'],metrics=metrics,comparisons=comparisons,
        sources={'manifest':digest(data/'manifest.json'),'answers':digest(data/'answers.jsonl')},
        analysis_sha256=digest(Path(__file__)),budget_scope=manifest['tokenizer'],
        note='Development evidence only. Answer quality does not certify semantic preservation; no automatic serving promotion.')
    save(output/'report.json',report)
    lines=['# Compressor development results','',''+report['scope'],'',
           '| Model / method | Accuracy | Invalid | Errors |','|---|---:|---:|---:|']
    for key,m in sorted(metrics.items()):lines.append(f"| {key} | {100*m['accuracy']:.2f}% | {m['invalid']} | {m['errors']} |")
    lines+=['','All invalid and capped replies remain in denominators. See report.json for paired clustered intervals and multiplicity-adjusted tests.']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return dict(status='complete',records=len(seen),comparisons=len(comparisons))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(evaluate(a.data,a.output)))
