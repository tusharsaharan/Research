"""One capped, lock-protected Ollama run of fingerprinted development variants."""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

from compressor_artifacts import digest, records, save


def api(endpoint,payload=None,timeout=180):
    request=urllib.request.Request('http://127.0.0.1:11435/api/'+endpoint,
        data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=timeout) as response:return json.load(response)


def verified_archive_cache(reuse_data,manifest):
    previous=json.loads((reuse_data/'manifest.json').read_text())
    if digest(reuse_data/'manifest.json')!=manifest['source_hashes']['manifest.json']:
        raise ValueError('Archive manifest checksum mismatch')
    if previous['options']!=manifest['options'] or previous['think']!=manifest['think']:
        raise ValueError('Archive inference settings differ')
    if digest(reuse_data/'answers.jsonl')!=manifest['source_hashes']['answers.jsonl']:
        raise ValueError('Archive raw answer checksum mismatch')
    for name,expected in manifest['models'].items():
        if previous['models'].get(name)!=expected:raise ValueError('Archive model digest differs')
    cache={}
    for row in records(reuse_data/'answers.jsonl'):
        response=row.get('response') or {}
        if (row['model'] in manifest['models'] and not response.get('generation_error')
                and response.get('done') and response.get('done_reason')!='length'):
            key=(row['model'],row['prompt_sha256'])
            if key in cache and cache[key]!=response:raise ValueError('Conflicting archived exact-prompt replies')
            cache[key]=response
    return cache


def run(data, lock_path, reuse_data=None):
    import fcntl
    if (data/'state.json').exists():raise ValueError('Run already exists; no automatic duplicate/retry')
    manifest=json.loads((data/'manifest.json').read_text())
    for name,expected in manifest['files'].items():
        if digest(data/name)!=expected:raise ValueError('Frozen campaign input changed: '+name)
    models={m['name']:m for m in api('tags')['models']}
    for name,expected in manifest['models'].items():
        if models.get(name,{}).get('digest')!=expected:raise ValueError('Model missing/digest changed: '+name)
    archive_cache={} if reuse_data is None else verified_archive_cache(reuse_data,manifest)
    state=dict(status='waiting_for_lock',completed=0,models={},max_seconds=manifest['max_seconds'])
    save(data/'state.json',state)
    start=time.monotonic()
    with lock_path.open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        state['status']='running';save(data/'state.json',state)
        try:
            variants=list(records(data/'variants.jsonl'))
            with (data/'answers.jsonl').open('x',encoding='utf-8') as stream:
                for model in manifest['models']:
                    state['models'][model]=dict(completed=0,errors=0)
                    cache={key[1]:value for key,value in archive_cache.items() if key[0]==model}
                    archived_prompts=set(cache)
                    for variant in variants:
                        if time.monotonic()-start+180>manifest['max_seconds']:
                            raise TimeoutError('Frozen campaign wall cap reached')
                        response=None;error=None;reused=False
                        prompt=variant['prompt']
                        if len((manifest['answer_system']+prompt).encode())+640>=manifest['options']['num_ctx']:
                            error='Conservative prompt size guard; refuse truncation'
                        elif variant['prompt_sha256'] in cache:
                            response=cache[variant['prompt_sha256']];reused=True
                        else:
                            try:
                                response=api('generate',dict(model=model,system=manifest['answer_system'],prompt=prompt,
                                    think=False,stream=False,options=manifest['options'],keep_alive='10m'))
                                if not response.get('done') or response.get('done_reason')=='length':
                                    error='Incomplete/output-capped generation'
                                if not error:cache[variant['prompt_sha256']]=response
                            except Exception as exc:error=f'{type(exc).__name__}: {exc}'
                        result=dict(key=variant['key'],uid=variant['uid'],method=variant['method'],model=model,
                            model_digest=manifest['models'][model],prompt_sha256=variant['prompt_sha256'],
                            content='' if error else (response or {}).get('response',''),error=error,
                            response=response,reused_exact_prompt=reused,
                            reused_from_archive=reused and variant['prompt_sha256'] in archived_prompts,
                            manifest_sha256=digest(data/'manifest.json'))
                        stream.write(json.dumps(result,ensure_ascii=False)+'\n');stream.flush()
                        state['completed']+=1;state['models'][model]['completed']+=1
                        state['models'][model]['errors']+=int(error is not None)
                        state['elapsed_seconds']=time.monotonic()-start
                        save(data/'state.json',state)
                        if state['completed']%100==0:print(json.dumps(state),flush=True)
                    state['models'][model]['gpu']=api('ps')
                    api('generate',dict(model=model,keep_alive=0),timeout=30)
            state.update(status='complete',answers_sha256=digest(data/'answers.jsonl'))
            save(data/'state.json',state)
        except BaseException as exc:
            state.update(status='failed',error=f'{type(exc).__name__}: {exc}')
            save(data/'state.json',state)
            raise
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--lock',type=Path,default=Path('/home/user/hinglish-research/gpu-campaign.lock'))
    p.add_argument('--reuse-data',type=Path,help='Hash-verified historical campaign with identical model/options and exact rendered prompt hashes')
    a=p.parse_args();run(a.data,a.lock,a.reuse_data)
