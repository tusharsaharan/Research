"""One frozen Qwen answer per problem; never reads full solution/test records."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

DATA = Path('/home/user/hinglish-research/codeforces700_20261116')
ROOT = DATA / 'qwen_answers_v1'
MODEL = 'qwen3.6:35b'
SYSTEM = ('Solve the given competitive programming problem. Explain the algorithm, '
          'justify its correctness, and give time and space complexity. Provide a complete, '
          'working C++17 solution in one fenced cpp code block, reading standard input and '
          'writing standard output. Respect all stated constraints. Be concise so the full '
          'implementation fits in your answer.')
FIELDS = ('title', 'description', 'input_format', 'output_format', 'interaction_format',
          'note', 'examples', 'time_limit', 'memory_limit')
OPTIONS = {'temperature': 0, 'seed': 42, 'num_ctx': 32768, 'num_predict': 8192}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def api(endpoint, payload=None):
    req = urllib.request.Request('http://127.0.0.1:11435/api/' + endpoint,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as reply:
        return json.load(reply)


def atomic(name, obj):
    tmp = ROOT / (name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    os.replace(tmp, ROOT / name)


def main():
    ROOT.mkdir(exist_ok=True)
    lock = open('/home/user/hinglish-research/gpu-campaign.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state = {'status': 'preparing', 'completed': 0, 'started': time.time()}
    atomic('state.json', state)
    try:
        source = json.loads((DATA / 'manifest.json').read_text())
        jobs = []
        hashes = {}
        for split, expected in [('train', 500), ('test', 200)]:
            path = DATA / f'{split}_problems.jsonl'
            hashes[path.name] = sha(path)
            assert hashes[path.name] == source['outputs'][path.name]
            rows = [json.loads(line) for line in path.open(encoding='utf-8')]
            assert len(rows) == expected
            for row in rows:
                prompt = json.dumps({k: row.get(k) for k in FIELDS}, ensure_ascii=False)
                # Conservative UTF-8 byte bound reserves output and chat-template space.
                if len(prompt.encode()) + len(SYSTEM.encode()) > 23000:
                    raise ValueError(f'Prompt needs context review before any inference: {row["id"]}')
                jobs.append({'id': row['id'], 'split': split, 'prompt': prompt})
        assert len({j['id'] for j in jobs}) == 700
        config = {'model': MODEL, 'digest': next(m['digest'] for m in api('tags')['models'] if m['name'] == MODEL),
                  'system': SYSTEM, 'options': OPTIONS, 'think': False, 'input_hashes': hashes,
                  'source_revision': source['revision'], 'script_sha256': sha(Path(__file__)),
                  'max_seconds': 259200, 'retry_policy': 'none; transport failure halts; no continuation',
                  'prompt_fields': FIELDS}
        manifest = ROOT / 'manifest.json'
        if manifest.exists():
            assert json.loads(manifest.read_text()) == json.loads(json.dumps(config)), 'Frozen config changed'
        else:
            atomic('manifest.json', config)
            with (ROOT / 'prompts.jsonl').open('w', encoding='utf-8') as out:
                for job in jobs:
                    out.write(json.dumps(job, ensure_ascii=False) + '\n')
        done = set()
        for split in ('train', 'test'):
            path = ROOT / f'{split}_responses.jsonl'
            if path.exists():
                for line in path.open(encoding='utf-8'):
                    r = json.loads(line)
                    assert r['id'] not in done
                    done.add(r['id'])
        state['completed'] = len(done)
        for job in jobs:
            if job['id'] in done:
                continue
            if time.time() - state['started'] > config['max_seconds'] - 900:
                raise TimeoutError('72-hour cap reached')
            before = time.time()
            reply = api('chat', {'model': MODEL, 'stream': False, 'think': False,
                'options': OPTIONS, 'messages': [{'role': 'system', 'content': SYSTEM},
                                               {'role': 'user', 'content': job['prompt']}]})
            record = {'id': job['id'], 'split': job['split'],
                      'prompt_sha256': hashlib.sha256(job['prompt'].encode()).hexdigest(),
                      'raw': reply, 'elapsed_seconds': time.time() - before}
            with (ROOT / f'{job["split"]}_responses.jsonl').open('a', encoding='utf-8') as out:
                out.write(json.dumps(record, ensure_ascii=False) + '\n')
                out.flush()
                os.fsync(out.fileno())
            done.add(job['id'])
            state.update(status='running', completed=len(done), last_id=job['id'],
                         last_split=job['split'], updated=time.time())
            atomic('state.json', state)
        state.update(status='complete', updated=time.time())
        atomic('state.json', state)
    except Exception as exc:
        state.update(status='failed', error=repr(exc), updated=time.time())
        atomic('state.json', state)
        raise


if __name__ == '__main__':
    main()
