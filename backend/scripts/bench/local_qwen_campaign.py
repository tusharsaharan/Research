"""Frozen, bounded Hinglish development campaign on an existing local Ollama.

No downloads, provider calls, retries or polling. Reuse Kaggle variants, add
source-span rankers, then answer all variants with each installed Qwen model.
Token caps use the fingerprinted Qwen2.5 reference tokenizer. Across Qwen
versions this is a fixed-text transfer test, NOT matched serving-token caps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from common import BACKEND, read_jsonl

sys.path.insert(0, str(BACKEND / 'scripts'))
from grade import extract_letter
from hinglish_research_audit import paired_interval, passage_key
from ollama_qwen_models import MODELS, LocalOllama, save

from gateway.modules.m2_compressor.qwen_evidence import (
    RANK_SYSTEM,
    lexical_order,
    pack_ranked,
    ranking_request,
    validate_ranking,
)

RANKERS = {'bqwen4b_span': 'qwen3.5:4b', 'bqwen35b_span': 'qwen3.6:35b'}
ANSWER_SYSTEM = 'Answer the multiple-choice question. Reply with only the correct option letter.'
OPTIONS = dict(num_ctx=8192, num_predict=128, temperature=0, seed=42)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def utc():
    return datetime.now(UTC).isoformat()


def append(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')
        stream.flush()


def answer_prompt(row, text):
    return (f"Passage: {text}\n\nQuestion: {row['question']}\n\n"
            + '\n'.join(f'{letter}) {option}' for letter, option in zip('ABCD', row['options'], strict=True)))


def checked_generate(api, model, system, prompt, deadline, schema=None, record_invalid=False):
    # UTF-8 byte length is a conservative token upper bound for these BPE
    # models; reserve 512 tokens for chat-template overhead, without truncation.
    if len((system + prompt).encode('utf-8')) + OPTIONS['num_predict'] + 512 >= OPTIONS['num_ctx']:
        raise ValueError('Prompt exceeds conservative context bound; refusing truncation')
    if time.monotonic() + 300 > deadline:
        raise TimeoutError('Time cap: reserving up to 300 seconds for the next request')
    body = dict(model=model, system=system, prompt=prompt, stream=False,
                think=False, keep_alive='10m', options=OPTIONS)
    if schema is not None:
        body['format'] = schema
    response = api.json('generate', body)
    error = None
    if not response.get('done') or not response.get('response', '').strip():
        error = 'Incomplete or empty generation'
    if response.get('thinking'):
        error = 'Thinking was requested off but reasoning was returned'
    if response.get('done_reason') == 'length':
        error = 'Generation exhausted the output cap'
    if response.get('prompt_eval_count', 0) >= OPTIONS['num_ctx'] - OPTIONS['num_predict']:
        error = 'Possible context truncation'
    if error:
        if not record_invalid:
            raise RuntimeError(error)
        response['generation_error'] = error
    return response


class BoundedOllama(LocalOllama):
    def open(self, route, body=None):
        import urllib.request
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.host + '/api/' + route, data=data,
                                        headers={'Content-Type': 'application/json'})
        return self.opener.open(request, timeout=300)


def gpu_receipt(api, model):
    loaded = api.json('ps').get('models', [])
    match = [r for r in loaded if r.get('name') == model and r.get('size_vram', 0) > 0]
    if not match:
        raise RuntimeError('Model generation did not have confirmed GPU residency')
    return match


def prepare(pilot, out, tokenizer, ready):
    if out.exists():
        raise ValueError('Use a new campaign directory')
    rows = read_jsonl(pilot / 'inputs.jsonl')
    if not rows or any(r['lang'] != 'hinglish' or r['task'] != 'mcq' for r in rows):
        raise ValueError('Hinglish MCQ inputs only')
    old = json.loads((pilot / 'kernel_output/report.json').read_text())
    if not old['complete']:
        raise ValueError('Baseline pilot must be complete')
    installed = json.loads(ready.read_text())['models']
    models = {m: installed[m]['installed']['digest'] for m in MODELS}
    out.mkdir(parents=True)
    for src, name in ((pilot / 'inputs.jsonl', 'inputs.jsonl'),
                      (pilot / 'kernel_output/variants.jsonl', 'baseline_variants.jsonl'),
                      (tokenizer, 'tokenizer.json')):
        shutil.copy2(src, out / name)
    root = BACKEND.parent
    files = subprocess.check_output(['git', 'ls-files', 'backend/src', 'backend/scripts/bench',
                                     'backend/scripts/ollama_qwen_models.py'], cwd=root, text=True).splitlines()
    files = [f for f in files if f.endswith('.py') and (root / f).is_file()]
    required = [str(Path(__file__).relative_to(root)).replace('\\', '/'),
                'backend/src/gateway/modules/m2_compressor/qwen_evidence.py']
    if any(f not in files for f in required):
        raise ValueError('Commit the new campaign source before preparing it')
    with zipfile.ZipFile(out / 'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            archive.write(root / name, name)
    baseline = read_jsonl(out / 'baseline_variants.jsonl')
    methods = sorted({v['method'] for v in baseline})
    methods += [f'{name}@{rate}' for name in [*RANKERS, 'bspan_bm25'] for rate in (0.5, 0.33)]
    manifest = dict(created=utc(), study='Exploratory Hinglish-only local Qwen evidence campaign',
        models=models, rankers=RANKERS, methods=methods, rates=[0.5, 0.33],
        input_count=len(rows), expected_answers_per_model=len(rows) * len(methods),
        options=OPTIONS, think=False, max_seconds=14400, model_max_seconds=2700,
        ranker_max_seconds=1500, host='http://127.0.0.1:11435',
        budget_tokenizer='Qwen/Qwen2.5-3B-Instruct', tokenizer_revision=tokenizer.parent.name,
        budget_scope='Qwen2.5 reference caps; other answer models are fixed-text transfer only',
        ranking_inputs='question and source spans only; no options or gold',
        inference='Previously exposed development data; no confirmatory claim. All Qwen models are one family.',
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        files={f: digest(out / f) for f in ('inputs.jsonl', 'baseline_variants.jsonl', 'tokenizer.json', 'source.zip')})
    save(out / 'manifest.json', manifest)
    print(json.dumps(dict(out=str(out), inputs=len(rows), models=list(models),
                         expected_answers_per_model=manifest['expected_answers_per_model'])))


def validate_data(data, manifest, count):
    for name, expected in manifest['files'].items():
        if digest(data / name) != expected:
            raise ValueError(f'Changed frozen input: {name}')
    source_root = BACKEND.parent
    with zipfile.ZipFile(data / 'source.zip') as archive:
        for name in archive.namelist():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest(source_root / name):
                raise ValueError(f'Changed frozen source: {name}')
    rows = read_jsonl(data / 'inputs.jsonl')
    inputs = {r['uid']: r for r in rows}
    if len(inputs) != len(rows):
        raise ValueError('Duplicate inputs')
    variants = read_jsonl(data / 'baseline_variants.jsonl')
    keys = set()
    for v in variants:
        if v['key'] in keys or v['uid'] not in inputs:
            raise ValueError('Duplicate or foreign variant')
        keys.add(v['key'])
        if count(v['text']) != v['actual_tokens'] or count(inputs[v['uid']]['context']) != v['original_tokens']:
            raise ValueError('Reference tokenizer disagrees with saved pilot counts')
        if v['method'] == 'original' and v['text'] != inputs[v['uid']]['context']:
            raise ValueError('Original context mismatch')
        if v['method'] != 'original' and v['actual_tokens'] > v['target_tokens']:
            raise ValueError('Baseline exceeds reference cap')
    baseline_methods = {v['method'] for v in variants}
    if keys != {uid + '|' + method for uid in inputs for method in baseline_methods}:
        raise ValueError('Unpaired baseline variants')
    return rows, variants


def run(data):
    from tokenizers import Tokenizer
    manifest = json.loads((data / 'manifest.json').read_text())
    tokenizer = Tokenizer.from_file(str(data / 'tokenizer.json'))
    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)
    rows, variants = validate_data(data, manifest, count)
    if (data / 'state.json').exists():
        raise ValueError('Existing run: no automatic retry or overwrite')
    api = BoundedOllama(manifest['host'])
    tags = {m['name']: m['digest'] for m in api.json('tags')['models']}
    if any(tags.get(m) != d for m, d in manifest['models'].items()):
        raise ValueError('Installed model digest differs from frozen model')
    config = fingerprint(manifest)
    state = dict(status='running', started=utc(), config=config, stage='ranking',
                 models={}, rankers={}, version=api.json('version'), manifest_sha256=digest(data / 'manifest.json'))
    save(data / 'state.json', state)
    deadline = time.monotonic() + manifest['max_seconds']
    try:
        for method, model in manifest['rankers'].items():
            part = state['rankers'][method] = dict(status='running', completed=0, fallbacks=0)
            rank_deadline = min(deadline, time.monotonic() + manifest['ranker_max_seconds'])
            for row in rows:
                started = time.monotonic()
                units, prompt, schema = ranking_request(row['context'], row['question'])
                response = checked_generate(api, model, RANK_SYSTEM, prompt, rank_deadline, schema)
                if not part.get('gpu'):
                    part['gpu'] = gpu_receipt(api, model)
                error = None
                try:
                    order = validate_ranking(response['response'], len(units))
                except (ValueError, TypeError) as exc:
                    order, error = lexical_order(units, row['question']), str(exc)
                    part['fallbacks'] += 1
                elapsed = time.monotonic() - started
                append(data / 'rankings.jsonl', dict(uid=row['uid'], method=method, model=model,
                    prompt=prompt, system=RANK_SYSTEM, prompt_sha256=fingerprint([RANK_SYSTEM, prompt]),
                    response=response, order=order, error=error, seconds=elapsed, config=config))
                for rate in manifest['rates']:
                    packed = pack_ranked(row['context'], units, order, rate, count)
                    label = f'{method}@{rate}'
                    variants.append(dict(key=row['uid'] + '|' + label, uid=row['uid'], method=label,
                        **packed, compression_seconds=elapsed, config=config, ranking_fallback=error))
                part['completed'] += 1
                state['updated'] = utc()
                save(data / 'state.json', state)
                if part['completed'] % 20 == 0:
                    print(f'{method}: {part["completed"]}/{len(rows)} ranked', flush=True)
            part['status'] = 'complete'
            api.json('generate', dict(model=model, keep_alive=0))
        for row in rows:
            units, _, _ = ranking_request(row['context'], row['question'])
            order = lexical_order(units, row['question'])
            for rate in manifest['rates']:
                started = time.monotonic()
                packed = pack_ranked(row['context'], units, order, rate, count)
                label = f'bspan_bm25@{rate}'
                variants.append(dict(key=row['uid'] + '|' + label, uid=row['uid'], method=label,
                    **packed, compression_seconds=time.monotonic() - started, config=config))
        with (data / 'variants.jsonl').open('w', encoding='utf-8') as stream:
            for v in variants:
                stream.write(json.dumps(v, ensure_ascii=False) + '\n')
        state['variants_sha256'] = digest(data / 'variants.jsonl')
        inputs = {r['uid']: r for r in rows}
        grouped = defaultdict(list)
        for v in sorted(variants, key=lambda v: (v['uid'], v['method'] != 'original', v['method'])):
            grouped[answer_prompt(inputs[v['uid']], v['text'])].append(v)
        state.update(stage='answers', unique_prompts_per_model=len(grouped))
        for model in manifest['models']:
            part = state['models'][model] = dict(status='running', answers=0, generations=0)
            model_deadline = min(deadline, time.monotonic() + manifest['model_max_seconds'])
            try:
                for prompt, group in grouped.items():
                    response = checked_generate(api, model, ANSWER_SYSTEM, prompt, model_deadline,
                        record_invalid=manifest.get('record_invalid_answers', False))
                    if not part.get('gpu'):
                        part['gpu'] = gpu_receipt(api, model)
                    for v in group:
                        append(data / 'answers.jsonl', dict(key=v['key'], uid=v['uid'], method=v['method'],
                            model=model, content='' if response.get('generation_error') else response['response'],
                            prompt_tokens=response.get('prompt_eval_count'),
                            prompt_sha256=fingerprint([ANSWER_SYSTEM, prompt]), reused_from=group[0]['key'],
                            response=response, config=config))
                    part['answers'] += len(group)
                    part['generations'] += 1
                    state['updated'] = utc()
                    save(data / 'state.json', state)
                    if part['generations'] % 100 == 0:
                        print(f'{model}: {part["answers"]} answers / {part["generations"]} generations', flush=True)
                part['status'] = 'complete'
            except Exception as exc:
                part.update(status='partial' if isinstance(exc, TimeoutError) else 'failed', error=str(exc))
                print(f'{model}: {part["status"]}: {exc}', flush=True)
            finally:
                api.json('generate', dict(model=model, keep_alive=0))
                save(data / 'state.json', state)
                report(data)
        state['status'] = 'complete' if all(p['status'] == 'complete' for p in state['models'].values()) else 'partial'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        state['finished'] = utc()
        save(data / 'state.json', state)
        print(json.dumps(state), flush=True)
    report(data)


def report(data):
    manifest = json.loads((data / 'manifest.json').read_text())
    rows = read_jsonl(data / 'inputs.jsonl')
    variants = {v['key']: v for v in read_jsonl(data / 'variants.jsonl')}
    raw = read_jsonl(data / 'answers.jsonl')
    answers = {(r['model'], r['key']): r for r in raw}
    if len(answers) != len(raw):
        raise ValueError('Duplicate answer records')
    config = fingerprint(manifest)
    if any(a['config'] != config for a in raw):
        raise ValueError('Answer configuration mismatch')
    result = dict(created=utc(), config=config, budget_scope=manifest['budget_scope'],
        inference=manifest['inference'], models={}, comparisons=[], examples=[],
        files={p.name: digest(p) for p in [data / 'manifest.json', data / 'inputs.jsonl',
              data / 'variants.jsonl', data / 'answers.jsonl'] if p.exists()}, analysis_sha256=digest(__file__))
    for model in manifest['models']:
        methods = result['models'][model] = {}
        for method in manifest['methods']:
            pairs = [(r, answers[(model, r['uid'] + '|' + method)]) for r in rows
                     if (model, r['uid'] + '|' + method) in answers]
            accuracy = sum(extract_letter(a['content']) == r['gold'] for r, a in pairs)
            methods[method] = dict(n=len(pairs), expected=len(rows), complete=len(pairs) == len(rows),
                accuracy=accuracy / len(pairs) if pairs else None,
                invalid=sum(extract_letter(a['content']) is None for _, a in pairs),
                reference_budget_misses=sum(not variants[a['key']]['budget_met'] for _, a in pairs),
                mean_context_ratio=(sum(variants[a['key']]['kept_ratio'] for _, a in pairs)
                                    / len(pairs)) if pairs else None,
                mean_compression_seconds=(sum(variants[a['key']].get('compression_seconds', 0)
                    for _, a in pairs) / len(pairs)) if pairs else None,
                mean_generation_seconds=(sum(a['response'].get('total_duration', 0) / 1e9
                    for _, a in pairs) / len(pairs)) if pairs else None,
                mean_output_tokens=(sum(a['response'].get('eval_count', 0)
                    for _, a in pairs) / len(pairs)) if pairs else None)
            originals = [(r, a, answers[(model, r['uid'] + '|original')]) for r, a in pairs
                         if (model, r['uid'] + '|original') in answers]
            originals = [(r, a, o) for r, a, o in originals if a.get('prompt_tokens') and o.get('prompt_tokens')]
            methods[method]['mean_full_prompt_ratio'] = (sum(a['prompt_tokens'] / o['prompt_tokens']
                for _, a, o in originals) / len(originals)) if originals else None
            if rows and 'selection_source_overlap' in rows[0]:
                methods[method]['source_overlap_strata'] = {}
                for overlap in (True, False):
                    subset = [(r, a) for r, a in pairs if r['selection_source_overlap'] == overlap]
                    methods[method]['source_overlap_strata'][str(overlap)] = dict(n=len(subset),
                        accuracy=(sum(extract_letter(a['content']) == r['gold'] for r, a in subset)
                                  / len(subset)) if subset else None)
            if method == 'original':
                continue
            rate = method.rsplit('@', 1)[1]
            references = ['original', f'bm25_strict@{rate}', f'llml2L_strict@{rate}']
            if method.startswith('bqwen'):
                references.append(f'bspan_bm25@{rate}')
            for reference in references:
                paired = [(r, a, answers[(model, r['uid'] + '|' + reference)]) for r, a in pairs
                          if (model, r['uid'] + '|' + reference) in answers]
                if len(paired) != len(rows) or reference == method:
                    continue  # Never select on time-limited subset accuracies.
                deltas = [int(extract_letter(a['content']) == r['gold'])
                          - int(extract_letter(b['content']) == r['gold']) for r, a, b in paired]
                result['comparisons'].append(dict(model=model, method=method, reference=reference,
                    **paired_interval(deltas, [r.get('passage_group', passage_key(r['context']))
                                              for r, _, _ in paired])))
                if rows and 'selection_source_overlap' in rows[0] and method.startswith('bqwen'):
                    for overlap in (True, False):
                        subset = [(r, d) for (r, _, _), d in zip(paired, deltas, strict=True)
                                  if r['selection_source_overlap'] == overlap]
                        result['comparisons'].append(dict(model=model, method=method, reference=reference,
                            selection_source_overlap=overlap,
                            **paired_interval([d for _, d in subset], [r['passage_group'] for r, _ in subset])))
                if method.startswith('bqwen') and reference.startswith('bm25'):
                    for direction in (-1, 1):
                        chosen = [(r, a, b) for (r, a, b), d in zip(paired, deltas, strict=True) if d == direction][:3]
                        for r, a, b in chosen:
                            result['examples'].append(dict(model=model, method=method, reference=reference,
                                direction=direction, input=r, candidate=variants[a['key']], baseline=variants[b['key']],
                                candidate_answer=a['content'], baseline_answer=b['content']))
    result['complete'] = all(s['complete'] for methods in result['models'].values() for s in methods.values())
    save(data / 'report.json', result)
    print(json.dumps(dict(report=str(data / 'report.json'), complete=result['complete'], answers=len(raw))), flush=True)


def preflight(data):
    from tokenizers import Tokenizer
    manifest = json.loads((data / 'manifest.json').read_text())
    tokenizer = Tokenizer.from_file(str(data / 'tokenizer.json'))

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    rows, variants = validate_data(data, manifest, count)
    api = BoundedOllama(manifest['host'])
    results = dict(created=utc(), manifest_sha256=digest(data / 'manifest.json'),
                   validated_variants=len(variants), tests=[])
    row = rows[0]
    for model in manifest['models']:
        response = checked_generate(api, model, ANSWER_SYSTEM,
                                    answer_prompt(row, row['context']), time.monotonic() + 500)
        result = dict(model=model, response=response, gpu=gpu_receipt(api, model))
        if model in manifest['rankers'].values():
            units, prompt, schema = ranking_request(row['context'], row['question'])
            ranked = checked_generate(api, model, RANK_SYSTEM, prompt, time.monotonic() + 500, schema)
            order = validate_ranking(ranked['response'], len(units))
            result.update(ranking=ranked, packed=pack_ranked(row['context'], units, order, 0.5, count))
        results['tests'].append(result)
        save(data / 'preflight.json', results)
        api.json('generate', dict(model=model, keep_alive=0))
        print(model + ': GPU preflight passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run', 'report', 'preflight'])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--pilot', type=Path)
    parser.add_argument('--tokenizer', type=Path)
    parser.add_argument('--ready', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.pilot, args.data, args.tokenizer, args.ready)
    elif args.command == 'run':
        run(args.data)
    elif args.command == 'preflight':
        preflight(args.data)
    else:
        report(args.data)
