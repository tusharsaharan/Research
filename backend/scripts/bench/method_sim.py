"""Mean embedding similarity + compression + meaning-unit loss for chosen methods
(reuses adaptive_emb_cache.npz, so only new texts are embedded).

    python backend/scripts/bench/method_sim.py lexical-safe lexical-safe+guarded@0.5 crf+guarded@0.5 guarded2@0.5
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import torch
from adaptive_eval import CACHE
from common import BENCH
from compress_eval import build_prompts

from gateway.modules.m4_router.certified import _encoder


def main() -> None:
    torch.set_num_threads(os.cpu_count() or 4)
    want = set(sys.argv[1:])
    prompts = {p["pid"]: p for p in build_prompts(8000, 20261016)}
    rows, seen = defaultdict(list), set()
    for f in glob.glob(str(BENCH / "compress_rows.*shard*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["method"] in want and r["pid"] in prompts and (r["pid"], r["method"]) not in seen:
                seen.add((r["pid"], r["method"]))
                rows[r["method"]].append(r)
    emb = {}
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        emb = dict(zip(z["keys"].tolist(), z["vecs"]))
    def text(r):
        return r["compressed"] if r["changed"] and r.get("compressed") else prompts[r["pid"]]["text"]
    need = {prompts[r["pid"]]["text"] for rs in rows.values() for r in rs} | {text(r) for rs in rows.values() for r in rs}
    todo = [t for t in need if t not in emb]
    print(f"embedding {len(todo)} new texts", flush=True)
    if todo:
        emb.update(zip(todo, _encoder().encode(todo, batch_size=128, normalize_embeddings=True, show_progress_bar=False)))
        np.savez(CACHE, keys=np.array(list(emb), dtype=object), vecs=np.stack(list(emb.values())))
    out = {}
    for m, rs in sorted(rows.items()):
        for lang in ("english", "hinglish"):
            sub = [r for r in rs if r["lang"] == lang]
            if not sub:
                continue
            sims = np.array([float(emb[prompts[r["pid"]]["text"]] @ emb[text(r)]) for r in sub])
            kept = sum(r["tokens_after"]["o200k"] for r in sub) / sum(r["tokens_before"]["o200k"] for r in sub)
            neg = [r for r in sub if r["neg_in"]]
            qw = [r for r in sub if r["qw_in"]]
            out[f"{m}|{lang}"] = {"n": len(sub), "kept_o200k": round(kept, 4), "mean_sim": round(float(sims.mean()), 4),
                                  "share_sim_below_0.80": round(float((sims < 0.8).mean()), 4),
                                  "neg_lost": round(float(np.mean([r["neg_out"] < r["neg_in"] for r in neg])), 4) if neg else None,
                                  "qw_lost": round(float(np.mean([r["qw_out"] < r["qw_in"] for r in qw])), 4) if qw else None}
            o = out[f"{m}|{lang}"]
            print(f"{m:28} {lang:8} n={o['n']:5} kept={o['kept_o200k']} sim={o['mean_sim']} <0.80={o['share_sim_below_0.80']} "
                  f"neg={o['neg_lost']} qw={o['qw_lost']}")
    (BENCH / "method_sim_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
