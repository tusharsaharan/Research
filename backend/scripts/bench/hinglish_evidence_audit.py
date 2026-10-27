"""Offline, sharded source-integrity/budget audit; no model inference or downloads.

Use a local tokenizer.json explicitly. Output contains full candidate text and
source offsets for manual review. Answer quality remains pending: retaining
complete surface units is not evidence of improved downstream accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from common import BACKEND, in_shard, read_jsonl
from compressor_pilot import EVIDENCE_METHODS, RATES, write_rows
from gateway.modules.m2_compressor.hinglish_evidence import compress_evidence


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(data, out, tokenizer_file, shard, item_ids=()):
    from tokenizers import Tokenizer

    inputs = data / 'inputs.jsonl'
    manifest = json.loads((data / 'manifest.json').read_text(encoding='utf-8'))
    if digest(inputs) != manifest['inputs_sha256']:
        raise ValueError('Pilot input fingerprint mismatch')
    name = shard.replace('/', '_')
    target = out / f'evidence_{name}.jsonl'
    metadata_file = out / f'metadata_{name}.json'
    if target.exists() or metadata_file.exists():
        raise ValueError('Use a fresh output folder; completed shards are immutable')
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    tokenizer.no_truncation()
    tokenizer.no_padding()

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    original_file = data / 'kernel_output/variants.jsonl'
    originals = {r['uid']: r['original_tokens'] for r in read_jsonl(original_file) if r['method'] == 'original'}
    paths = [inputs, data / 'manifest.json', tokenizer_file, Path(__file__),
             Path(__file__).with_name('compressor_pilot.py'), Path(__file__).with_name('common.py')]
    paths += [BACKEND / 'src/gateway/modules/m2_compressor' / (name + '.py')
              for name in ('hinglish_evidence', 'budgeted', 'safety_span')]
    if original_file.exists():
        paths.append(original_file)
    inputs_to_check = [row for row in read_jsonl(inputs) if not item_ids or row['item_id'] in item_ids]
    if item_ids and set(item_ids) != {row['item_id'] for row in inputs_to_check}:
        raise ValueError('Requested smoke-test item is absent from pilot inputs')
    metadata = dict(sources_sha256={str(path.resolve()): digest(path) for path in paths},
                    tokenizer_file=str(tokenizer_file.resolve()), methods=list(EVIDENCE_METHODS), rates=RATES,
                    item_ids=sorted(item_ids), input_units=len(inputs_to_check), shard=shard, answer_quality='pending')
    rows = []
    for row in inputs_to_check:
        if not in_shard(row['item_id'], shard):
            continue
        original_n = count(row['context'])
        for method, settings in EVIDENCE_METHODS.items():
            for rate in RATES:
                start = time.perf_counter()
                result = compress_evidence(row['context'], row['question'], rate, count, **settings)
                detail = asdict(result)
                spans_ok = result.text == '\n'.join(row['context'][a:b] for a, b in result.source_spans)
                if result.selection_reason == 'original_fits':
                    spans_ok = result.text == row['context']
                if not result.budget_met or not spans_ok:
                    raise AssertionError(f'Budget/source invariant failed for {row["uid"]}')
                rows.append(dict(uid=row['uid'], item_id=row['item_id'], lang=row['lang'], method=method,
                                 rate=rate, original_tokens=original_n, source_exact=spans_ok,
                                 saved_original_count_matches=(original_n == originals[row['uid']]
                                                               if row['uid'] in originals else None),
                                 seconds=time.perf_counter() - start, **detail))
    write_rows(target, rows)
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(dict(shard=shard, records=len(rows))), flush=True)


def merge(out, shards):
    records, shared = [], None
    for i in range(1, shards + 1):
        metadata = json.loads((out / f'metadata_{i}_{shards}.json').read_text(encoding='utf-8'))
        if metadata.pop('shard') != f'{i}/{shards}':
            raise ValueError('Shard identity mismatch')
        if shared is not None and metadata != shared:
            raise ValueError('Shard source/configuration mismatch')
        shared = metadata
        records.extend(read_jsonl(out / f'evidence_{i}_{shards}.jsonl'))
    expected = shared['input_units'] * len(shared['methods']) * len(shared['rates'])
    keys = {(r['uid'], r['method'], r['rate']) for r in records}
    if len(records) != expected or len(keys) != expected:
        raise ValueError('Incomplete or duplicate coverage')
    # Check the actual Cartesian product, not just a matching total count.
    input_path = next(Path(p) for p in shared['sources_sha256'] if Path(p).name == 'inputs.jsonl')
    if digest(input_path) != shared['sources_sha256'][str(input_path)]:
        raise ValueError('Inputs changed after shard execution')
    expected_keys = {(r['uid'], m, rate) for r in read_jsonl(input_path)
                     if not shared['item_ids'] or r['item_id'] in shared['item_ids']
                     for m in shared['methods'] for rate in shared['rates']}
    if keys != expected_keys:
        raise ValueError('Input/method/rate coverage mismatch')
    groups = defaultdict(list)
    for record in records:
        groups[f"{record['lang']}|{record['method']}@{record['rate']}"].append(record)
    report = dict(shared, records=len(records), complete=True, groups={},
                  interpretation='Development diagnostics only; no downstream answers generated. '
                  'Cached tokenizer count agreement does not establish tokenizer identity.')
    for group, rows in groups.items():
        report['groups'][group] = dict(
            n=len(rows), budget_misses=sum(not r['budget_met'] for r in rows),
            source_mismatches=sum(not r['source_exact'] for r in rows),
            empty_outputs=sum(not r['text'] for r in rows),
            infeasible_evidence=sum(not r['evidence_feasible'] for r in rows),
            dependencies_unresolved=sum(r.get('dependencies_unresolved', 0) for r in rows),
            refill_units=sum(r.get('refill_units', 0) for r in rows),
            mean_kept_ratio=sum(r['actual_tokens'] / max(1, r['original_tokens']) for r in rows) / len(rows),
            saved_original_count_mismatches=sum(r['saved_original_count_matches'] is False for r in rows),
            saved_original_count_unavailable=sum(r['saved_original_count_matches'] is None for r in rows),
        )
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(report=str(out / 'report.json'), records=len(records), answer_quality='pending')))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['audit', 'merge'])
    ap.add_argument('--data', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--tokenizer-file', type=Path)
    ap.add_argument('--shard', default='1/1')
    ap.add_argument('--item-ids', nargs='+', default=[], help='Bounded regression smoke test, not a full CPU job')
    ap.add_argument('--shards', type=int, default=14)
    args = ap.parse_args()
    if args.action == 'audit':
        if args.data is None or args.tokenizer_file is None:
            ap.error('audit requires --data and --tokenizer-file (local file, no download)')
        audit(args.data, args.out, args.tokenizer_file, args.shard, args.item_ids)
    elif args.shards < 1:
        ap.error('--shards must be positive')
    else:
        merge(args.out, args.shards)
