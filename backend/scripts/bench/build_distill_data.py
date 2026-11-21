"""Build grouped, exposed-development ordinal supervision from saved ranks.

Choices, gold and downstream model answers never enter scorer examples.
Teacher failures are excluded explicitly. No model inference or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from compressor_artifacts import digest, records, save, verify_archive
from gateway.modules.m2_compressor.qwen_evidence import RANK_SYSTEM, source_units, validate_ranking


def build(data: Path, output: Path) -> dict:
    hashes = verify_archive(data, ['inputs.jsonl', 'rankings.jsonl', 'manifest.json'])
    inputs = {row['uid']: row for row in records(data / 'inputs.jsonl')}
    if len(inputs) != 900:
        raise ValueError('Expected the frozen 900-item exposed development pool')
    if output.exists():
        raise ValueError('Output exists; inspect it instead of overwriting')
    output.mkdir(parents=True)
    counts, excluded, seen = Counter(), Counter(), set()
    families = {'train': set(), 'development': set()}
    paths = {split: output / f'compressor_distill_{split}.jsonl' for split in families}
    streams = {split: path.open('x', encoding='utf-8', newline='\n') for split, path in paths.items()}
    try:
        for rank in records(data / 'rankings.jsonl'):
            if rank['method'] != 'bqwen35b_span':
                continue
            uid = rank['uid']
            if uid in seen or uid not in inputs:
                raise ValueError('Duplicate or unknown teacher item: ' + uid)
            seen.add(uid)
            if rank.get('error') or rank.get('response', {}).get('generation_error'):
                excluded['teacher_failure_or_lexical_fallback'] += 1
                continue
            row = inputs[uid]
            units = source_units(row['context'])
            order = validate_ranking(json.dumps({'ranking': rank['order']}), len(units))
            prompt = json.loads(rank['prompt'])
            if rank['system'] != RANK_SYSTEM or prompt['question'] != row['question']:
                raise ValueError('Teacher prompt mismatch: ' + uid)
            if prompt['spans'] != [{'id': i, 'text': text} for i, text in enumerate(units)]:
                raise ValueError('Teacher segmentation differs from frozen source: ' + uid)
            group = row['passage_group']
            fraction = int(hashlib.sha256(f'20261116|{group}'.encode()).hexdigest(), 16) / 2**256
            split = 'train' if fraction < 0.8 else 'development'
            families[split].add(group)
            result = dict(uid=uid, passage_group=group, context=row['context'], question=row['question'],
                          spans=units, teacher_order=order, teacher_model=rank['model'],
                          teacher_prompt_sha256=rank['prompt_sha256'],
                          historically_exposed=True, supervision='ordinal teacher order; not human evidence labels')
            streams[split].write(json.dumps(result, ensure_ascii=False) + '\n')
            counts[split + '_items'] += 1
            counts[split + '_spans'] += len(units)
    finally:
        for stream in streams.values():
            stream.close()
    if seen != set(inputs):
        raise ValueError('Saved teacher rankings do not cover all input IDs')
    if families['train'] & families['development']:
        raise ValueError('Source passage leakage')
    manifest = dict(status='complete', seed=20261116, train_share=0.8, counts=dict(counts),
                    source_groups={key: len(value) for key, value in families.items()},
                    source_group_overlap=0, excluded=dict(excluded), sources=hashes,
                    outputs={path.name: digest(path) for path in paths.values()},
                    script_sha256=digest(Path(__file__)),
                    scope='Historically exposed development data; no sealed/fresh/test split. License review pending redistribution.',
                    label_inputs='Teacher rank permutation only; no gold/options/answers or AI translation labels.')
    save(output / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.output), indent=2))
