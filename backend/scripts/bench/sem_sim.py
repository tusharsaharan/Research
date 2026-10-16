"""Meaning-preservation proxy: cosine similarity between original and compressed
prompt embeddings (paraphrase-multilingual-MiniLM-L12-v2, handles Hinglish),
per language and method, over all compress_rows*.jsonl files. Offline.

Also reports the share of changed prompts with similarity < 0.80 ("likely
meaning drift", spot-check these by hand).

    python backend/scripts/bench/sem_sim.py
"""

from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from common import BENCH
from compress_eval import build_prompts

from gateway.modules.m4_router.certified import _encoder


def main() -> None:
    texts = {p["pid"]: (p["text"], p["lang"]) for p in build_prompts(8000, 20261016)}
    pairs = defaultdict(list)  # (lang, method) -> [(orig, comp)]
    for f in sorted(BENCH.glob("compress_rows*.jsonl")):
        if f.name == "compress_rows.jsonl" and any(BENCH.glob("compress_rows.*shard*.jsonl")):
            continue
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("changed") and r.get("compressed") and r["pid"] in texts:
                pairs[(r["lang"], r["method"])].append((texts[r["pid"]][0], r["compressed"]))
    enc = _encoder()
    out = {}
    for (lang, m), ps in sorted(pairs.items()):
        a = enc.encode([p[0] for p in ps], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        b = enc.encode([p[1] for p in ps], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        sim = (a * b).sum(1)
        out[f"{lang}|{m}"] = {"n_changed": len(ps), "mean_sim": round(float(sim.mean()), 4),
                              "p10_sim": round(float(np.quantile(sim, 0.1)), 4),
                              "share_below_0.80": round(float((sim < 0.8).mean()), 4)}
        print(f"{lang:9} {m:24} n={len(ps):5} mean={out[f'{lang}|{m}']['mean_sim']} "
              f"p10={out[f'{lang}|{m}']['p10_sim']} <0.80={out[f'{lang}|{m}']['share_below_0.80']}")
    (BENCH / "sem_sim_report.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
