"""Conservative sandboxed compilation/test audit; never runs generated checkers."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import tempfile
import time

DATA=Path('/home/user/hinglish-research/codeforces700_20261116')
ROOT=DATA/'qwen_judging_v1'
POLICY={'cpp_selection':'last cpp/c++/cxx fence containing main, including unclosed fence',
        'compiler':['g++','-std=c++17','-O2','-pipe'], 'compile_timeout_seconds':30,
        'test_timeout_seconds':10,'max_output_bytes':4194304,'memory_mib':1024,
        'max_wall_seconds':86400,
        'scope':'Compile stdio C++ candidates; test only clearly specified integer scalar outputs without custom checkers.',
        'verdicts':'compile_error, failed_saved_test, runtime_error, resource_limit, passed_available_tests, unverified',
        'warning':'Saved tests and metadata are not validated official judges; passing is not proof of universal correctness.'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def atomic(name,obj):
    tmp=ROOT/(name+'.tmp');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');tmp.replace(ROOT/name)


def sandbox(extra,command):
    return ['bwrap','--unshare-all','--die-with-parent','--ro-bind','/usr','/usr',
            '--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--symlink','usr/bin','/bin',
            '--proc','/proc','--dev','/dev','--tmpfs','/tmp',*extra,'--',*command]


def limits():
    resource.setrlimit(resource.RLIMIT_AS,(POLICY['memory_mib']*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(POLICY['max_output_bytes'],)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def run(command,timeout,stdin=b''):
    with tempfile.TemporaryFile() as inp,tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
        inp.write(stdin);inp.seek(0)
        process=subprocess.Popen(command,stdin=inp,stdout=out,stderr=err,start_new_session=True,
                                 preexec_fn=limits,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        timed_out=False
        try:process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGKILL);process.wait()
        out.seek(0);err.seek(0)
        return {'exit':process.returncode,'timeout':timed_out,
                'stdout':out.read().decode('utf-8',errors='replace'),
                'stderr':err.read().decode('utf-8',errors='replace')}


def code_from(text):
    candidates=[]
    for match in re.finditer(r'```(?:cpp|c\+\+|cxx)[^\n]*\n',text,re.I):
        end=text.find('```',match.end())
        code=text[match.end():end if end>=0 else len(text)]
        if re.search(r'\bmain\s*\(',code):candidates.append(code)
    return candidates[-1] if candidates else None


def test_eligible(problem):
    fmt=problem.get('output_format') or ''
    if problem.get('generated_checker'):return False,'custom checker not validated'
    if problem.get('interaction_format'):return False,'interaction/hack adapter needs review'
    if re.search(r'\b(any|permutation|indices|sequence|coordinates|possible solutions)\b',fmt,re.I):
        return False,'output may not be unique'
    if not re.search(r'(single|one) integer',fmt,re.I):return False,'scalar integer output not established'
    tests=problem.get('official_tests') or []
    if not tests:return False,'no saved official tests'
    if any(not re.fullmatch(r'\s*-?\d+(?:\s+-?\d+)*\s*',t.get('output') or '') for t in tests):
        return False,'noninteger expected output'
    return True,None


def assess(problem,response,split):
    raw=response['raw'];text=raw['message']['content'];code=code_from(text)
    result={'id':problem['id'],'split':split,'verdict':'unverified',
            'generation_done_reason':raw.get('done_reason'),'saved_tests_passed':0,
            'saved_tests_total':len(problem.get('official_tests') or []),
            'official_tests_marked_complete':bool(problem.get('official_tests_complete'))}
    if not code:
        result['reason']='No extractable C++ main program';return result
    if not problem.get('input_format') or re.search(r'\bQ#\b|QSharp|namespace Solution',problem.get('description') or ''):
        result['reason']='Nonstandard task interface needs review';return result
    with tempfile.TemporaryDirectory(prefix='cfjudge_') as work:
        work=Path(work);(work/'source.cpp').write_text(code,encoding='utf-8')
        result['selected_code_sha256']=sha(work/'source.cpp')
        build=run(sandbox(['--bind',str(work),'/work','--chdir','/work'],
                  ['/usr/bin/g++','-std=c++17','-O2','-pipe','source.cpp','-o','program']),30)
        result['compile']={'exit':build['exit'],'timeout':build['timeout'],'stderr':build['stderr'][:12000]}
        if build['timeout']:
            result.update(verdict='resource_limit',reason='compilation wall limit');return result
        if build['exit']:
            if 'bwrap:' in build['stderr']:raise RuntimeError(build['stderr'])
            result.update(verdict='compile_error',reason='selected C++17 candidate failed compilation');return result
        eligible,reason=test_eligible(problem)
        if not eligible:
            result['reason']=reason;return result
        for i,test in enumerate(problem['official_tests']):
            trial=run(sandbox(['--ro-bind',str(work/'program'),'/program','--chdir','/tmp'],['/program']),10,
                      test['input'].encode())
            failure={'index':i,'input_sha256':hashlib.sha256(test['input'].encode()).hexdigest(),
                     'expected':test['output'][:16000],'actual':trial['stdout'][:16000],
                     'stderr':trial['stderr'][:4000],'exit':trial['exit'],'timeout':trial['timeout']}
            if trial['timeout']:
                result.update(verdict='resource_limit',failure=failure);return result
            if trial['exit']:
                if 'bwrap:' in trial['stderr']:raise RuntimeError(trial['stderr'])
                result.update(verdict='runtime_error',failure=failure);return result
            try:
                actual=[int(x) for x in trial['stdout'].split()]
                expected=[int(x) for x in test['output'].split()]
                same=actual==expected
            except ValueError:same=False
            if not same:
                result.update(verdict='failed_saved_test',failure=failure);return result
            result['saved_tests_passed']+=1
        result['verdict']='passed_available_tests';return result


def main():
    ROOT.mkdir(exist_ok=True)
    lock=open(ROOT/'run.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state={'status':'preparing','completed':0,'started':time.time(),'counts':{}}
    atomic('state.json',state)
    try:
        assert subprocess.run(sandbox([],['/usr/bin/true']),capture_output=True).returncode==0
        paths=[DATA/f'{s}_full.jsonl' for s in ('train','test')]+[DATA/'qwen_answers_v1'/f'{s}_responses.jsonl' for s in ('train','test')]
        config={'policy':POLICY,'input_sha256':{str(p.relative_to(DATA)):sha(p) for p in paths},'script_sha256':sha(Path(__file__)),
                'compiler_version':subprocess.check_output(['g++','--version'],text=True).splitlines()[0]}
        if (ROOT/'manifest.json').exists():assert json.loads((ROOT/'manifest.json').read_text())==config
        else:atomic('manifest.json',config)
        for split in ('train','test'):
            problems={r['id']:r for r in map(json.loads,(DATA/f'{split}_full.jsonl').open(encoding='utf-8'))}
            done=set();output=ROOT/f'{split}_verdicts.jsonl'
            if output.exists():
                for line in output.open(encoding='utf-8'):
                    r=json.loads(line);done.add(r['id']);state['counts'][r['verdict']]=state['counts'].get(r['verdict'],0)+1;state['completed']+=1
            with output.open('a',encoding='utf-8') as sink:
                for line in (DATA/'qwen_answers_v1'/f'{split}_responses.jsonl').open(encoding='utf-8'):
                    row=json.loads(line)
                    if row['id'] in done:continue
                    if time.time()-state['started']>86400-60:raise TimeoutError('24-hour wall cap')
                    result=assess(problems[row['id']],row,split)
                    sink.write(json.dumps(result,ensure_ascii=False)+'\n');sink.flush();os.fsync(sink.fileno())
                    state['counts'][result['verdict']]=state['counts'].get(result['verdict'],0)+1
                    state.update(status='running',completed=state['completed']+1,last_id=row['id'],updated=time.time());atomic('state.json',state)
        state.update(status='complete',updated=time.time());atomic('state.json',state)
    except Exception as exc:
        state.update(status='failed',error=repr(exc),updated=time.time());atomic('state.json',state);raise


if __name__=='__main__':main()
