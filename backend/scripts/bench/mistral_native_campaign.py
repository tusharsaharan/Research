"""Native-token independent-family development comparison on cached Mistral.

All methods see context/question only. This uses the frozen 183-item exposed
development split, never a fresh/sealed test. Complete failures remain rows.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import time
from pathlib import Path

from compressor_artifacts import digest, records, save
from controls import shuffled_context
from gateway.modules.m2_compressor.hinglish_budget import strict_prefix
from gateway.modules.m2_compressor.qwen_evidence import lexical_order, pack_ranked, source_units
from gateway.modules.m2_compressor.student_ranker import rank_spans
from local_qwen_campaign import ANSWER_SYSTEM, answer_prompt, fingerprint

MISTRAL_REVISION='c170c708c41dac9275d15a8fff4eca08d52bab71'
LLML2='microsoft/llmlingua-2-xlm-roberta-large-meetingbank'
LLML2_REVISION='ebaba9b0e874dadd3003ffcff828e4397e568089'
XPROVENCE='naver/xprovence-reranker-bgem3-v2'
XPROVENCE_REVISION='f2798d357213c40164bdd79557d6d2e43ca7d8d2'


def run(base, teachers, student_path, model_path, output):
    import fcntl
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
    from gateway.modules.m2_compressor.llmlingua2 import LLMLingua2Compressor

    if output.exists():raise ValueError('Output exists; no automatic repeat/resume')
    if model_path.name!=MISTRAL_REVISION:raise ValueError('Cached Mistral revision mismatch')
    base_manifest=json.loads((base/'manifest.json').read_text())
    if digest(base/'inputs.jsonl')!=base_manifest['files']['inputs.jsonl']:
        raise ValueError('Frozen development inputs changed')
    if digest(student_path)!=base_manifest['student_sha256']:raise ValueError('Student checkpoint changed')
    checkpoint=json.loads(student_path.read_text())
    rows=list(records(base/'inputs.jsonl'))
    if len(rows)!=183:raise ValueError('Expected all 183 frozen development items')
    teacher={r['uid']:r for r in records(teachers) if r['method']=='bqwen35b_span'}
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
    count=lambda text:len(tokenizer.encode(text,add_special_tokens=False))
    llml_path=Path(snapshot_download(LLML2,revision=LLML2_REVISION,local_files_only=True))
    xp_path=Path(snapshot_download(XPROVENCE,revision=XPROVENCE_REVISION,local_files_only=True))
    methods=['original','no_context']+[f'{method}@{rate}' for method in
        ['teacher_prefix','teacher_atomic','student_atomic','bm25_atomic','shuffled','llml2_strict','xprovence_strict']
        for rate in [.5,.33]]
    source_files={str(path):digest(path) for path in sorted(model_path.iterdir()) if path.is_file()}
    xp_files={str(path):digest(path) for path in sorted(xp_path.iterdir()) if path.is_file()}
    llml_files={str(path):digest(path) for path in sorted(llml_path.iterdir()) if path.is_file()}
    spec=dict(scope='Exposed source-grouped independent-family development',model='mistralai/Mistral-7B-Instruct-v0.3',
        revision=MISTRAL_REVISION,model_files=source_files,xprovence_files=xp_files,llml2_files=llml_files,
        items=len(rows),source_groups=len({r['passage_group'] for r in rows}),methods=methods,rates=[.5,.33],
        primary_candidate='student_atomic@0.5',primary_baselines=['bm25_atomic@0.5','llml2_strict@0.5','xprovence_strict@0.5'],
        tokenizer_scope='Native Mistral tokenizer and the exact same local HF serving checkpoint/template',
        answer_system=ANSWER_SYSTEM,max_new_tokens=128,do_sample=False,seed=42,max_seconds=14400,
        xprovence_settings=dict(revision=XPROVENCE_REVISION,threshold=.3,always_select_title=False),
        baseline_budget_policy='Published model output followed by explicit word-boundary measured cap; report clipping.',
        source_hashes=dict(inputs=digest(base/'inputs.jsonl'),teachers=digest(teachers),student=digest(student_path)),
        code_sha256=digest(Path(__file__)),failure_policy='No retries. Exceptions, empty and capped replies count incorrect. No row filtering.')
    output.mkdir(parents=True)
    save(output/'manifest.json',spec)
    state=dict(status='waiting_for_lock',stage='preparation',variants=0,answers=0)
    save(output/'state.json',state)
    start=time.monotonic()
    def bounded():
        if time.monotonic()-start>spec['max_seconds']-180:raise TimeoutError('Four-hour wall cap')
    with Path('/home/user/hinglish-research/gpu-campaign.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            state.update(status='running',stage='baseline_compression');save(output/'state.json',state)
            setup_start=time.perf_counter()
            lingua=LLMLingua2Compressor(str(llml_path),device='cuda:0')
            lingua._ensure()
            xp=AutoModel.from_pretrained(xp_path,trust_remote_code=True,local_files_only=True).to('cuda').eval()
            state['compressor_setup_seconds']=time.perf_counter()-setup_start
            with (output/'variants.jsonl').open('x',encoding='utf-8') as stream:
                for row in rows:
                    bounded();passage=row['context'];units=source_units(passage)
                    for method in methods:
                        tick=time.perf_counter();error=None;clip=False;teacher_cost=0
                        budget=count(passage)
                        try:
                            if method=='original':text=passage
                            elif method=='no_context':text=''
                            else:
                                name,rate_text=method.split('@');rate=float(rate_text)
                                budget=max(1,math.floor(count(passage)*rate))
                                if name=='shuffled':text=shuffled_context(passage,row['uid'],rate,count)['text']
                                elif name=='llml2_strict':
                                    text=lingua._ensure().compress_prompt(passage,rate=rate,force_tokens=['\n','?','.'])['compressed_prompt']
                                    capped=strict_prefix(text,budget,count);clip=capped!=text;text=capped
                                elif name=='xprovence_strict':
                                    text=xp.process(row['question'],passage,threshold=.3,always_select_title=False)['pruned_context']
                                    capped=strict_prefix(text,budget,count);clip=capped!=text;text=capped
                                else:
                                    if name.startswith('teacher'):
                                        order=teacher[row['uid']]['order'];teacher_cost=teacher[row['uid']]['seconds']
                                    elif name=='student_atomic':order=rank_spans(units,row['question'],checkpoint)
                                    else:order=lexical_order(units,row['question'])
                                    result=pack_ranked(passage,units,order,rate,count,
                                        fallback_policy='word_prefix' if name=='teacher_prefix' else 'empty')
                                    text=result['text'];clip=result['detail']['budget_enforced']
                            if count(text)>budget:raise ValueError('Native context cap exceeded')
                        except Exception as exc:
                            text='';error=f'{type(exc).__name__}: {exc}'
                        variant=dict(uid=row['uid'],method=method,text=text,budget=budget,context_tokens=count(text),
                            original_context_tokens=count(passage),compression_seconds=time.perf_counter()-tick,
                            historical_teacher_rank_seconds=teacher_cost,budget_clipped=clip,error=error)
                        stream.write(json.dumps(variant,ensure_ascii=False)+'\n');stream.flush();state['variants']+=1
                    save(output/'state.json',state)
            del xp,lingua;gc.collect();torch.cuda.empty_cache()
            bounded();state['stage']='answering';save(output/'state.json',state)
            setup_start=time.perf_counter()
            torch.manual_seed(42)
            model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,trust_remote_code=False,
                torch_dtype=torch.bfloat16,device_map='cuda',attn_implementation='sdpa').eval()
            state['generator_setup_seconds']=time.perf_counter()-setup_start
            by_id={r['uid']:r for r in rows};cache={}
            with (output/'answers.jsonl').open('x',encoding='utf-8') as stream:
                for variant in records(output/'variants.jsonl'):
                    bounded();row=by_id[variant['uid']];text='';error=variant['error'];usage=None;reused=False
                    prompt=ANSWER_SYSTEM+'\n\n'+answer_prompt(row,variant['text'])
                    rendered=tokenizer.apply_chat_template([dict(role='user',content=prompt)],tokenize=False,add_generation_prompt=True)
                    key=fingerprint(rendered)
                    if error:pass
                    elif key in cache:
                        text,error,usage=cache[key];reused=True
                    else:
                        try:
                            encoded=tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to('cuda')
                            if encoded.input_ids.shape[1]+128>8192:raise ValueError('No prompt truncation allowed')
                            torch.cuda.synchronize();tick=time.perf_counter()
                            with torch.inference_mode():
                                generated=model.generate(**encoded,max_new_tokens=128,do_sample=False,
                                    pad_token_id=tokenizer.eos_token_id)
                            torch.cuda.synchronize();elapsed=time.perf_counter()-tick
                            ids=generated[0,encoded.input_ids.shape[1]:]
                            text=tokenizer.decode(ids,skip_special_tokens=True)
                            if len(ids)>=128 and int(ids[-1])!=tokenizer.eos_token_id:error='Output cap reached'
                            usage=dict(prompt_tokens=int(encoded.input_ids.shape[1]),output_tokens=len(ids),generation_seconds=elapsed,
                                       gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
                            cache[key]=(text,error,usage)
                        except Exception as exc:error=f'{type(exc).__name__}: {exc}'
                    stream.write(json.dumps(dict(uid=row['uid'],method=variant['method'],content=text,error=error,usage=usage,
                        exact_prompt_reuse=reused,rendered_prompt_sha256=key),ensure_ascii=False)+'\n');stream.flush()
                    state['answers']+=1;state['elapsed_seconds']=time.monotonic()-start
                    save(output/'state.json',state)
                    if state['answers']%100==0:print(json.dumps(state),flush=True)
            state.update(status='complete',answers_sha256=digest(output/'answers.jsonl'),variants_sha256=digest(output/'variants.jsonl'))
            save(output/'state.json',state)
        except BaseException as exc:
            state.update(status='failed',error=f'{type(exc).__name__}: {exc}')
            save(output/'state.json',state);raise
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ['base','teachers','student','model','output']:p.add_argument('--'+flag,type=Path,required=True)
    a=p.parse_args();run(a.base,a.teachers,a.student,a.model,a.output)
