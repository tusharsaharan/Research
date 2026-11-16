"""Independently replay native context caps and exact served prompt accounting."""
from __future__ import annotations
import argparse
import json
import math
from collections import Counter
from pathlib import Path
from compressor_artifacts import digest,records,save
from local_qwen_campaign import ANSWER_SYSTEM,answer_prompt,fingerprint


def audit(data,inputs_path,tokenizer_path,output):
    from transformers import AutoTokenizer
    spec=json.loads((data/'manifest.json').read_text())
    state=json.loads((data/'state.json').read_text())
    if state['status']!='complete':raise ValueError('Incomplete campaign')
    for name in ['answers','variants']:
        if digest(data/(name+'.jsonl'))!=state[name+'_sha256']:raise ValueError('Changed raw outputs')
    if digest(inputs_path)!=spec['source_hashes']['inputs']:raise ValueError('Changed inputs')
    if ANSWER_SYSTEM!=spec['answer_system']:raise ValueError('Changed answer-system prompt')
    tokenizer_hashes={}
    for original,expected in spec['model_files'].items():
        name=Path(original).name
        if name.startswith(('tokenizer','special_tokens','added_tokens','chat_template')):
            path=tokenizer_path/name
            if digest(path)!=expected:raise ValueError('Changed tokenizer asset: '+name)
            tokenizer_hashes[name]=expected
    tokenizer=AutoTokenizer.from_pretrained(tokenizer_path,local_files_only=True,trust_remote_code=False)
    count=lambda text:len(tokenizer.encode(text,add_special_tokens=False))
    inputs={r['uid']:r for r in records(inputs_path)}
    variants={(r['uid'],r['method']):r for r in records(data/'variants.jsonl')}
    expected={(uid,method) for uid in inputs for method in spec['methods']}
    if set(variants)!=expected:raise ValueError('Incomplete variants')
    cap_misses=[];errors=Counter();seen=set();reuse=0
    for key,row in variants.items():
        actual=count(row['text']);original=count(inputs[row['uid']]['context'])
        if actual!=row['context_tokens'] or original!=row['original_context_tokens']:raise ValueError('Saved context-token count mismatch')
        if '@' in row['method']:
            budget=max(1,math.floor(original*float(row['method'].split('@')[1])))
            if budget!=row['budget']:raise ValueError('Saved budget mismatch')
            if actual>budget:cap_misses.append(dict(uid=row['uid'],method=row['method'],actual=actual,budget=budget))
    for row in records(data/'answers.jsonl'):
        key=row['uid'],row['method']
        if key in seen or key not in expected:raise ValueError('Unexpected/duplicate answer')
        seen.add(key);variant=variants[key];source=inputs[row['uid']]
        rendered=tokenizer.apply_chat_template([dict(role='user',content=ANSWER_SYSTEM+'\n\n'+answer_prompt(source,variant['text']))],tokenize=False,add_generation_prompt=True)
        tokens=count(rendered)
        if fingerprint(rendered)!=row['rendered_prompt_sha256'] or tokens!=row['rendered_prompt_tokens']:
            raise ValueError('Served rendered-prompt hash/token count mismatch')
        if row['usage'] and tokens!=row['usage']['prompt_tokens']:raise ValueError('Actual generation input-length mismatch')
        if row['error']:errors[row['error']]+=1
        reuse+=int(row.get('exact_prompt_reuse',False))
    if seen!=expected:raise ValueError('Missing answers')
    report=dict(status='complete',records=len(seen),native_cap_misses=cap_misses,
        exact_rendered_prompts_verified=len(seen),errors=dict(errors),exact_prompt_reuse_rows=reuse,
        tokenizer_assets=tokenizer_hashes,tokenizer_scope=spec['tokenizer_scope'],
        sources={name:digest(data/name) for name in ['manifest.json','state.json','answers.jsonl','variants.jsonl']},
        inputs_sha256=digest(inputs_path),script_sha256=digest(Path(__file__)))
    save(output,report)
    print(json.dumps({key:report[key] for key in ['status','records','native_cap_misses','exact_rendered_prompts_verified','errors','exact_prompt_reuse_rows']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['data','inputs','tokenizer','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();audit(a.data,a.inputs,a.tokenizer,a.output)
