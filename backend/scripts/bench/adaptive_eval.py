"""Adaptive per-prompt compression (offline, no API).

For each prompt, choose the most aggressive guarded2 keep-rate whose compressed
text keeps multilingual-embedding similarity to the original >= a floor tau.
Guards (negations, question words, digit words, MCQ options) are already in
every candidate, so the floor only has to protect the rest of the meaning.

Compares, per language: fixed guarded2@r for r in {0.4..0.8} vs adaptive(tau)
on mean o200k kept ratio, mean similarity, share of prompts below 0.80, and
negation / question-word / number loss.

    python backend/scripts/bench/adaptive_eval.py
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

import numpy as np
import torch
from common import BENCH
from compress_eval import build_prompts

from gateway.modules.m4_router.certified import _encoder

RATES = ["guarded2@0.4", "guarded2@0.5", "guarded2@0.6", "guarded2@0.7", "guarded2@0.8"]  # most -> least aggressive
TAUS = [0.80, 0.85, 0.90, 0.93]
CACHE = BENCH / "adaptive_emb_cache.npz"


def main() -> None:
    torch.set_num_threads(os.cpu_count() or 4)
    prompts = {p["pid"]: p for p in build_prompts(8000, 20261016)}
    rows: dict = defaultdict(dict)  # pid -> method -> row
    for f in glob.glob(str(BENCH / "compress_rows.guarded2.shard*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["method"] in RATES and r["pid"] in prompts:
                rows[r["pid"]][r["method"]] = r
    pids = [p for p in rows if len(rows[p]) == len(RATES)]
    print(f"{len(pids)} prompts with all {len(RATES)} guarded rates")

    texts = {}
    for p in pids:
        texts[prompts[p]["text"]] = None
        for m in RATES:
            r = rows[p][m]
            texts[r["compressed"] if r["changed"] and r.get("compressed") else prompts[p]["text"]] = None
    keys = list(texts)
    emb = {}
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        emb = dict(zip(z["keys"].tolist(), z["vecs"]))
    todo = [k for k in keys if k not in emb]
    print(f"embedding {len(todo)} new texts ({len(keys) - len(todo)} cached)", flush=True)
    if todo:
        vecs = _encoder().encode(todo, batch_size=128, normalize_embeddings=True, show_progress_bar=False)
        emb.update(zip(todo, vecs))
        np.savez(CACHE, keys=np.array(list(emb), dtype=object), vecs=np.stack(list(emb.values())))

    def cand(p, m):
        r = rows[p][m]
        t = r["compressed"] if r["changed"] and r.get("compressed") else prompts[p]["text"]
        sim = float(emb[prompts[p]["text"]] @ emb[t])
        return r, sim

    def score(chosen):  # chosen: pid -> (row, sim)
        out = {}
        for lang in ("english", "hinglish"):
            ps = [p for p in chosen if prompts[p]["lang"] == lang]
            if not ps:
                continue
            kept = sum(chosen[p][0]["tokens_after"]["o200k"] for p in ps) / sum(chosen[p][0]["tokens_before"]["o200k"] for p in ps)
            sims = np.array([chosen[p][1] for p in ps])
            neg = [chosen[p][0] for p in ps if chosen[p][0]["neg_in"]]
            qw = [chosen[p][0] for p in ps if chosen[p][0]["qw_in"]]
            num = [chosen[p][0] for p in ps if chosen[p][0].get("numbers_present") is not None]
            out[lang] = {"n": len(ps), "kept_o200k": round(kept, 4), "mean_sim": round(float(sims.mean()), 4),
                         "share_sim_below_0.80": round(float((sims < 0.80).mean()), 4),
                         "neg_lost": round(np.mean([r["neg_out"] < r["neg_in"] for r in neg]), 4) if neg else None,
                         "qw_lost": round(np.mean([r["qw_out"] < r["qw_in"] for r in qw]), 4) if qw else None,
                         "num_deleted": round(1 - np.mean([r["numbers_present"] for r in num]), 4) if num else None}
        return out

    report = {}
    for m in RATES:
        report[f"fixed {m}"] = score({p: cand(p, m) for p in pids})
    for tau in TAUS:
        chosen = {}
        for p in pids:
            pick = None
            for m in RATES:  # most aggressive first
                r, s = cand(p, m)
                if s >= tau:
                    pick = (r, s)
                    break
            chosen[p] = pick or cand(p, RATES[-1])  # nothing passes -> lightest rate
        report[f"adaptive tau={tau}"] = score(chosen)
    (BENCH / "adaptive_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for lang in ("english", "hinglish"):
        print(f"\n{lang}: {'method':24} {'kept':>6} {'sim':>6} {'<0.80':>6} {'neg':>6} {'qw':>6} {'numDel':>7}")
        for k, v in report.items():
            r = v.get(lang)
            if r:
                print(f"         {k:24} {r['kept_o200k']:>6} {r['mean_sim']:>6} {r['share_sim_below_0.80']:>6} "
                      f"{r['neg_lost']!s:>6} {r['qw_lost']!s:>6} {r['num_deleted']!s:>7}")


if __name__ == "__main__":
    main()
