"""Stage the full existing Hinglish pool and authorized follow-on limits.

No inference. Selection stays pending until the current four-model run ends.
Historical exposure is retained; more evaluations do not create fresh data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(text):
    return hashlib.sha256(' '.join(text.split()).encode()).hexdigest()


def prepare(items, parent, out):
    if out.exists():
        raise ValueError('Use a new output directory; preserve frozen artifacts')
    source = [json.loads(line) for line in items.read_text(encoding='utf-8').splitlines() if line.strip()]
    pilot = [json.loads(line) for line in (parent / 'inputs.jsonl').read_text(encoding='utf-8').splitlines()]
    pilot_ids = {r['item_id'] for r in pilot}
    pilot_groups = {group(r['english']['passage']) for r in source if r['id'] in pilot_ids}
    rows = []
    seen = set()
    for row in source:
        h = row['hinglish']
        if (row['id'] in seen or row['gold'] not in 'ABCD' or len(row['gold']) != 1
                or len(h['options']) != 4 or not all(isinstance(x, str) and x.strip()
                    for x in [h['passage'], h['question'], *h['options']])):
            raise ValueError(f"Invalid or duplicate item: {row['id']}")
        seen.add(row['id'])
        passage = group(row['english']['passage'])
        rows.append(dict(uid=f"belebele|{row['id']}|hinglish", item_id=row['id'], dataset='belebele',
            task='mcq', lang='hinglish', context=h['passage'], question=h['question'], options=h['options'],
            gold=row['gold'], passage_group=passage, selection_item=row['id'] in pilot_ids,
            selection_source_overlap=passage in pilot_groups, historical_exposure=True))
    out.mkdir(parents=True)
    (out / 'inputs.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    plan = dict(status='waiting_for_parent_completion_and_selection', parent=str(parent),
        items=len(rows), source_passages=len({r['passage_group'] for r in rows}),
        items_outside_current_selection_sources=sum(not r['selection_source_overlap'] for r in rows),
        sources={str(items): sha(items), str(parent / 'manifest.json'): sha(parent / 'manifest.json'),
                 str(Path(__file__)): sha(Path(__file__))}, inputs_sha256=sha(out / 'inputs.jsonl'),
        historical_exposure='All current Belebele items previously exposed; no fresh confirmatory set.',
        selection='Pending: select on complete current pilot only; freeze before expanded answers.',
        main_budget=0.5, other_budgets=[0.75, 0.33, 0.25],
        models=['qwen3.5:4b', 'qwen3.6:35b', 'qwen3.8:27b', 'qwen3.5:9b'],
        controls=['original', 'bm25_strict', 'llml2L_strict', 'matched segmentation/packing control'],
        extra_controls='Retain strongest cheap candidate; validated query-aware baseline if capacity permits.',
        max_additional_gpu_hours=24, max_public_text_download_bytes=2_000_000_000,
        max_independent_gold_qa_items=5000, max_natural_hinglish_stress_contexts=10000,
        expansion='Find licensed public Hinglish data with source provenance. Use genuine available QA labels; '
                  'never label generated or paraphrased items independent. '
                  'Natural unlabeled text is stress diagnostics only.',
        compute='College GPU for installed local Qwen inference; free Kaggle GPU for compression and useful '
                'independent-family validation. Respect quotas and shared GPU lock. No paid APIs or account rotation.',
        budget_reporting='Matched serving-token caps where tokenizer identity is verified; '
                         'otherwise label fixed-text transfer.',
        analysis=['passage-clustered paired accuracy and intervals', 'current-selection-source overlap strata',
                  'actual context and prompt retention', 'compressor and generation latency with hardware provenance',
                  'negation, numbers, names and relational evidence diagnostics', 'empty output and failure coverage',
                  'source fidelity, long context and code-mix/spelling strata',
                  'three raw examples for suspicious gains'],
        execution='Commit runner and freeze source/data/model hashes before launch. Reuse exact prompts and verified '
                  'checkpoints. Resume interrupted shards only with matching configuration; do not retry known '
                  'failures repeatedly. Stop at 24 added GPU-hours; record partial coverage.',
        notifications='Keep hourly checks compact; detailed analysis at stage boundaries and completion only.')
    (out / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: plan[k] for k in ('status', 'items', 'source_passages',
                                         'items_outside_current_selection_sources')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.items, args.parent, args.out)
