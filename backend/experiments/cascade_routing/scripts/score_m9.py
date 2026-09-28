"""score_m9.py — Difficulty labeling using the REAL m9_reasoning budget calculation.

Uses gateway.modules.m9_reasoning.budget.ReasoningBudgetEstimator (same weights,
same _MATH/_LOGIC regexes, same m1 code_mix_ratio) and maps its token budget
to a [0,1] difficulty score for conformal calibration:

    d(x) = (budget(x) - base_budget) / (max_budget - base_budget), clipped [0,1]

Defaults: base=128, max=2048 (the estimator's own defaults).

Usage (run from cascade_routing/):
    python scripts/score_m9.py
    python scripts/score_m9.py --input data/prompts.csv --output data/prompts_scored.csv
"""
from __future__ import annotations
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # cascade_routing/
BACKEND_SRC = os.path.abspath(os.path.join(HERE, "..", "..", "..", "src"))
sys.path.insert(0, BACKEND_SRC)

from gateway.modules.m9_reasoning.budget import ReasoningBudgetEstimator  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(ROOT, "data", "prompts.csv"))
    ap.add_argument("--output", default=os.path.join(ROOT, "data", "prompts_scored.csv"))
    ap.add_argument("--backup-old", default=os.path.join(ROOT, "scratch", "prompts_scored_legacy.csv"))
    a = ap.parse_args()

    est = ReasoningBudgetEstimator()
    lo, hi = est.base_budget, est.max_budget

    with open(a.input, encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        col = next((c for c in ["prompt", "instruction", "text"] if c in rdr.fieldnames), rdr.fieldnames[0])
        prompts = [(r.get(col) or "").strip() for r in rdr]
    prompts = [p for p in prompts if p]

    if os.path.exists(a.output):
        os.replace(a.output, a.backup_old)
        print(f"old scores backed up -> {a.backup_old}")

    n_tok = lambda t: len(t.split())  # noqa: E731 - same whitespace count as budget.py _features
    with open(a.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["prompt", "n_tokens", "code_mix", "math_count", "logic_count", "budget", "d"])
        w.writeheader()
        for p in prompts:
            b = est.estimate(p)
            d = min(1.0, max(0.0, (b.reasoning_tokens - lo) / (hi - lo)))
            w.writerow({"prompt": p, "n_tokens": n_tok(p), "code_mix": b.code_mix_ratio,
                        "math_count": b.math_marker_count, "logic_count": b.logic_marker_count,
                        "budget": b.reasoning_tokens, "d": round(d, 4)})
    print(f"scored {len(prompts)} prompts with m9 budget -> {a.output} (base={lo} max={hi})")


if __name__ == "__main__":
    main()
