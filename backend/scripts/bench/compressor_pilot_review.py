"""Paired, passage-clustered review of a completed compressor pilot.

Intervals are exploratory: inspected development runs are not confirmatory.
Includes actual prompt retention, strict-budget references and raw examples.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from compressor_pilot import grade
from grade import extract_letter
from hinglish_research_audit import digest, paired_interval, passage_key, read_rows
from hotpot import clean, f1


def review(data):
    out = data / 'kernel_output'
    validated = grade(data, out)
    if not validated['complete']:
        raise ValueError('Full paired review requires a complete run')
    rows = list(read_rows(data / 'inputs.jsonl'))
    answers = {r['key']: r for r in read_rows(out / 'answers.jsonl')}
    variants = {r['key']: r for r in read_rows(out / 'variants.jsonl')}
    groups = defaultdict(list)
    for row in rows:
        groups[row['dataset'] + '|' + row['lang']].append(row)
    result = dict(config=validated['config'], complete=True, groups={}, comparisons=[], examples=[],
                  inference='Exploratory paired passage-cluster bootstrap; adaptive selection and multiple comparisons are not corrected.')

    def key(row, method):
        return row['uid'] + '|' + method

    def score(row, method):
        reply = answers[key(row, method)]['content']
        return float(extract_letter(reply) == row['gold']) if row['task'] == 'mcq' else f1(clean(reply), row['gold'])

    for group, inputs in groups.items():
        methods = validated['groups'][group]['methods']
        result['groups'][group] = {}
        for method, stats in methods.items():
            selected = [variants[key(row, method)] for row in inputs]
            result['groups'][group][method] = dict(stats,
                mean_full_prompt_ratio=sum(answers[key(r, method)]['prompt_tokens'] / answers[key(r, 'original')]['prompt_tokens'] for r in inputs) / len(inputs),
                clipped=sum(v.get('detail', {}).get('budget_enforced', False) for v in selected),
                empty_outputs=sum(not v['text'].strip() for v in selected),
                infeasible_evidence=sum(v.get('detail', {}).get('evidence_feasible') is False for v in selected),
                invalid_answers=sum(extract_letter(answers[key(r, method)]['content']) is None for r in inputs) if inputs[0]['task'] == 'mcq' else None)
            if not method.startswith(('bhybrid_strict@', 'bhybrid_char@', 'bhybrid_clause@', 'bhybrid_char_clause@',
                                      'bhinglish_units@', 'bhinglish_coverage@')):
                continue
            rate = method.rsplit('@', 1)[1]
            references = [f'bm25_strict@{rate}', f'llml2L_strict@{rate}', 'original']
            if method.startswith('bhinglish_coverage@'):
                references.append(f'bhinglish_units@{rate}')
            for reference in references:
                if reference not in methods:
                    continue
                deltas = [score(r, method) - score(r, reference) for r in inputs]
                result['comparisons'].append(dict(group=group, method=method, reference=reference,
                    **paired_interval(deltas, [r.get('passage_group', passage_key(r['context'])) for r in inputs])))
                if reference.startswith('bm25_strict') and method in ('bhybrid_strict@0.33', 'bhybrid_char_clause@0.5'):
                    for direction in (-1, 1):
                        examples = [r for r, d in zip(inputs, deltas, strict=True) if d * direction > 0][:3]
                        for r in examples:
                            result['examples'].append(dict(group=group, item_id=r['item_id'], method=method,
                                reference=reference, direction=direction, question=r['question'], gold=r['gold'],
                                options=r.get('options'), original=r['context'],
                                variants={m: variants[key(r, m)] for m in (method, reference)},
                                answers={m: answers[key(r, m)]['content'] for m in (method, reference, 'original')}))
    paths = [data / 'inputs.jsonl', data / 'manifest.json', out / 'answers.jsonl', out / 'variants.jsonl',
             Path(__file__), Path(__file__).with_name('hinglish_research_audit.py'),
             Path(__file__).with_name('compressor_pilot.py'), Path(__file__).with_name('grade.py'),
             Path(__file__).with_name('hotpot.py')]
    result['sources_sha256'] = {str(p): digest(p) for p in paths}
    (out / 'review.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(review=str(out / 'review.json'), comparisons=len(result['comparisons']),
                          examples=len(result['examples']))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    review(parser.parse_args().data)
