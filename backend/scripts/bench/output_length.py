"""Does prompt compression change answer length? Paired input/output/total token
ratios (compressed vs original prompt, same item) with a 95% bootstrap CI on the
output ratio, from the Kaggle answers (Qwen2.5-3B). CondaQA rows excluded.

    python output_length.py   -> data/bench/output_length_report.json
"""

from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from common import BENCH


def main() -> None:
    d: dict = defaultdict(dict)
    for x in open(BENCH / "kaggle" / "answers.jsonl", encoding="utf-8"):
        r = json.loads(x)
        if r["item_id"].startswith("cq-"):
            continue
        for m in r["methods"]:
            d[(r["item_id"], r["lang"])][m] = (r["prompt_tokens"], r["completion_tokens"])
    methods = sorted({m for v in d.values() for m in v} - {"original"})
    rng = np.random.default_rng(0)
    out = {}
    for lang in ("english", "hinglish"):
        for m in methods:
            pairs = [(v["original"], v[m]) for (_, lg), v in d.items() if lg == lang and m in v and "original" in v]
            if not pairs:
                continue
            o = np.array([a for a, _ in pairs], dtype=float)
            c = np.array([b for _, b in pairs], dtype=float)
            boot = [c[i, 1].sum() / o[i, 1].sum() for i in (rng.integers(0, len(pairs), len(pairs)) for _ in range(1000))]
            res = {"n": len(pairs), "input_ratio": round(c[:, 0].sum() / o[:, 0].sum(), 4),
                   "output_ratio": round(c[:, 1].sum() / o[:, 1].sum(), 4),
                   "output_ratio_ci95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
                   "total_ratio": round(c.sum() / o.sum(), 4)}
            out[f"{m}|{lang}"] = res
            print(f"{lang:8} {m:26} in={res['input_ratio']:.3f} out={res['output_ratio']:.3f} "
                  f"{res['output_ratio_ci95']} total={res['total_ratio']:.3f}")
    (BENCH / "output_length_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
