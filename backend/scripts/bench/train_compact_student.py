"""Fit one fixed compact student and report held-out teacher-imitation metrics.

No answers are generated. Rank correlation is not QA accuracy. CPU-only fit,
no hyperparameter search, no loading of pickle checkpoints.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import random
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

from compressor_artifacts import digest, records, save
from gateway.modules.m2_compressor.qwen_evidence import lexical_order
from gateway.modules.m2_compressor.student_ranker import FEATURES, rank_spans, span_features


def metrics(rows: list[dict], order_fn) -> dict:
    top, ndcg, correlations, timed = [], [], [], []
    for row in rows:
        started = time.perf_counter()
        order = order_fn(row)
        timed.append(time.perf_counter() - started)
        teacher = row['teacher_order']
        if sorted(order) != list(range(len(teacher))):
            raise ValueError('Invalid student permutation')
        top.append(order[0] == teacher[0])
        positions = {span: rank for rank, span in enumerate(teacher)}
        # Linear ordinal relevance; do not interpret it as answer importance.
        gains = np.arange(len(teacher), 0, -1, dtype=float)
        k = min(3, len(teacher))
        discount = np.log2(np.arange(k) + 2)
        ndcg.append(float(sum(gains[positions[i]] / discount[j] for j, i in enumerate(order[:k]))
                          / sum(gains[:k] / discount)))
        if len(teacher) > 1:
            predicted_positions = {span: rank for rank, span in enumerate(order)}
            correlations.append(float(spearmanr([predicted_positions[i] for i in range(len(order))],
                                               [positions[i] for i in range(len(order))]).statistic))
    return dict(items=len(rows), top1_teacher_agreement=float(np.mean(top)),
                ndcg_at_3=float(np.mean(ndcg)), mean_spearman=float(np.mean(correlations)) if correlations else None,
                correlation_items=len(correlations),
                scoring_seconds_mean=float(np.mean(timed)), scoring_seconds_p95=float(np.quantile(timed, .95)))


def train(data: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('Output exists; do not overwrite a finished run')
    started = time.perf_counter()
    manifest = json.loads((data / 'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        if digest(data / name) != expected:
            raise ValueError('Training artifact changed: ' + name)
    train_rows = list(records(data / 'compressor_distill_train.jsonl'))
    dev_rows = list(records(data / 'compressor_distill_development.jsonl'))
    if not train_rows or not dev_rows:
        raise ValueError('Nonempty train and development sets required')
    if {r['passage_group'] for r in train_rows} & {r['passage_group'] for r in dev_rows}:
        raise ValueError('Source passage leakage')
    rng = random.Random(20261116)
    pairs = []
    for row in train_rows:
        features = np.asarray(span_features(row['spans'], row['question']))
        order = row['teacher_order']
        for i, winner in enumerate(order):
            for loser in order[i + 1:]:
                delta = features[winner] - features[loser]
                pairs.extend([(delta, 1), (-delta, 0)])
    rng.shuffle(pairs)
    pairs = pairs[:50000]
    if not pairs:
        raise ValueError('No pairwise training comparisons')
    model = LogisticRegression(C=1, fit_intercept=False, max_iter=1000, random_state=20261116)
    model.fit(np.asarray([x for x, _ in pairs]), np.asarray([y for _, y in pairs]))
    if any(model.n_iter_ >= 1000):
        raise ValueError('Optimizer did not converge within frozen iteration cap')
    checkpoint = dict(schema='compact_lexical_student_v1', features=list(FEATURES),
                      weights=model.coef_[0].tolist(), seed=20261116, C=1,
                      training_manifest_sha256=digest(data / 'manifest.json'),
                      label='exposed-development ordinal teacher imitation; downstream quality unmeasured')
    result = dict(status='complete', scope=checkpoint['label'], directed_training_pairs=len(pairs),
                  train_items=len(train_rows), development_items=len(dev_rows),
                  student=metrics(dev_rows, lambda r: rank_spans(r['spans'], r['question'], checkpoint)),
                  bm25=metrics(dev_rows, lambda r: lexical_order(r['spans'], r['question'])),
                  fit_and_evaluation_seconds=time.perf_counter() - started,
                  sources={'training_manifest': digest(data / 'manifest.json'), 'script': digest(Path(__file__))},
                  parameter_count=len(FEATURES), selection='Single fixed candidate; no development hyperparameter search.')
    result['versions'] = {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'scikit-learn']}
    save(output / 'student.json', checkpoint)
    result['checkpoint_sha256'] = digest(output / 'student.json')
    save(output / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(train(args.data, args.output), indent=2))
