"""Generate fresh language-bound answers from problem-only request records."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT=Path('/home/user/hinglish-research/codeforces700_20261116/alternate_languages_v1')


def api(endpoint,payload=None):
    req=urllib.request.Request('http://127.0.0.1:11435/api/'+endpoint,
        data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as r:return json.load(r)


def atomic(name,obj):
    p=ROOT/(name+'.tmp');p.write_text(json.dumps(obj,indent=2));p.replace(ROOT/name)


def main():
    lock=open('/home/user/hinglish-research/gpu-campaign.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state={'status':'preparing','completed':0,'started':time.time()};atomic('state.json',state)
    try:
        jobs=[json.loads(x) for x in (ROOT/'requests.jsonl').open(encoding='utf-8')]
        model=next(m for m in api('tags')['models'] if m['name']=='qwen3.6:35b')
        config={'model':model,'requests_sha256':hashlib.sha256((ROOT/'requests.jsonl').read_bytes()).hexdigest(),
                'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'options':{'temperature':0,'seed':42,'num_ctx':32768,'num_predict':8192},'think':False,
                'system':'Solve the given competitive programming problem. Explain the algorithm, correctness and complexity concisely, then provide a complete working solution in the requested language in one fenced code block. Use standard input/output. Respect all constraints.',
                'max_seconds':14400,'policy':'one fresh answer per problem/language, no retries or repairs, no checker/editorial/official tests'}
        if (ROOT/'manifest.json').exists():assert json.loads((ROOT/'manifest.json').read_text())==config
        else:atomic('manifest.json',config)
        output=ROOT/'responses.jsonl';done=set()
        if output.exists():done={json.loads(x)['id'] for x in output.open(encoding='utf-8')}
        state['completed']=len(done)
        for job in jobs:
            if job['id'] in done:continue
            if time.time()-state['started']>13500:raise TimeoutError('4h cap')
            start=time.time();reply=api('chat',{'model':'qwen3.6:35b','stream':False,'think':False,'options':config['options'],
                'messages':[{'role':'system','content':config['system']},{'role':'user','content':job['prompt']}]})
            record={'id':job['id'],'split':job['split'],'language':job['language'],'program_type_id':job['program_type_id'],
                    'raw':reply,'elapsed_seconds':time.time()-start}
            with output.open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
            done.add(job['id']);state.update(status='running',completed=len(done),last_id=job['id'],updated=time.time());atomic('state.json',state)
        state.update(status='complete',updated=time.time());atomic('state.json',state)
    except Exception as exc:
        state.update(status='failed',error=repr(exc),updated=time.time());atomic('state.json',state);raise


if __name__=='__main__':main()
