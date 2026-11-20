"""Serial, journaled submissions through the user's dedicated logged-in browser."""
import hashlib
import json
from pathlib import Path
import re
import time
from codeforces_browser import evaluate

DATA=Path('backend/data/bench/codeforces700_20261116')
ROOT=DATA/'official_codeforces_v1'
HANDLE='research_test_acc'


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


def wait_verified():
    # Observe the normal widget result; never solve, alter, or expose its token.
    return evaluate('''new Promise(resolve=>{
      const ready=()=>{const t=document.querySelector('input[name=turnstileToken],input[name="cf-turnstile-response"]');
        const b=document.querySelector('textarea[name=source]')?.form.querySelector('input[type=submit]');
        return !!b&&!b.disabled&&(!document.querySelector('.cf-turnstile,.turnstile-container')||(!!t&&!!t.value));};
      if(ready()){resolve(true);return;}const timer=setInterval(()=>{if(ready()){clearInterval(timer);clearTimeout(deadline);resolve(true);}},500);
      const deadline=setTimeout(()=>{clearInterval(timer);resolve(false);},180000);
    })''')


def status_receipt(ident,existing):
    result=evaluate('''(async()=>{const response=await fetch('/problemset/status?my=on',{credentials:'same-origin'});
      const doc=new DOMParser().parseFromString(await response.text(),'text/html');
      return {authenticated:!!doc.querySelector('a[href="/profile/research_test_acc"]'),
      rows:Array.from(doc.querySelectorAll('tr[data-submission-id]')).map(r=>({submission_id:r.getAttribute('data-submission-id'),text:r.innerText}))};})()''')
    if not result['authenticated']:raise RuntimeError('Cannot reconcile authenticated submission status; no retry')
    old={r.get('submission_id') for r in existing.values()}
    return next((r for r in result['rows'] if ident.replace('/','')+' - ' in r['text'] and r['submission_id'] not in old),None)


def wait_receipt_navigation(expression):
    try:
        return evaluate(expression)
    except RuntimeError as exc:
        if 'Inspected target navigated or closed' not in str(exc) and 'Execution context was destroyed' not in str(exc):
            raise
        # The status-page navigation may destroy the observer's old context.
        # Reconnect read-only; never click Submit again because of this event.
        time.sleep(5)
        return None


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
                    if '/problemset/submit/'+ident not in page['url']:
                        if page['url']=='https://codeforces.com/problemset/status?my=on':
                            record.update(status='not_submitted',reason='submission route redirected to status; official judging unavailable, not a WRONG verdict',observed_url=page['url'])
                            sink.write(json.dumps(record,ensure_ascii=False)+'\n');sink.flush()
                            existing[ident]=record
                            state.update(status='running',processed=state['processed']+1,last_id=ident,updated=time.time())
                            atomic('state.json',state)
                            print(json.dumps({'processed':state['processed'],'id':ident,'status':record['status'],'reason':record['reason']}),flush=True)
                            continue
                        raise RuntimeError('Unexpected submission URL')
                    languages=evaluate("Array.from(document.querySelector('select[name=programTypeId]').options).map(o=>({id:o.value,name:o.text}))")
                    if not any(lang['id']=='54' for lang in languages):
                        record.update(status='not_submitted',reason='Frozen GNU G++17 compiler unavailable for this problem; source not translated or retried',available_languages=languages)
                        sink.write(json.dumps(record,ensure_ascii=False)+'\n');sink.flush()
                        existing[ident]=record
                        state.update(status='running',processed=state['processed']+1,last_id=ident,updated=time.time())
                        atomic('state.json',state)
                        print(json.dumps({'processed':state['processed'],'id':ident,'status':record['status'],'reason':record['reason']}),flush=True)
                        continue
                    fill='''(()=>{const source=document.querySelector('textarea[name=source]');
                      if(!source)throw Error('No source field');source.value=CODE;
                      const cm=document.querySelector('.CodeMirror');if(cm&&cm.CodeMirror)cm.CodeMirror.setValue(CODE);
                      const lang=document.querySelector('select[name=programTypeId]');
                      if(!Array.from(lang.options).some(o=>o.value==='54'))throw Error('C++17 unavailable');
                      lang.value='54';lang.dispatchEvent(new Event('change',{bubbles:true}));
                      return {length:source.value.length,language:lang.value};})()'''.replace('CODE',json.dumps(code))
                    prepared=evaluate(fill)
                    assert prepared['length']==len(code) and prepared['language']=='54'
                    if not wait_verified():raise RuntimeError('ANTI_BOT_VERIFICATION_REQUIRED: verification did not finish within 3min; no click issued')
                    record['code_sha256']=hashlib.sha256(code.encode()).hexdigest()
                    record['language']='GNU G++17 7.3.0'
                    atomic('attempt_in_flight.json',record)
                    evaluate('document.querySelector("textarea[name=source]").form.querySelector("input[type=submit]").click(); "clicked"')
                    last_submit=time.time();time.sleep(8)
                    wait_receipt_navigation('''new Promise(resolve=>{
                      const ready=()=>!!document.querySelector('tr[data-submission-id]');
                      if(ready()){resolve(true);return;}
                      const observer=new MutationObserver(()=>{if(ready()){observer.disconnect();resolve(true);}});
                      observer.observe(document.documentElement,{childList:true,subtree:true});
                      setTimeout(()=>{observer.disconnect();resolve(false);},20000);
                    })''')
                    page=snapshot()
                    if not page['rows'] and 'Please complete the anti-bot verification' in page['text']:
                        receipt=status_receipt(ident,existing)
                        if receipt:
                            page['rows']=[receipt]
                        elif wait_verified():
                            # One post-verification click only after confirming no receipt.
                            evaluate('document.querySelector("textarea[name=source]").form.querySelector("input[type=submit]").click(); "clicked after completed verification"')
                            last_submit=time.time();time.sleep(20)
                            page=snapshot()
                    if not page['rows']:
                        if 'Please complete the anti-bot verification' in page['text'] or 'Just a moment' in page['title']:
                            raise RuntimeError('ANTI_BOT_VERIFICATION_REQUIRED: complete the normal browser verification and manually click Submit once; reconcile receipt before resume. No automatic resubmission.')
                        raise RuntimeError('No submission receipt; inspect browser, no automatic retry')
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
