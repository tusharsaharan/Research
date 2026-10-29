"""Download the selected local Qwen models and run bounded Hinglish smoke prompts.

Use a persistent session. Progress streams from Ollama; there is no polling
loop, paid provider API, benchmark tuning, or automatic failed-model retry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

MODELS = ('qwen3.5:4b', 'qwen3.6:35b', 'qwen3.8:27b', 'qwen3.5:9b')
OPTIONS = dict(num_ctx=4096, num_predict=128, temperature=0, seed=42)
PROMPTS = (
    'Sirf final number likho: 17 aur 25 ka sum kya hai?',
    "Is sentence ko natural Hinglish mein likho: 'The train leaves at six in the evening.'",
    'Context: Riya ka bag laal hai. Aman ka bag neela hai. Sawaal: Riya ka bag kis rang ka hai? Sirf rang likho.',
)


class LocalOllama:
    def __init__(self, host):
        parsed = urlsplit(host)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username):
            raise ValueError('Use a loopback Ollama HTTP endpoint')
        self.host = host.rstrip('/')
        # Local generation traffic must never pass through the college proxy.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def open(self, route, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.host + '/api/' + route, data=payload,
                                     headers={'Content-Type': 'application/json'})
        return self.opener.open(req, timeout=900)

    def json(self, route, body=None):
        with self.open(route, body) as response:
            result = json.load(response)
        if result.get('error'):
            raise RuntimeError(result['error'])
        return result

    def pull(self, model, progress):
        success = False
        with self.open('pull', dict(model=model, stream=True)) as response:
            for raw in response:
                if not raw.strip():
                    continue
                event = json.loads(raw)
                if event.get('error'):
                    raise RuntimeError(event['error'])
                progress(event)
                success = event.get('status') == 'success'
        if not success:
            raise RuntimeError('Pull stream ended without a success receipt')


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def run(host, out, resume=False):
    api = LocalOllama(host)
    config = dict(host=api.host, models=list(MODELS), options=OPTIONS, prompts=list(PROMPTS),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'state.json'
    if path.exists():
        state = json.loads(path.read_text(encoding='utf-8'))
        if not resume or state['config'] != config:
            raise ValueError('Existing job: use --resume with the identical configuration')
    else:
        state = dict(config=config, version=api.json('version'), status='running', models={},
                     note='Engineering smoke checks only; no compressor accuracy estimates.')
    save(path, state)
    for model in MODELS:
        if state['models'].get(model, {}).get('status') == 'ready':
            continue
        item = state['models'][model] = dict(status='downloading', tests=[])
        save(path, state)
        print(model + ': downloading', flush=True)
        last_saved = 0

        def progress(event):
            nonlocal last_saved
            item['pull_progress'] = event
            if time.monotonic() - last_saved >= 30 or event.get('status') == 'success':
                save(path, state)
                print(model + ': ' + json.dumps(event), flush=True)
                last_saved = time.monotonic()

        try:
            api.pull(model, progress)
            tags = api.json('tags')['models']
            item['installed'] = next(row for row in tags if row.get('name') == model)
            shown = api.json('show', dict(model=model))
            item['details'] = shown.get('details', {})
            item['status'] = 'testing'
            save(path, state)
            for prompt in PROMPTS:
                response = api.json('generate', dict(model=model, prompt=prompt, stream=False,
                    think=False, keep_alive='2m', options=OPTIONS))
                if not response.get('done') or not response.get('response', '').strip():
                    raise RuntimeError('Generation did not produce a completed nonempty answer')
                item['tests'].append(dict(prompt=prompt, **{key: response.get(key) for key in (
                    'response', 'done_reason', 'eval_count', 'eval_duration', 'prompt_eval_count',
                    'prompt_eval_duration', 'load_duration', 'total_duration')}))
                save(path, state)
            item['loaded'] = api.json('ps').get('models', [])
            item['gpu_used'] = any(m.get('name') == model and m.get('size_vram', 0) > 0 for m in item['loaded'])
            if not item['gpu_used']:
                raise RuntimeError('Smoke answers completed but GPU use was not confirmed')
            item['status'] = 'ready'
            print(model + ': installed; Hinglish generation and GPU use confirmed', flush=True)
        except Exception as error:
            item.update(status='failed', error=str(error))
            print(model + ': failed: ' + str(error), flush=True)
        finally:
            try:
                api.json('generate', dict(model=model, keep_alive=0))
            except Exception:
                pass
            save(path, state)
    state['status'] = 'complete' if all(item['status'] == 'ready' for item in state['models'].values()) else 'partial'
    save(path, state)
    print('Qwen preparation: ' + state['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='http://127.0.0.1:11435')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    run(args.host, args.out, args.resume)
