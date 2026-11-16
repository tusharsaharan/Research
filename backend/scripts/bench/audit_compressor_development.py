"""Post-run reproducibility and reference-cap audit; never selects a method.

Three first teacher-win examples illustrate outcomes, not representative quality.
No rows are filtered, no model is queried, and original gold stays unchanged.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from compressor_artifacts import digest, records, save
from gateway.native_tokenizer import ArtifactTokenCounter
from grade import extract_letter


def audit(data,tokenizer_path,output):
    spec=json.loads((data/'manifest.json').read_text())
    state=json.loads((data/'state.json').read_text())
    if state['status']!='complete' or digest(data/'answers.jsonl')!=state['answers_sha256']:
        raise ValueError('Incomplete/changed answer run')
    for name,expected in spec['files'].items():
        if digest(data/name)!=expected:raise ValueError('Frozen input changed: '+name)
    counter=ArtifactTokenCounter(tokenizer_path,spec['tokenizer']['sha256'],
        model_id=spec['tokenizer']['model_id'],scope='reference_text_transfer')
    inputs={r['uid']:r for r in records(data/'inputs.jsonl')}
    variants={(r['uid'],r['method']):r for r in records(data/'variants.jsonl')}
    answers=list(records(data/'answers.jsonl'))
    if len(variants)!=len(inputs)*len(spec['methods']):raise ValueError('Variant coverage mismatch')
    misses=[]
    for (uid,method),row in variants.items():
        count=counter.count(row['text'])
        if count!=row['context_tokens']:raise ValueError('Recorded token count mismatch')
        if '@' in method:
            budget=max(1,math.floor(counter.count(inputs[uid]['context'])*float(method.split('@')[1])))
            if count>budget:misses.append(dict(uid=uid,method=method,count=count,budget=budget))
    examples=[]
    for model in spec['models']:
        indexed={(r['uid'],r['method']):r for r in answers if r['model']==model}
        correct=lambda row,gold: not row['error'] and extract_letter(row['content'])==gold
        selected=0
        for uid,row in inputs.items():
            teacher=indexed[uid,'teacher_atomic@0.5'];bm25=indexed[uid,'bm25_atomic@0.5']
            if correct(teacher,row['gold']) and not correct(bm25,row['gold']):
                examples.append(dict(model=model,source=row,teacher=variants[uid,'teacher_atomic@0.5'],
                    bm25=variants[uid,'bm25_atomic@0.5'],teacher_answer=teacher,bm25_answer=bm25))
                selected+=1
                if selected==3:break
    report=dict(scope='Retrospective exposed-development verification; examples selected to inspect teacher wins, not representativeness.',
        answer_records=len(answers),variant_records=len(variants),reference_cap_misses=misses,
        historical_archive_reuse=sum(r.get('reused_from_archive',False) for r in answers),
        within_run_reuse=sum(r['reused_exact_prompt'] and not r.get('reused_from_archive',False) for r in answers),
        actual_new_calls=sum(not r['reused_exact_prompt'] for r in answers),examples=examples,
        warning='Reference-token caps are not native Qwen3.5 serving caps. Historical timings are not fresh measurements.',
        sources={name:digest(data/name) for name in ['manifest.json','state.json','inputs.jsonl','variants.jsonl','answers.jsonl']},
        script_sha256=digest(Path(__file__)))
    save(output,report)
    return {key:report[key] for key in ['answer_records','variant_records','reference_cap_misses','historical_archive_reuse','within_run_reuse','actual_new_calls']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['data','tokenizer','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.data,a.tokenizer,a.output)))
