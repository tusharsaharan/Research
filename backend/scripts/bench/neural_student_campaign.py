"""One fixed neural distillation attempt and added native-Mistral dev cells.

Training sees question/span pairs and ordinal teacher orders, never QA gold.
Existing native baseline outputs remain immutable. This is exposed development.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import random
import time
from pathlib import Path

from compressor_artifacts import digest, records, save
from gateway.modules.m2_compressor.qwen_evidence import pack_ranked
from local_qwen_campaign import ANSWER_SYSTEM, answer_prompt, fingerprint

SEED=42
BASE_REVISION='ebaba9b0e874dadd3003ffcff828e4397e568089'
TRAINING=dict(epochs=2,pairs_per_batch=16,max_pair_tokens=192,encoder_lr=1e-5,
    head_lr=1e-3,weight_decay=.01,max_gradient_norm=1.0,max_seconds=1800)


def ordinal_pairs(rows):
    texts=[];pairs=[]
    for row in rows:
        offset=len(texts)
        texts.extend((row['question'],span) for span in row['spans'])
        order=row['teacher_order']
        if sorted(order)!=list(range(len(row['spans']))):raise ValueError('Invalid teacher permutation')
        for i,winner in enumerate(order):
            pairs.extend((offset+winner,offset+loser) for loser in order[i+1:])
    return texts,pairs


def run(training,native,model_path,output):
    import fcntl
    import torch
    from huggingface_hub import snapshot_download
    from safetensors.torch import load_file,save_file
    from transformers import AutoModel,AutoModelForCausalLM,AutoTokenizer
    from train_compact_student import metrics
    from review_mistral_native import review

    if output.exists():raise ValueError('Output exists; no repeat/automatic resume')
    spec=json.loads((native/'manifest.json').read_text())
    original_state=json.loads((native/'state.json').read_text())
    if original_state['status']!='complete':raise ValueError('Base native campaign incomplete')
    for name in ['answers','variants']:
        if digest(native/(name+'.jsonl'))!=original_state[name+'_sha256']:raise ValueError('Base output hash mismatch')
    train_manifest=json.loads((training/'manifest.json').read_text())
    for name,expected in train_manifest['outputs'].items():
        if digest(training/name)!=expected:raise ValueError('Training data hash mismatch')
    train_rows=list(records(training/'compressor_distill_train.jsonl'))
    dev_rows=list(records(training/'compressor_distill_development.jsonl'))
    if {r['passage_group'] for r in train_rows}&{r['passage_group'] for r in dev_rows}:raise ValueError('Source leakage')
    inputs_path=native.parent/'data/base/inputs.jsonl'
    if digest(inputs_path)!=spec['source_hashes']['inputs']:raise ValueError('Native input checksum mismatch')
    inputs={r['uid']:r for r in records(inputs_path)}
    if set(inputs)!={r['uid'] for r in dev_rows}:raise ValueError('Development coverage mismatch')
    for row in dev_rows:
        if row['context']!=inputs[row['uid']]['context'] or row['question']!=inputs[row['uid']]['question']:
            raise ValueError('Development source text mismatch')
    if model_path.name!=spec['revision']:raise ValueError('Answer model revision mismatch')
    for path,expected in {**spec['model_files'],**spec['llml2_files']}.items():
        if digest(Path(path))!=expected:raise ValueError('Pinned model asset changed: '+path)
    base=Path(snapshot_download('microsoft/llmlingua-2-xlm-roberta-large-meetingbank',revision=BASE_REVISION,local_files_only=True))
    texts,pairs=ordinal_pairs(train_rows)
    output.mkdir(parents=True)
    frozen=dict(scope='Exploratory exposed-development neural teacher imitation after lexical-student results',
        training=TRAINING,seed=SEED,base_revision=BASE_REVISION,architecture='XLM-R large CLS linear ranker; last block and head trainable',
        training_manifest_sha256=digest(training/'manifest.json'),native_manifest_sha256=digest(native/'manifest.json'),
        native_answers_sha256=original_state['answers_sha256'],base_asset_hashes=spec['llml2_files'],
        answer_asset_hashes=spec['model_files'],training_items=len(train_rows),development_items=len(dev_rows),
        pairs=len(pairs),code_sha256=digest(Path(__file__)),max_seconds=3600,
        decoder='Same native Mistral greedy 128-token decoder; no truncation/retries',
        failure_policy='Keep errors/empty/capped answers incorrect; no checkpoint or hyperparameter search')
    save(output/'manifest.json',frozen)
    state=dict(status='waiting_for_lock',stage='training',step=0,answers=0)
    save(output/'state.json',state)
    start=time.monotonic()
    with Path('/home/user/hinglish-research/gpu-campaign.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            state['status']='running';save(output/'state.json',state)
            torch.manual_seed(SEED);random.seed(SEED)
            tokenizer=AutoTokenizer.from_pretrained(base,local_files_only=True)
            encoder=AutoModel.from_pretrained(base,local_files_only=True,add_pooling_layer=False).to('cuda')
            if encoder.config.model_type!='xlm-roberta':raise ValueError('Expected XLM-R base encoder')
            for parameter in encoder.parameters():parameter.requires_grad_(False)
            last=encoder.encoder.layer[-1]
            for parameter in last.parameters():parameter.requires_grad_(True)
            head=torch.nn.Linear(encoder.config.hidden_size,1).to('cuda')
            encoder.eval();last.train();head.train()
            encoded=tokenizer([q for q,s in texts],[s for q,s in texts],padding='max_length',
                truncation=True,max_length=TRAINING['max_pair_tokens'],return_tensors='pt')
            untruncated=tokenizer([q for q,s in texts],[s for q,s in texts],truncation=False,return_length=True)
            truncated=sum(n>TRAINING['max_pair_tokens'] for n in untruncated['length'])
            del untruncated
            optimizer=torch.optim.AdamW([{'params':last.parameters(),'lr':TRAINING['encoder_lr']},
                {'params':head.parameters(),'lr':TRAINING['head_lr']}],weight_decay=TRAINING['weight_decay'])
            def score(batch):
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=encoder(**batch).last_hidden_state[:,0,:]
                    return head(hidden).squeeze(-1).float()
            trained=list(last.parameters())+list(head.parameters())
            train_start=time.monotonic()
            with (output/'losses.jsonl').open('x') as log:
                for epoch in range(TRAINING['epochs']):
                    order=list(pairs);random.Random(SEED+epoch).shuffle(order)
                    for index in range(0,len(order),TRAINING['pairs_per_batch']):
                        if time.monotonic()-train_start>TRAINING['max_seconds']-10:raise TimeoutError('Frozen training cap')
                        batch_pairs=order[index:index+TRAINING['pairs_per_batch']]
                        ids=[w for w,l in batch_pairs]+[l for w,l in batch_pairs]
                        batch={key:value[ids].to('cuda') for key,value in encoded.items()}
                        optimizer.zero_grad(set_to_none=True)
                        scores=score(batch);n=len(batch_pairs)
                        loss=torch.nn.functional.softplus(-(scores[:n]-scores[n:])).mean()
                        if not torch.isfinite(loss):raise ValueError('Non-finite training loss')
                        loss.backward();torch.nn.utils.clip_grad_norm_(trained,TRAINING['max_gradient_norm']);optimizer.step()
                        state['step']+=1
                        log.write(json.dumps(dict(epoch=epoch+1,step=state['step'],loss=float(loss.detach())))+'\n')
                        if state['step']%50==0:
                            state['elapsed_seconds']=time.monotonic()-start;save(output/'state.json',state)
                            print(json.dumps(state),flush=True)
            torch.cuda.synchronize()
            patch={'last.'+key:value.detach().cpu().contiguous() for key,value in last.state_dict().items()}
            patch.update({'head.'+key:value.detach().cpu().contiguous() for key,value in head.state_dict().items()})
            save_file(patch,str(output/'checkpoint.safetensors'))
            # Prove that evaluation uses the persisted, safely loadable checkpoint.
            restored=load_file(str(output/'checkpoint.safetensors'),device='cuda')
            last.load_state_dict({key[5:]:value for key,value in restored.items() if key.startswith('last.')},strict=True)
            head.load_state_dict({key[5:]:value for key,value in restored.items() if key.startswith('head.')},strict=True)
            del restored
            save(output/'checkpoint.json',dict(base_revision=BASE_REVISION,patch='checkpoint.safetensors',
                patch_sha256=digest(output/'checkpoint.safetensors'),training_manifest_sha256=digest(output/'manifest.json'),
                base_asset_hashes=spec['llml2_files'],application='Load frozen base AutoModel without pooler; apply last.* to encoder.layer[-1], head.* to linear head; strict=True for each.'))
            state.update(stage='ranking_development',training_seconds=time.monotonic()-train_start)
            save(output/'state.json',state)
            encoder.eval();head.eval();ranking={};timings={}
            def rank(row):
                torch.cuda.synchronize();tick=time.perf_counter()
                batch=tokenizer([row['question']]*len(row['spans']),row['spans'],padding=True,
                    truncation=True,max_length=TRAINING['max_pair_tokens'],return_tensors='pt').to('cuda')
                with torch.inference_mode():values=score(batch).cpu().tolist()
                torch.cuda.synchronize();timings[row['uid']]=time.perf_counter()-tick
                result=sorted(range(len(values)),key=lambda i:(-values[i],i));ranking[row['uid']]=result
                return result
            imitation=metrics(dev_rows,rank)
            save(output/'training_report.json',dict(status='complete',teacher_imitation=imitation,
                training_seconds=state['training_seconds'],total_encoder_parameters=sum(p.numel() for p in encoder.parameters()),
                trainable_parameters=sum(p.numel() for p in trained),truncated_training_pair_texts=truncated,
                steps=state['step'],checkpoint_sha256=digest(output/'checkpoint.safetensors'),
                note='Final fixed checkpoint only; ordinal teacher agreement is not downstream QA quality.'))
            with (output/'rankings.jsonl').open('x') as stream:
                for row in dev_rows:stream.write(json.dumps(dict(uid=row['uid'],order=ranking[row['uid']],seconds=timings[row['uid']]))+'\n')
            del encoder,last,head,optimizer,trained,encoded,batch,scores,loss,patch
            gc.collect();torch.cuda.empty_cache()
            tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
            count=lambda text:len(tokenizer.encode(text,add_special_tokens=False))
            variants=[]
            for row in dev_rows:
                for rate in [.5,.33]:
                    tick=time.perf_counter()
                    packed=pack_ranked(row['context'],row['spans'],ranking[row['uid']],rate,count,fallback_policy='empty')
                    variants.append(dict(uid=row['uid'],method=f'student_neural@{rate}',text=packed['text'],
                        budget=packed['target_tokens'],context_tokens=packed['actual_tokens'],original_context_tokens=packed['original_tokens'],
                        compression_seconds=timings[row['uid']]+time.perf_counter()-tick,historical_teacher_rank_seconds=0,
                        budget_clipped=packed['detail']['budget_enforced'],error=None))
            with (output/'variants.jsonl').open('x') as stream:
                for row in variants:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
            state.update(stage='answering');save(output/'state.json',state)
            model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True,torch_dtype=torch.bfloat16,
                device_map='cuda',attn_implementation='sdpa').eval()
            cache={r['rendered_prompt_sha256']:r for r in records(native/'answers.jsonl') if r.get('usage')}
            with (output/'answers.jsonl').open('x') as stream:
                for variant in variants:
                    if time.monotonic()-start>frozen['max_seconds']-180:raise TimeoutError('Frozen neural campaign cap')
                    row=inputs[variant['uid']];text='';error=None;usage=None;reused=False
                    rendered=tokenizer.apply_chat_template([dict(role='user',content=ANSWER_SYSTEM+'\n\n'+answer_prompt(row,variant['text']))],tokenize=False,add_generation_prompt=True)
                    key=fingerprint(rendered);prompt_tokens=count(rendered)
                    if key in cache:
                        cached=cache[key];text=cached['content'];error=cached['error'];usage=cached['usage'];reused=True
                    else:
                        try:
                            batch=tokenizer(rendered,add_special_tokens=False,return_tensors='pt').to('cuda')
                            if prompt_tokens+128>8192:raise ValueError('No prompt truncation allowed')
                            torch.cuda.synchronize();tick=time.perf_counter()
                            with torch.inference_mode():generated=model.generate(**batch,max_new_tokens=128,do_sample=False,pad_token_id=tokenizer.eos_token_id)
                            torch.cuda.synchronize();elapsed=time.perf_counter()-tick
                            ids=generated[0,prompt_tokens:];text=tokenizer.decode(ids,skip_special_tokens=True)
                            if len(ids)>=128 and int(ids[-1])!=tokenizer.eos_token_id:error='Output cap reached'
                            usage=dict(prompt_tokens=prompt_tokens,output_tokens=len(ids),generation_seconds=elapsed,
                                gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
                        except Exception as exc:error=f'{type(exc).__name__}: {exc}'
                    answer=dict(uid=row['uid'],method=variant['method'],content=text,error=error,usage=usage,
                        exact_prompt_reuse=reused,rendered_prompt_sha256=key,rendered_prompt_tokens=prompt_tokens)
                    stream.write(json.dumps(answer,ensure_ascii=False)+'\n');stream.flush()
                    if usage:cache[key]=answer
                    state['answers']+=1;state['elapsed_seconds']=time.monotonic()-start
                    save(output/'state.json',state)
            combined=output/'combined';combined.mkdir()
            for name in ['answers','variants']:
                (combined/(name+'.jsonl')).write_bytes((native/(name+'.jsonl')).read_bytes()+(output/(name+'.jsonl')).read_bytes())
            combined_spec={**spec,'methods':spec['methods']+['student_neural@0.5','student_neural@0.33'],
                'scope':spec['scope']+'; exploratory neural addition after lexical Qwen findings',
                'neural_addition_manifest_sha256':digest(output/'manifest.json'),'checkpoint_sha256':digest(output/'checkpoint.safetensors')}
            save(combined/'manifest.json',combined_spec)
            save(combined/'state.json',dict(status='complete',answers_sha256=digest(combined/'answers.jsonl'),variants_sha256=digest(combined/'variants.jsonl')))
            review(combined,inputs_path)
            state.update(status='complete',answers_sha256=digest(output/'answers.jsonl'),variants_sha256=digest(output/'variants.jsonl'),
                checkpoint_sha256=digest(output/'checkpoint.safetensors'))
            save(output/'state.json',state)
        except BaseException as exc:
            state.update(status='failed',error=f'{type(exc).__name__}: {exc}');save(output/'state.json',state);raise
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['training','native','model','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.training,a.native,a.model,a.output)
