"""Freeze held-out exposed-development variants for a two-family GPU campaign."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from compressor_artifacts import digest, records, save, verify_archive
from controls import shuffled_context
from gateway.modules.m2_compressor.qwen_evidence import lexical_order, pack_ranked, source_units
from gateway.modules.m2_compressor.student_ranker import rank_spans
from gateway.native_tokenizer import ArtifactTokenCounter
from local_qwen_campaign import ANSWER_SYSTEM, OPTIONS, answer_prompt, fingerprint


def prepare(data, training, student, output, qwen_only=False):
    if output.exists():
        raise ValueError('Output already exists')
    hashes=verify_archive(data,['inputs.jsonl','rankings.jsonl','tokenizer.json','variants.jsonl','manifest.json','answers.jsonl'])
    original_manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    train_manifest=json.loads((training/'manifest.json').read_text())
    for name,expected in train_manifest['outputs'].items():
        if digest(training/name)!=expected:raise ValueError('Distillation dataset hash mismatch')
    dev_ids={r['uid'] for r in records(training/'compressor_distill_development.jsonl')}
    rows=[r for r in records(data/'inputs.jsonl') if r['uid'] in dev_ids]
    if len(rows)!=len(dev_ids):raise ValueError('Development item coverage mismatch')
    checkpoint=json.loads(student.read_text())
    if checkpoint['training_manifest_sha256']!=digest(training/'manifest.json'):
        raise ValueError('Student and split manifest differ')
    teacher={r['uid']:r for r in records(data/'rankings.jsonl') if r['method']=='bqwen35b_span'}
    historical={r['key']:r for r in records(data/'variants.jsonl') if r['uid'] in dev_ids}
    counter=ArtifactTokenCounter(data/'tokenizer.json',hashes['tokenizer.json'],
        model_id='Qwen/Qwen2.5-3B-Instruct',scope='reference_text_transfer')
    count=counter.count
    output.mkdir(parents=True)
    methods=['original','no_context']+[f'{name}@{rate}' for name in
        ['teacher_prefix','teacher_atomic','student_atomic','bm25_atomic','shuffled'] for rate in [.5,.33]]
    with (output/'inputs.jsonl').open('x',encoding='utf-8') as inp, (output/'variants.jsonl').open('x',encoding='utf-8') as out:
        for row in rows:
            inp.write(json.dumps(row,ensure_ascii=False)+'\n')
            units=source_units(row['context'])
            for method in methods:
                start=time.perf_counter()
                if method=='original':text=row['context']; details={}
                elif method=='no_context':text=''; details={}
                else:
                    name,rate_text=method.split('@');rate=float(rate_text)
                    if name=='teacher_prefix':
                        result=historical[row['uid']+'|bqwen35b_span@'+rate_text]
                    elif name=='shuffled':
                        result=shuffled_context(row['context'],row['uid'],rate,count)
                    else:
                        if name=='teacher_atomic':order=teacher[row['uid']]['order']
                        elif name=='student_atomic':order=rank_spans(units,row['question'],checkpoint)
                        else:order=lexical_order(units,row['question'])
                        result=pack_ranked(row['context'],units,order,rate,count,fallback_policy='empty')
                    text=result['text'];details={k:v for k,v in result.items() if k!='text'}
                prompt=answer_prompt(row,text)
                out.write(json.dumps(dict(key=row['uid']+'|'+method,uid=row['uid'],method=method,text=text,
                    prompt=prompt,prompt_sha256=fingerprint([ANSWER_SYSTEM,prompt]),
                    original_context_tokens=count(row['context']),context_tokens=count(text),
                    reference_rendered_prompt_tokens=count(ANSWER_SYSTEM+'\n'+prompt),
                    preparation_seconds=time.perf_counter()-start,detail=details),ensure_ascii=False)+'\n')
    root=Path(__file__).resolve().parents[3]
    models={'qwen3.5:4b':original_manifest['models']['qwen3.5:4b']}
    if not qwen_only:models['gemma4:26b']='001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c'
    if any(len(value)!=64 for value in models.values()):raise ValueError('Expected full SHA-256 model digests')
    manifest=dict(scope='Exposed source-grouped student development; not fresh or confirmatory',
        methods=methods,items=len(rows),passages=len({r['passage_group'] for r in rows}),
        rates=[.5,.33],models=models,
        answer_system=ANSWER_SYSTEM,options=OPTIONS,think=False,tokenizer=counter.receipt,
        max_seconds=14400,request_timeout=180,failure_policy='Record capped/invalid/error outputs as incorrect; no automatic retries.',
        source_hashes=hashes,training_manifest_sha256=digest(training/'manifest.json'),student_sha256=digest(student),
        files={name:digest(output/name) for name in ['inputs.jsonl','variants.jsonl']},
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        expected_answers=len(rows)*len(methods)*len(models),
        note='Teacher and prefix variants reuse saved teacher ranks. No gold/options enter any compressor. Native serving budgets and XProvence/LLMLingua cells remain separate pending arms.')
    save(output/'manifest.json',manifest)
    return {key:manifest[key] for key in ['items','passages','expected_answers','scope','tokenizer']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--training',type=Path,required=True)
    p.add_argument('--student',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qwen-only',action='store_true',help='Independent family is evaluated in the separate native Mistral campaign')
    a=p.parse_args()
    print(json.dumps(prepare(a.data,a.training,a.student,a.output,a.qwen_only),indent=2))
