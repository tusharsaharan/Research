"""Pinned, resumable raw-response collection; run on the Linux GPU host."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path('/home/user/hinglish-research/gsm8k_20261116')
ROOT.mkdir(parents=True, exist_ok=True)
API = 'http://127.0.0.1:11435/api/'
MODEL = 'qwen3.6:35b'
SYSTEM = 'Solve the math word problem step by step. End with #### followed by the final numeric answer.'


def request(url, payload=None, timeout=600):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def atomic(name, value):
    temp = ROOT / (name + '.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temp, ROOT / name)


def main():
    lock = open('/home/user/hinglish-research/gpu-campaign.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    started = time.time()
    state = {'status': 'preparing', 'completed': 0, 'started': started}
    atomic('state.json', state)
    try:
        manifest_path = ROOT / 'manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            revision = request('https://huggingface.co/api/datasets/openai/gsm8k')['sha']
            model = next(m for m in request(API + 'tags')['models'] if m['name'] == MODEL)
            manifest = {'dataset': 'openai/gsm8k', 'revision': revision, 'config': 'main',
                        'model': model, 'system': SYSTEM, 'think': False,
                        'options': {'temperature': 0, 'seed': 42, 'num_ctx': 8192, 'num_predict': 2048},
                        'max_seconds': 259200, 'splits': {}}
            for split, expected in [('train', 7473), ('test', 1319)]:
                url = f'https://huggingface.co/datasets/openai/gsm8k/resolve/{revision}/main/{split}-00000-of-00001.parquet'
                with urllib.request.urlopen(url, timeout=180) as response:
                    raw = response.read()
                (ROOT / (split + '.parquet')).write_bytes(raw)
                manifest['splits'][split] = {'count': expected, 'sha256': hashlib.sha256(raw).hexdigest(), 'url': url}
            atomic('manifest.json', manifest)
        current = next(m for m in request(API + 'tags')['models'] if m['name'] == MODEL)
        assert current['digest'] == manifest['model']['digest'], 'Model changed'
        import pyarrow.parquet as pq
        done = set()
        output = ROOT / 'responses.jsonl'
        if output.exists():
            for line in output.read_text().splitlines():
                done.add(json.loads(line)['id'])
        with output.open('a', encoding='utf-8') as sink:
            for split, spec in manifest['splits'].items():
                path = ROOT / (split + '.parquet')
                assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256']
                rows = pq.read_table(path).to_pylist()
                assert len(rows) == spec['count']
                for i, row in enumerate(rows):
                    item = f'{split}-{i:05d}'
                    if item in done:
                        continue
                    if time.time() - started > manifest['max_seconds'] - 600:
                        raise TimeoutError('72-hour compute cap reached; explicit resume required')
                    payload = {'model': MODEL, 'stream': False, 'think': manifest['think'],
                               'options': manifest['options'], 'messages': [
                                   {'role': 'system', 'content': manifest['system']},
                                   {'role': 'user', 'content': row['question']}]}
                    before = time.time()
                    reply = request(API + 'chat', payload)
                    sink.write(json.dumps({'id': item, 'question': row['question'], 'raw': reply,
                                           'elapsed_seconds': time.time() - before}, ensure_ascii=False) + '\n')
                    sink.flush()
                    os.fsync(sink.fileno())
                    done.add(item)
                    state.update(status='running', completed=len(done), last_id=item, updated=time.time())
                    atomic('state.json', state)
        state.update(status='complete', completed=len(done), updated=time.time())
        atomic('state.json', state)
    except Exception as exc:
        state.update(status='failed', error=repr(exc), updated=time.time())
        atomic('state.json', state)
        raise


if __name__ == '__main__':
    main()
