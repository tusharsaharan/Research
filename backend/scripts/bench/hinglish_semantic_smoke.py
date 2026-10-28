"""Bounded, cached-model engineering check on three exposed Hinglish examples.

No downloads, answer generation or accuracy estimates. The supplied tokenizer
is a local diagnostic; the GPU evaluator uses the answer model's own tokenizer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

from common import BACKEND, read_jsonl

sys.path.insert(0, str(BACKEND / 'src'))


def smoke(inputs, tokenizer_path, out):
    import torch
    from tokenizers import Tokenizer
    from gateway.modules.m2_compressor.hinglish_budget import compress_ablation, split_clauses, strict_prefix
    from gateway.modules.m2_compressor.semantic_ranker import (
        ENCODER_MODEL, ENCODER_REVISION, MultilingualWindowEncoder, SemanticRanker, window_max_scores,
    )

    if out.exists():
        raise ValueError('Use a new smoke report path')
    torch.set_num_threads(14)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    # The relevant source tail and second question window both affect ranking.
    embeddings = torch.tensor([[1., 0.], [0., 1.], [-1., 0.], [0., 1.], [-1., 0.]])
    assert window_max_scores(embeddings, torch.tensor([0, 0, 1, 1, 2]), 2) == [1., 0.]
    started = time.monotonic()
    encoder = MultilingualWindowEncoder(local_files_only=True)
    rankers = {'bhybrid_char_clause': None, 'bhinglish_semantic': SemanticRanker(encoder),
               'bhinglish_semantic_fused': SemanticRanker(encoder, fused=True)}
    long_text = 'Yeh ek lamba parikshan hai. ' * 80 + 'Gaadi radar ke liye bahut chhoti thi.'
    windows = encoder.tokenizer(long_text, truncation=True, max_length=128, stride=32,
                                return_overflowing_tokens=True)
    assert len(windows['input_ids']) > 1
    assert all(math.isfinite(v) for v in encoder.scores([long_text], 'Gaadi kyun nahi dikhi?'))
    ids = {'bb-418', 'bb-79', 'bb-285'}
    rows = [r for r in read_jsonl(inputs) if r['lang'] == 'hinglish' and r['item_id'] in ids]
    assert len(rows) == len(ids)
    examples = []
    for row in rows:
        units = split_clauses(row['context'])
        example = dict(uid=row['uid'], question=row['question'], context=row['context'],
                       units=units, semantic_scores=encoder.scores(units, row['question']), variants=[])
        for method, ranker in rankers.items():
            for rate in (0.5, 0.33):
                result = compress_ablation(row['context'], row['question'], rate, count, None,
                                          characters=True, clauses=True, ranker=ranker)
                target = max(1, math.floor(count(row['context']) * rate))
                text = strict_prefix(result.text, target, count)
                words = iter(row['context'].split())
                fidelity = all(any(word == source for source in words) for word in text.split())
                assert fidelity and count(text) <= target
                example['variants'].append(dict(method=method, rate=rate, text=text,
                    original_tokens=count(row['context']), target_tokens=target, actual_tokens=count(text),
                    before_cap_tokens=count(result.text), clipped=text != result.text, source_subsequence=fidelity))
        examples.append(example)
    sources = [Path(__file__), BACKEND / 'src/gateway/modules/m2_compressor/semantic_ranker.py',
               BACKEND / 'src/gateway/modules/m2_compressor/hinglish_budget.py',
               BACKEND / 'src/gateway/modules/m2_compressor/budgeted.py', inputs, tokenizer_path]
    report = dict(status='passed', accuracy='pending GPU answers; this checks engineering only',
        language='hinglish', git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        encoder=ENCODER_MODEL, revision=ENCODER_REVISION, device='cpu', torch_version=torch.__version__,
        elapsed_seconds=time.monotonic() - started, tokenizer=str(tokenizer_path),
        sources_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        multiwindow_check=True, examples=examples)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(dict(status=report['status'], examples=len(examples), report=str(out))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    smoke(args.inputs, args.tokenizer, args.out)
