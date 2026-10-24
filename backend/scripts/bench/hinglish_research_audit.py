"""Read-only evidence audit for the Hinglish compressor paper; no model calls.

Writes a reproducible snapshot under data/bench. Bootstrap intervals are
passage-clustered, paired and exploratory; reused development data cannot
support confirmatory claims. Historical protocols are kept separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from common import BENCH
from grade import extract_letter


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def passage_key(text):
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


def historical_letter_sensitivity(content):
    """Audit one observed legacy formatting failure without changing the grader."""
    strict = extract_letter(content)
    if strict is not None:
        return strict
    reversed_marker = re.search(r"(?:^|\n)\s*([ABCD])\s*####\s*$", content)
    return reversed_marker.group(1) if reversed_marker else None


def paired_interval(deltas, clusters, replicates=10000):
    if len(deltas) != len(clusters):
        raise ValueError("Every paired delta needs its passage cluster")
    if not deltas:
        return dict(n=0, n_passages=0, delta=None, ci95=None)
    grouped = defaultdict(list)
    for delta, cluster in zip(deltas, clusters, strict=True):
        grouped[cluster].append(delta)
    sums = np.array([sum(values) for values in grouped.values()])
    sizes = np.array([len(values) for values in grouped.values()])
    rng = np.random.default_rng(20261024)
    weights = rng.multinomial(len(sizes), np.full(len(sizes), 1 / len(sizes)), size=replicates)
    estimates = (weights @ sums) / (weights @ sizes)
    return dict(n=len(deltas), n_passages=len(sizes), delta=float(np.mean(deltas)),
                ci95=np.quantile(estimates, [0.025, 0.975]).tolist())


def audit(out):
    out.mkdir(parents=True, exist_ok=True)
    sources = {}

    def track(path):
        sources[str(path.relative_to(BENCH))] = digest(path)
        return path

    items = {r['id']: r for r in read_rows(track(BENCH / 'belebele/items.jsonl'))}
    groups = defaultdict(list)
    for item in items.values():
        groups[passage_key(item['english']['passage'])].append(item['id'])
    cluster = {iid: key for key, ids in groups.items() for iid in ids}
    split = lambda iid: 'dev' if int(hashlib.sha256(f'hybrid-dev|{iid}'.encode()).hexdigest(), 16) % 3 == 0 else 'test'
    crossed = {key for key, ids in groups.items() if len({split(i) for i in ids}) > 1}
    report = dict(analysis_sha256=digest(Path(__file__)),
                  grader_sha256=digest(Path(__file__).with_name('grade.py')), bootstrap_replicates=10000,
                  inference='Exploratory passage-clustered paired percentile intervals, not confirmatory tests.',
                  dataset=dict(items=len(items), unique_english_passages=len(groups),
                               passages_crossing_old_dev_test=len(crossed),
                               test_items_sharing_dev_passage=sum(split(i) == 'test' for key in crossed for i in groups[key]),
                               item_fields=sorted(next(iter(items.values())).keys())),
                  pilots={}, comparisons=[], failures=[], exposure={}, historical={})
    pilot_inputs = {}
    for revision in (4, 5, 6, 7, 8):
        folder = BENCH / f'compressor_pilot_v{revision}'
        manifest = json.loads(track(folder / 'manifest.json').read_text())
        rows = list(read_rows(track(folder / 'inputs.jsonl')))
        pilot_inputs[revision] = {r['item_id'] for r in rows if r['dataset'] == 'belebele'}
        output = folder / 'kernel_output'
        entry = dict(manifest=manifest, groups={}, completed=(output / 'report.json').exists())
        report['pilots'][str(revision)] = entry
        if not entry['completed']:
            continue
        saved = json.loads(track(output / 'report.json').read_text())
        entry.update(complete=saved['complete'], answered=saved['answered'],
                     groups=saved['groups'], identical_prompt_diagnostics=saved.get('identical_prompt_diagnostics'))
        if revision not in (5, 7):
            continue
        answers = {r['key']: r for r in read_rows(track(output / 'answers.jsonl'))}
        variants = {r['key']: r for r in read_rows(track(output / 'variants.jsonl'))}
        for lang in ('hinglish', 'english'):
            subset = [r for r in rows if r['dataset'] == 'belebele' and r['lang'] == lang]
            for method in saved['groups'][f'belebele|{lang}']['methods']:
                key = lambda row, m=method: row['uid'] + '|' + m
                paired = [r for r in subset if key(r) in answers and key(r, 'original') in answers]
                details = entry['groups'][f'belebele|{lang}']['methods'][method]
                details['invalid_answers'] = sum(extract_letter(answers[key(r)]['content']) is None for r in paired)
                details['mean_full_prompt_ratio'] = float(np.mean([
                    answers[key(r)]['prompt_tokens'] / answers[key(r, 'original')]['prompt_tokens'] for r in paired]))
                details['broke_original_correct'] = sum(extract_letter(answers[key(r, 'original')]['content']) == r['gold']
                                                       and extract_letter(answers[key(r)]['content']) != r['gold'] for r in paired)
                details['fixed_original_wrong'] = sum(extract_letter(answers[key(r, 'original')]['content']) != r['gold']
                                                     and extract_letter(answers[key(r)]['content']) == r['gold'] for r in paired)
                if not method.startswith(('bhybrid_v2@', 'bhybrid_doc@', 'bextract_doc@')):
                    continue
                reference = 'bm25@' + method.split('@')[1]
                compare = [r for r in paired if key(r, reference) in answers]
                conditions = {
                    'all_paired': lambda r: True,
                    'both_within_budget': lambda r: variants[key(r)]['budget_met'] and variants[key(r, reference)]['budget_met'],
                    'candidate_within_budget_and_no_more_tokens': lambda r: variants[key(r)]['budget_met']
                    and variants[key(r)]['actual_tokens'] <= variants[key(r, reference)]['actual_tokens'],
                }
                for condition, eligible in conditions.items():
                    fair = [r for r in compare if eligible(r)]
                    deltas = [int(extract_letter(answers[key(r)]['content']) == r['gold'])
                              - int(extract_letter(answers[key(r, reference)]['content']) == r['gold']) for r in fair]
                    report['comparisons'].append(dict(revision=revision, language=lang, method=method,
                                                      reference=reference, subset=condition,
                                                      **paired_interval(deltas, [cluster[r['item_id']] for r in fair])))
                if revision == 7 and lang == 'hinglish' and method == 'bextract_doc@0.33':
                    for r in compare:
                        if (extract_letter(answers[key(r, 'original')]['content']) == r['gold']
                                and extract_letter(answers[key(r)]['content']) != r['gold']
                                and extract_letter(answers[key(r, reference)]['content']) == r['gold']):
                            report['failures'].append(dict(item_id=r['item_id'], question=r['question'], options=r['options'],
                                                           gold=r['gold'], original=r['context'],
                                                           candidate=variants[key(r)], reference=variants[key(r, reference)],
                                                           answers={m: answers[key(r, m)]['content'] for m in ('original', method, reference)}))
    for left, right in ((5, 7), (7, 8)):
        seen = {cluster[i] for i in pilot_inputs[left]}
        report['exposure'][f'v{left}_to_v{right}'] = dict(
            item_overlap=len(pilot_inputs[left] & pilot_inputs[right]),
            later_items_sharing_earlier_passage=sum(cluster[i] in seen for i in pilot_inputs[right]),
            later_items=len(pilot_inputs[right]))
    historical_answers = track(BENCH / 'kaggle/answers.jsonl')
    historical = {}
    for a in read_rows(historical_answers):
        if a.get('item_id') in items and a.get('model') == 'Qwen/Qwen2.5-3B-Instruct':
            for method in a['methods']:
                if method in ('original', 'english'):
                    historical[(a['item_id'], method)] = a
    for method in ('original', 'english'):
        rows = [a for (iid, m), a in historical.items() if m == method]
        recovered = [a for a in rows if extract_letter(a['content']) is None
                     and historical_letter_sensitivity(a['content']) is not None]
        report['historical'][method] = dict(n=len(rows),
            invalid_answers=sum(extract_letter(a['content']) is None for a in rows),
            accuracy=sum(extract_letter(a['content']) == items[a['item_id']]['gold'] for a in rows) / len(rows),
            reversed_marker_recoverable=len(recovered),
            reversed_marker_correct=sum(historical_letter_sensitivity(a['content']) == items[a['item_id']]['gold'] for a in recovered),
            sensitivity_accuracy=sum(historical_letter_sensitivity(a['content']) == items[a['item_id']]['gold'] for a in rows) / len(rows),
            sensitivity_note='Original-only parser sensitivity, not a uniform regrade of methods; do not use for method ranking.',
            invalid_examples=[dict(item_id=a['item_id'], gold=items[a['item_id']]['gold'], content=a['content'])
                              for a in rows if extract_letter(a['content']) is None][:3])
    exposure_rows = [dict(item_id=iid, passage_sha256=cluster[iid], old_split=split(iid),
                          historical_original_answer_seen=(iid, 'original') in historical,
                          completed_pilots=[v for v in (4, 5, 6, 7) if iid in pilot_inputs[v]],
                          prepared_v8=iid in pilot_inputs[8]) for iid in sorted(items)]
    (out / 'exposure.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in exposure_rows), encoding='utf-8')
    for name in ('hybrid_select.json', 'extra_report.json', 'extra_report_7b.json'):
        report['historical'][name] = json.loads(track(BENCH / 'belebele' / name).read_text())
    report['sources_sha256'] = sources
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(dataset=report['dataset'], exposure=report['exposure'],
                          failures=len(report['failures']), output=str(out / 'report.json'))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=BENCH / 'hinglish_research_audit')
    audit(parser.parse_args().out)
