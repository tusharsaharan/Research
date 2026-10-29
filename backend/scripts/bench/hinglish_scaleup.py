"""Full-pool Hinglish evaluation plus separately labelled public-text stress checks.

One bounded GPU workflow; immutable source/data/model fingerprints, no retries.
The selected ranker is frozen from the earlier three complete development runs.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import re
import shutil
import subprocess
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from common import BACKEND, read_jsonl
from local_qwen_campaign import (
    RANK_SYSTEM,
    BoundedOllama,
    append,
    checked_generate,
    digest,
    fingerprint,
    gpu_receipt,
    lexical_order,
    pack_ranked,
    ranking_request,
    report,
    run,
    save,
    utc,
    validate_ranking,
)
from prepare_hinglish_scaleup import prepare as prepare_pool

LARGE = 'microsoft/llmlingua-2-xlm-roberta-large-meetingbank'
LARGE_REVISION = 'ebaba9b0e874dadd3003ffcff828e4397e568089'
BASELINES = ['bm25_strict', 'llml2L_strict', 'bhybrid_char_clause']
RATES = [0.5, 0.33, 0.75, 0.25]


def prepare(items, parent, stress, out):
    prepare_pool(items, parent, out)
    for name, path in [('tokenizer.json', parent / 'tokenizer.json'), ('stress_inputs.jsonl', stress),
                       ('selection_report.json', parent / 'report.json'),
                       ('stress_provenance.json', stress.with_suffix('.receipt.json')),
                       ('COMI_LICENSE.txt', stress.parent / 'public_comi/LICENSE.txt')]:
        shutil.copy2(path, out / name)
    root = BACKEND.parent
    files = subprocess.check_output(['git', 'ls-files', 'backend/src', 'backend/scripts/bench',
                                     'backend/scripts/ollama_qwen_models.py'], cwd=root, text=True).splitlines()
    if str(Path(__file__).relative_to(root)).replace('\\', '/') not in files:
        raise ValueError('Commit workflow source before freezing')
    with zipfile.ZipFile(out / 'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            if name.endswith('.py') and (root / name).is_file():
                archive.write(root / name, name)
    spec = json.loads((parent / 'manifest.json').read_text(encoding='utf-8'))
    rows = read_jsonl(out / 'inputs.jsonl')
    spec.update(created=utc(), study='Full existing Hinglish QA pool; exposed development expansion',
        input_count=len(rows), rates=RATES, rankers={'bqwen35b_span': 'qwen3.6:35b'},
        methods=['original'] + [f'{m}@{r}' for m in [*BASELINES, 'bqwen35b_span', 'bspan_bm25'] for r in RATES],
        max_seconds=57600, model_max_seconds=12600, ranker_max_seconds=3600,
        record_invalid_answers=True, llml2_model=LARGE, llml2_revision=LARGE_REVISION,
        failure_policy='Persist raw capped/invalid generations; score as failure without retry; do not abort model.',
        selection='35B span ranker selected on three complete pilot answer models only; 35B partial excluded.',
        overall_wall_cap_seconds=86400, stress_contexts=len(read_jsonl(stress)),
        source_provenance='COMI-LINGUA f02e16a1a513cdf29cfaf20b19c007dd89d8083a; LICENSE.txt CC-BY-SA-4.0; '
                          'Roman originals and derived romanizations are reported separately; stress is not gold QA.',
        files={name: digest(out / name) for name in ('inputs.jsonl', 'stress_inputs.jsonl', 'tokenizer.json',
                            'source.zip', 'selection_report.json', 'stress_provenance.json', 'COMI_LICENSE.txt')},
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip())
    spec['expected_answers_per_model'] = len(rows) * len(spec['methods'])
    save(out / 'workflow_manifest.json', spec)
    print(json.dumps(dict(inputs=len(rows), stress=spec['stress_contexts'],
                          planned_answers=4 * spec['expected_answers_per_model'])))


def verify(data, spec):
    for name, expected in spec['files'].items():
        if digest(data / name) != expected:
            raise ValueError(f'Frozen file changed: {name}')
    with zipfile.ZipFile(data / 'source.zip') as archive:
        for name in archive.namelist():
            if archive.read(name) != (BACKEND.parent / name).read_bytes():
                raise ValueError(f'Frozen source changed: {name}')


def baseline(data, spec, count, deadline, state):
    import torch
    from baselines2 import bm25_select
    from huggingface_hub import snapshot_download

    from gateway.modules.m2_compressor.hinglish_budget import compress_ablation, strict_prefix
    from gateway.modules.m2_compressor.llmlingua2 import LLMLingua2Compressor

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required')
    model_path = snapshot_download(LARGE, revision=LARGE_REVISION,
        allow_patterns=['*.json', '*.txt', '*.model', '*.safetensors', '*.bin'])
    lingua = LLMLingua2Compressor(model_path, device='cuda:0')
    rows = read_jsonl(data / 'inputs.jsonl')
    path = data / 'baseline_variants.jsonl'
    if path.exists():
        raise ValueError('Existing baseline output; do not overwrite')
    for i, row in enumerate(rows):
        text, question = row['context'], row['question']
        original = count(text)
        for method, rate in [('original', 1)] + [(m, r) for m in BASELINES for r in spec['rates']]:
            if time.monotonic() >= deadline:
                raise TimeoutError('Baseline stage time cap')
            started = time.monotonic()
            if method == 'original':
                compressed = text
            elif method == 'bm25_strict':
                compressed = bm25_select(text, question, rate, count)
            elif method == 'bhybrid_char_clause':
                compressed = compress_ablation(text, question, rate, count, None,
                                                characters=True, clauses=True).text
            else:
                compressed = lingua._ensure().compress_prompt(text, rate=rate,
                    force_tokens=['\n', '?', '.'])['compressed_prompt']
            target = original if rate == 1 else max(1, math.floor(original * rate))
            before = compressed
            compressed = strict_prefix(compressed, target, count)
            actual = count(compressed)
            label = method if rate == 1 else f'{method}@{rate}'
            append(path, dict(key=row['uid'] + '|' + label, uid=row['uid'], method=label, text=compressed,
                original_tokens=original, actual_tokens=actual, target_tokens=target, budget_met=actual <= target,
                kept_ratio=actual / max(1, original), compression_seconds=time.monotonic() - started,
                detail=dict(budget_enforced=compressed != before), config=fingerprint(spec)))
        state['baseline_items'] = i + 1
        if (i + 1) % 25 == 0:
            save(data / 'workflow.json', state)
            print(f'Baseline compression: {i + 1}/{len(rows)}', flush=True)
    save(data / 'baseline_runtime.json', dict(gpu=torch.cuda.get_device_name(), model=LARGE,
                                              revision=LARGE_REVISION, path=model_path))
    del lingua
    gc.collect()
    torch.cuda.empty_cache()


def stress_checks(data, spec, count, deadline, state):
    api = BoundedOllama(spec['host'])
    totals = defaultdict(Counter)
    model = 'qwen3.6:35b'
    gpu = None
    for i, row in enumerate(read_jsonl(data / 'stress_inputs.jsonl')):
        if time.monotonic() + 300 >= deadline:
            raise TimeoutError('Overall stress time cap')
        passage = row['context']
        units, prompt, schema = ranking_request(passage, 'Is text ka main point kya hai?')
        fallback = None
        response = None
        if len(units) == 1:
            order = [0]  # The unique permutation; no model inference needed.
        else:
            response = checked_generate(api, model, RANK_SYSTEM, prompt, deadline, schema, record_invalid=True)
            if gpu is None:
                gpu = gpu_receipt(api, model)
            try:
                if response.get('generation_error'):
                    raise ValueError(response['generation_error'])
                order = validate_ranking(response['response'], len(units))
            except ValueError as exc:
                order, fallback = lexical_order(units, 'Is text ka main point kya hai?'), str(exc)
        append(data / 'stress_rankings.jsonl', dict(uid=row['uid'], order=order, error=fallback, response=response))
        for method, indices in [('bqwen35b_span', order),
                                ('bspan_bm25', lexical_order(units, 'Is text ka main point kya hai?'))]:
            for rate in spec['rates']:
                packed = pack_ranked(passage, units, indices, rate, count)
                before = Counter(re.findall(r'\b(?:nahi|nahin|nhi|not|never|no|\d+)\b', passage.lower()))
                after = Counter(re.findall(r'\b(?:nahi|nahin|nhi|not|never|no|\d+)\b', packed['text'].lower()))
                lost = sum((before - after).values())
                key = f"{row['stratum']}|{method}@{rate}"
                totals[key].update(items=1, budget_misses=int(not packed['budget_met']),
                    empty=int(not packed['text']), clipped=int(packed['detail']['budget_enforced']),
                    guard_occurrences=sum(before.values()), lost_guard_occurrences=lost,
                    original_tokens=packed['original_tokens'], output_tokens=packed['actual_tokens'])
                append(data / 'stress_variants.jsonl', dict(uid=row['uid'], stratum=row['stratum'],
                    method=method, rate=rate, lost_guard_occurrences=lost, **packed))
        state['stress_items'] = i + 1
        if (i + 1) % 100 == 0:
            save(data / 'workflow.json', state)
            print(f'Stress: {i + 1}/{spec["stress_contexts"]}', flush=True)
    api.json('generate', dict(model=model, keep_alive=0))
    save(data / 'stress_report.json', dict(complete=True, totals=dict(totals), gpu=gpu,
        note='Surface guard-loss diagnostics, not semantic accuracy; original and derived texts separate.',
        sources={f: digest(data / f)
                 for f in ('stress_inputs.jsonl', 'stress_variants.jsonl', 'stress_rankings.jsonl')},
        script_sha256=digest(__file__)))


def run_workflow(data):
    from tokenizers import Tokenizer
    spec = json.loads((data / 'workflow_manifest.json').read_text(encoding='utf-8'))
    verify(data, spec)
    if (data / 'workflow.json').exists():
        raise ValueError('Existing workflow: explicit repair required, no automatic retry')
    tokenizer = Tokenizer.from_file(str(data / 'tokenizer.json'))

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    state = dict(status='running', stage='baselines', started=utc(), baseline_items=0, stress_items=0,
                 workflow_manifest_sha256=digest(data / 'workflow_manifest.json'))
    save(data / 'workflow.json', state)
    deadline = time.monotonic() + 85800
    try:
        baseline(data, spec, count, min(deadline, time.monotonic() + 10800), state)
        manifest = dict(spec, files={**spec['files'],
                                    'baseline_variants.jsonl': digest(data / 'baseline_variants.jsonl')})
        save(data / 'manifest.json', manifest)
        state['stage'] = 'ranking_and_answers'
        save(data / 'workflow.json', state)
        run(data)
        state['stage'] = 'stress'
        save(data / 'workflow.json', state)
        stress_checks(data, spec, count, deadline, state)
        report(data)
        qa_complete = json.loads((data / 'report.json').read_text(encoding='utf-8'))['complete']
        state['status'] = 'complete' if qa_complete else 'partial'
    except Exception as exc:
        state.update(status='failed', error=str(exc))
        raise
    finally:
        state['updated'] = utc()
        save(data / 'workflow.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--items', type=Path)
    parser.add_argument('--stress', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.items, args.parent, args.stress, args.data)
    else:
        run_workflow(args.data)
