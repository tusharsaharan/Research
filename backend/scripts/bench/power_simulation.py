"""Passage-clustered planning simulation from archived paired dev answers.

Resample complete paired passage differences under a centered null or a fixed
accuracy-shift alternative. Uses a cluster-robust normal approximation; this is
planning sensitivity, not confirmatory inference or a promise of future power.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import norm

from compressor_artifacts import digest, records, save, verify_archive
from grade import extract_letter


def simulate(differences, sizes, clusters, replicates, effect, rng, alpha):
    differences, sizes = np.asarray(differences, float), np.asarray(sizes, float)
    centered = differences - differences.sum() / sizes.sum() * sizes
    rejected = 0
    critical = norm.ppf(1 - alpha / 2)
    for start in range(0, replicates, 200):
        batch = min(200, replicates-start)
        indices = rng.integers(0, len(sizes), size=(batch, clusters))
        n = sizes[indices]
        d = centered[indices] + effect * n
        estimate = d.sum(axis=1) / n.sum(axis=1)
        residual = d - estimate[:, None] * n
        se = np.sqrt(clusters / (clusters-1) * (residual**2).sum(axis=1)) / n.sum(axis=1)
        rejected += int(np.count_nonzero(np.abs(estimate) > critical * se))
    rate = rejected / replicates
    return dict(rejection_rate=rate, monte_carlo_se=float(np.sqrt(rate*(1-rate)/replicates)))


def plan(data: Path, output: Path, replicates=10000) -> dict:
    if output.exists():
        raise ValueError('Output exists; no automatic repeated planning runs')
    hashes = verify_archive(data, ['answers.jsonl', 'inputs.jsonl'])
    inputs = {r['uid']:r for r in records(data/'inputs.jsonl')}
    methods = ['bqwen35b_span@0.5','bm25_strict@0.5','llml2L_strict@0.5']
    answers = {}
    for row in records(data/'answers.jsonl'):
        if row['model'] == 'qwen3.5:4b' and row['method'] in methods:
            key = (row['uid'],row['method'])
            if key in answers:
                raise ValueError('Duplicate answer')
            answers[key] = int(extract_letter(row['content']) == inputs[row['uid']]['gold'])
    if len(answers) != len(inputs)*len(methods):
        raise ValueError('Incomplete paired planning cell')
    rng, comparisons = np.random.default_rng(20261116), {}
    for baseline in methods[1:]:
        grouped = defaultdict(lambda:[0,0])
        for uid, item in inputs.items():
            group = grouped[item['passage_group']]
            group[0] += answers[(uid,methods[0])] - answers[(uid,baseline)]
            group[1] += 1
        deltas,sizes = zip(*grouped.values(), strict=True)
        cells=[]
        for clusters in [100,200,400,800,1200,2000,3000]:
            cells.append(dict(independent_passages=clusters, expected_questions=clusters*float(np.mean(sizes)),
                null=simulate(deltas,sizes,clusters,replicates,0,rng,.025),
                alternative_3pp=simulate(deltas,sizes,clusters,replicates,.03,rng,.025)))
        eligible=[c['independent_passages'] for c in cells if c['alternative_3pp']['rejection_rate']>=.8]
        comparisons[baseline]=dict(development_passages=len(sizes),development_questions=sum(sizes),
            observed_development_delta=sum(deltas)/sum(sizes),
            minimum_tested_passages_for_80pct_power=min(eligible) if eligible else None, cells=cells)
    report=dict(status='complete',seed=20261116,replicates=replicates,primary_model='qwen3.5:4b',rate=.5,
        target_effect=.03,family_alpha=.05,per_comparison_alpha=.025,comparisons=comparisons,sources=hashes,
        script_sha256=digest(Path(__file__)), assumptions=[
            'Empirical independent source passages, retaining their unequal question counts and paired differences.',
            'Centered passage-level differences shifted by 0.03; synthetic planning distribution can lie outside discrete binary support.',
            'Normal cluster-robust test approximation; null rejection reported to expose poor calibration.',
            'No fresh-data sample-size guarantee; estimate uncertainty and source-distribution shift remain limitations.',
            'This plan covers the frozen primary model; independent-family planning must be updated before its sealed run.'])
    save(output,report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=plan(args.data,args.output)
    print(json.dumps({k:v['minimum_tested_passages_for_80pct_power'] for k,v in report['comparisons'].items()}))
