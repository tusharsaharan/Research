"""Sharded, model-free historical regrade; preserves original raw answers.

All methods get both the old parser and the same narrowly revised parser.
No model downloads or inference. Latest record wins per item/model/method.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from common import BENCH, in_shard
from grade import extract_letter


def rows(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def revised_letter(text):
    strict = extract_letter(text)
    if strict is not None:
        return strict
    match = re.search(r'(?:^|\n)\s*([ABCD])\s*####\s*$', text)
    return match[1] if match else None


def regrade(shard, out):
    out.mkdir(parents=True, exist_ok=True)
    name = shard.replace('/', '_')
    gold = {r['id']: r['gold'] for r in rows(BENCH / 'belebele/items.jsonl') if in_shard(r['id'], shard)}
    answers = BENCH / 'kaggle/answers.jsonl'
    latest = {}
    for answer in rows(answers):
        iid = answer.get('item_id')
        if iid not in gold:
            continue
        old, new = extract_letter(answer['content']), revised_letter(answer['content'])
        for method in answer['methods']:
            latest[(iid, answer['model'], method)] = dict(
                item_id=iid, model=answer['model'], method=method, gold=gold[iid],
                old_letter=old, revised_letter=new, old_correct=old == gold[iid],
                revised_correct=new == gold[iid], answer_sha256=hashlib.sha256(answer['content'].encode()).hexdigest())
    target = out / f'regrade_{name}.jsonl'
    with target.open('w', encoding='utf-8') as stream:
        for key in sorted(latest):
            stream.write(json.dumps(latest[key]) + '\n')
    metadata = dict(shard=shard, records=len(latest), script_sha256=sha(Path(__file__)),
                    grader_sha256=sha(Path(__file__).with_name('grade.py')),
                    input_sha256=sha(answers), items_sha256=sha(BENCH / 'belebele/items.jsonl'))
    (out / f'meta_{name}.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata), flush=True)


def merge(out, shards):
    groups = defaultdict(list)
    seen = set()
    metas = []
    for i in range(1, shards + 1):
        meta = json.loads((out / f'meta_{i}_{shards}.json').read_text())
        if meta['shard'] != f'{i}/{shards}':
            raise ValueError('Wrong shard identity')
        metas.append(meta)
        data = list(rows(out / f'regrade_{i}_{shards}.jsonl'))
        if len(data) != meta['records']:
            raise ValueError('Incomplete shard')
        for row in data:
            key = (row['item_id'], row['model'], row['method'])
            if key in seen or not in_shard(row['item_id'], f'{i}/{shards}'):
                raise ValueError('Duplicate or misplaced answer')
            seen.add(key)
            groups[(row['model'], row['method'])].append(row)
    for field in ('script_sha256', 'grader_sha256', 'input_sha256', 'items_sha256'):
        if len({meta[field] for meta in metas}) != 1:
            raise ValueError(f'Mixed source/config: {field}')
    summary = []
    for (model, method), data in sorted(groups.items()):
        n = len(data)
        summary.append(dict(model=model, method=method, n=n,
                            old_accuracy=sum(r['old_correct'] for r in data) / n,
                            revised_accuracy=sum(r['revised_correct'] for r in data) / n,
                            old_invalid=sum(r['old_letter'] is None for r in data),
                            revised_invalid=sum(r['revised_letter'] is None for r in data)))
    result = dict(protocol='Retrospective uniform parser sensitivity, no new model answers or test claims.',
                  shards=shards, records=len(seen), provenance=metas, groups=summary)
    (out / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(shards=shards, records=len(seen), method_groups=len(summary))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cmd', choices=('regrade', 'merge'))
    parser.add_argument('--shard', default='1/1')
    parser.add_argument('--shards', type=int, default=14)
    parser.add_argument('--out', type=Path, default=BENCH / 'hinglish_cpu_v1')
    args = parser.parse_args()
    if args.cmd == 'regrade':
        regrade(args.shard, args.out)
    else:
        merge(args.out, args.shards)
