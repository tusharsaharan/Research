"""Replay frozen stress rankings with atomic packing; no model calls."""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

from tokenizers import Tokenizer

from compressor_artifacts import digest, records, save, verify_archive
from gateway.modules.m2_compressor.qwen_evidence import lexical_order, pack_ranked, source_units

GUARD = re.compile(r'\b(?:nahi|nahin|nhi|not|never|no|\d+)\b')


def replay(data: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('Output exists; inspect it instead of repeating the diagnostic')
    sources = verify_archive(data, ['stress_inputs.jsonl', 'stress_rankings.jsonl', 'tokenizer.json', 'stress_variants.jsonl'])
    tokenizer = Tokenizer.from_file(str(data / 'tokenizer.json'))
    count = lambda text: len(tokenizer.encode(text, add_special_tokens=False).ids)
    inputs = {r['uid']: r for r in records(data / 'stress_inputs.jsonl')}
    rankings = {r['uid']: r for r in records(data / 'stress_rankings.jsonl')}
    if len(inputs) != 10000 or set(inputs) != set(rankings):
        raise ValueError('Frozen stress coverage mismatch')
    historical = defaultdict(Counter)
    for row in records(data / 'stress_variants.jsonl'):
        key = f"{row['stratum']}|{row['method']}@{row['rate']}"
        historical[key].update(items=1, empty=int(not row['text']),
            punctuation_only=int(bool(row['text']) and not re.search(r'[^\W_]', row['text'])),
            lost_guard_occurrences=row['lost_guard_occurrences'],
            output_tokens=row['actual_tokens'], budget_misses=int(not row['budget_met']))
    output.mkdir(parents=True)
    totals, examples = defaultdict(Counter), []
    started = time.perf_counter()
    with (output / 'variants.jsonl').open('x', encoding='utf-8') as stream:
        for uid, row in inputs.items():
            if time.perf_counter() - started > 1800:
                raise TimeoutError('Frozen 30-minute CPU replay cap')
            units = source_units(row['context'])
            orders = {'bqwen35b_span_atomic': rankings[uid]['order'],
                      'bspan_bm25_atomic': lexical_order(units, 'Is text ka main point kya hai?')}
            before = Counter(GUARD.findall(row['context'].lower()))
            for method, order in orders.items():
                for rate in (.25, .33, .5, .75):
                    packed = pack_ranked(row['context'], units, order, rate, count, fallback_policy='empty')
                    text = packed['text']
                    after = Counter(GUARD.findall(text.lower()))
                    lost = sum((before - after).values())
                    punctuation = bool(text) and not re.search(r'[^\W_]', text)
                    if punctuation or not packed['budget_met']:
                        raise ValueError('Atomic packing invariant failed: ' + uid)
                    key = f"{row['stratum']}|{method}@{rate}"
                    totals[key].update(items=1, empty=int(not text), punctuation_only=int(punctuation),
                        lost_guard_occurrences=lost, guard_occurrences=sum(before.values()),
                        output_tokens=packed['actual_tokens'], budget_misses=int(not packed['budget_met']))
                    stream.write(json.dumps(dict(uid=uid, stratum=row['stratum'], method=method, rate=rate,
                                                 lost_guard_occurrences=lost, **packed), ensure_ascii=False) + '\n')
                    if method == 'bqwen35b_span_atomic' and rate == .33 and len(examples) < 3 and before:
                        examples.append(dict(uid=uid, original=row['context'], output=text, lost_literals=dict(before-after)))
    report = dict(status='complete', inputs=len(inputs), records=sum(x['items'] for x in totals.values()),
        historical=dict(historical), atomic=dict(totals), examples=examples,
        seconds=time.perf_counter()-started, sources=sources,
        script_sha256=digest(Path(__file__)), output_sha256=digest(output/'variants.jsonl'),
        note='Surface diagnostics only. Empty evidence remains a failure. Complete spans do not guarantee semantic preservation.')
    save(output/'report.json', report)
    return {key:report[key] for key in ('status','inputs','records','seconds','note')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.data, args.output), indent=2))
