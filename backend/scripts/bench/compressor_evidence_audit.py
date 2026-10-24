"""CPU retrieval diagnostic: answer-string retention is not answer quality.

No model weights, provider calls or reference answers enter the compressors.
CL100K budgets are diagnostic; the GPU pilot separately uses Qwen token counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import BENCH, read_jsonl
from gateway.modules.m2_compressor.document import bridge_document, extract_document
from gateway.tokenizer import TokenCounter
from hotpot import norm


class Identity:
    def compress_masked(self, texts, *args, **kwargs):
        return texts


def contains_answer(context, answer):
    normalized = norm(answer)
    return bool(normalized) and f" {normalized} " in f" {norm(context)} "


def audit(data: Path, out: Path, workers: int):
    inputs = data / "inputs.jsonl"
    rows = [r for r in read_jsonl(inputs) if r['task'] == 'qa']
    counter = TokenCounter()
    identity = Identity()

    def run(row):
        records = []
        original_has_gold = contains_answer(row['context'], row['gold'])
        for method, compressor in (("bextract_doc", extract_document), ("bbridge_doc", bridge_document)):
            for rate in (0.5, 0.33):
                result = compressor(row['context'], row['question'], rate, counter.count, identity)
                records.append(dict(uid=row['uid'], dataset=row['dataset'], method=method, rate=rate,
                                    original_has_gold=original_has_gold,
                                    compressed_has_gold=contains_answer(result.text, row['gold']),
                                    actual_tokens=result.actual_tokens, target_tokens=result.target_tokens,
                                    budget_met=result.budget_met))
        return records

    out.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(lambda: dict(n=0, original_has_gold=0, retained=0, budget_misses=0))
    with ThreadPoolExecutor(max_workers=workers) as pool, (out / "rows.jsonl").open('w', encoding='utf-8') as fh:
        for batch in pool.map(run, rows):
            for record in batch:
                fh.write(json.dumps(record) + '\n')
                group = groups[f"{record['dataset']}|{record['method']}@{record['rate']}"]
                group['n'] += 1
                group['original_has_gold'] += record['original_has_gold']
                group['retained'] += record['original_has_gold'] and record['compressed_has_gold']
                group['budget_misses'] += not record['budget_met']
    from gateway.modules.m2_compressor import document
    report = dict(inputs_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest(),
                  analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  compressor_sha256=hashlib.sha256(Path(document.__file__).read_bytes()).hexdigest(),
                  workers=workers, tokenizer=counter.backend, groups=groups,
                  note="Answer-string retention only; identity thinning, no answer generation or quality claim.")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=BENCH / 'compressor_evidence_audit')
    parser.add_argument('--workers', type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('workers must be positive')
    audit(args.data, args.out, args.workers)
