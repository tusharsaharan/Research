"""Serial, journaled submissions through the user's dedicated logged-in browser."""
import hashlib
import json
from pathlib import Path
import re
import time
from codeforces_browser import evaluate

DATA=Path('backend/data/bench/codeforces700_20261116')
ROOT=DATA/'official_codeforces_v1'
HANDLE='SUP3RMAN'


def atomic(name,obj):
    tmp=ROOT/(name+'.tmp');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');tmp.replace(ROOT/name)


def code_from(text):
    candidates=[]
    for m in re.finditer(r'```(?:cpp|c\+\+|cxx)[^\n]*\n',text,re.I):
        end=text.find('```',m.end());code=text[m.end():end if end>=0 else len(text)]
        if re.search(r'\bmain\s*\(',code):candidates.append(code)
    return candidates[-1] if candidates else None


def snapshot():
    return json.loads(evaluate('''JSON.stringify({url:location.href,title:document.title,
      handle:Array.from(document.querySelectorAll('a')).filter(a=>a.href.includes('/profile/')).map(a=>a.textContent.trim())[0],
      text:document.body.innerText.slice(0,6000),
      rows:Array.from(document.querySelectorAll('tr[data-submission-id]')).map(r=>({submission_id:r.getAttribute('data-submission-id'),text:r.innerText}))})'''))


def main():
    ROOT.mkdir(exist_ok=True)
    jobs=[]
    for split in ('train','test'):
        problems={r['id']:r for r in map(json.loads,(DATA/f'{split}_problems.jsonl').open(encoding='utf-8'))}
        for line in (DATA/'qwen_answers_v1'/f'{split}_responses.jsonl').open(encoding='utf-8'):
            row=json.loads(line);jobs.append((split,problems[row['id']],row))
    state={'status':'preparing','started':time.time(),'processed':0}
    atomic('state.json',state)
    journal=ROOT/'submission_journal.jsonl'
    existing={}
    if journal.exists():
        for line in journal.open(encoding='utf-8'):
            r=json.loads(line);existing[r['id']]=r
    if (ROOT/'attempt_in_flight.json').exists():
        attempt=json.loads((ROOT/'attempt_in_flight.json').read_text())
        if attempt['id'] not in existing:raise RuntimeError('Unresolved prior submission; reconcile manually before resuming')
    last_submit=time.time()
    try:
        with journal.open('a',encoding='utf-8') as sink:
            for split,problem,row in jobs:
                ident=row['id']
                if ident in existing:
                    state['processed']+=1;continue
                if time.time()-state['started']>86400:raise TimeoutError('24h overall cap')
                code=code_from(row['raw']['message']['content'])
                record={'id':ident,'split':split,'handle':HANDLE,'label':None}
                if not code:
                    record.update(status='not_submitted',reason='no extractable C++ main; not an official verdict')
                elif not problem.get('input_format'):
                    record.update(status='not_submitted',reason='nonstandard interface needs review')
                else:
                    # This explicit cooldown caps submission traffic, never retries errors.
                    time.sleep(max(0,60-(time.time()-last_submit)))
                    evaluate('location.href='+json.dumps('https://codeforces.com/problemset/submit/'+ident)+'; "navigating"')
                    time.sleep(6)
                    page=snapshot()
                    if page['handle']!=HANDLE:raise RuntimeError('Login/account changed or challenge encountered')
                    if '/problemset/submit/'+ident not in page['url']:raise RuntimeError('Unexpected submission URL')
                    fill='''(()=>{const source=document.querySelector('textarea[name=source]');
                      if(!source)throw Error('No source field');source.value=CODE;
                      const cm=document.querySelector('.CodeMirror');if(cm&&cm.CodeMirror)cm.CodeMirror.setValue(CODE);
                      const lang=document.querySelector('select[name=programTypeId]');
                      if(!Array.from(lang.options).some(o=>o.value==='54'))throw Error('C++17 unavailable');
                      lang.value='54';lang.dispatchEvent(new Event('change',{bubbles:true}));
                      return {length:source.value.length,language:lang.value};})()'''.replace('CODE',json.dumps(code))
                    prepared=evaluate(fill)
                    assert prepared['length']==len(code) and prepared['language']=='54'
                    record['code_sha256']=hashlib.sha256(code.encode()).hexdigest()
                    record['language']='GNU G++17 7.3.0'
                    atomic('attempt_in_flight.json',record)
                    evaluate('document.querySelector("textarea[name=source]").form.querySelector("input[type=submit]").click(); "clicked"')
                    last_submit=time.time();time.sleep(8)
                    page=snapshot()
                    if not page['rows']:raise RuntimeError('No submission receipt; inspect browser, no automatic retry')
                    receipt=page['rows'][0]
                    target=ident.replace('/','')
                    if target+' - ' not in receipt['text'] or HANDLE not in receipt['text']:
                        raise RuntimeError('Receipt does not match target; reconcile manually')
                    if receipt['submission_id'] in {v.get('submission_id') for v in existing.values()}:
                        raise RuntimeError('Duplicate receipt; no new submission confirmed')
                    record.update(status='submitted',**receipt)
                    txt=receipt['text']
                    if 'Accepted' in txt:record['label']='CORRECT'
                    elif re.search(r'Wrong answer|Runtime error|Compilation error|Time limit exceeded|Memory limit exceeded|Idleness limit exceeded|Output limit exceeded',txt,re.I):record['label']='WRONG'
                    record['submission_url']='https://codeforces.com/problemset/submission/'+receipt['submission_id']
                sink.write(json.dumps(record,ensure_ascii=False)+'\n');sink.flush()
                existing[ident]=record
                state.update(status='running',processed=state['processed']+1,last_id=ident,updated=time.time())
                atomic('state.json',state)
                print(json.dumps({'processed':state['processed'],'id':ident,
                                  'submission_id':record.get('submission_id'),
                                  'label':record.get('label'),'status':record['status']}),flush=True)
        state.update(status='submissions_complete',updated=time.time());atomic('state.json',state)
    except Exception as exc:
        state.update(status='stopped',error=repr(exc),updated=time.time());atomic('state.json',state);raise


if __name__=='__main__':main()
