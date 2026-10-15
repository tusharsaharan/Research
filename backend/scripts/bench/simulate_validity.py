"""Known-truth check of the certification code used by certify.py.

Synthetic routing data where the true risk curve of each language is known:
scores s ~ U(0,1), P(u=1 | s, group) = c_g * s, so R_g(lam) = c_g * lam^2 / 2
(route cheap iff s <= lam). Hinglish gets the steeper curve. A certification
is violated when the TRUE risk at the certified threshold exceeds alpha.

Expected: per-language violation rate <= delta in both groups; the marginal
threshold (pooled data) over-risks the steeper group.

    python backend/scripts/bench/simulate_validity.py
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from certify import fixed_sequence
from common import BENCH
from scipy.stats import beta as beta_dist

C = {"english": 0.3, "hinglish": 0.6}


def true_risk(g: str, lam: float) -> float:
    lam = min(max(lam, 0.0), 1.0)
    return C[g] * lam * lam / 2


def cp_ci(k: int, n: int) -> list[float]:
    lo = beta_dist.ppf(0.025, k, n - k + 1) if k else 0.0
    hi = beta_dist.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return [round(float(lo), 3), round(float(hi), 3)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--n-per-group", type=int, default=400)
    ap.add_argument("--hinglish-share", type=float, default=0.3)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--delta", type=float, default=0.10)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    grid = np.linspace(0, 1, 101)
    viol = {("per_language", g): 0 for g in C} | {("marginal", g): 0 for g in C}
    viol_marg_pooled = 0
    p = args.hinglish_share
    for _ in range(args.trials):
        data = {}
        for g in C:
            n = args.n_per_group
            s = rng.uniform(0, 1, n)
            u = (rng.uniform(0, 1, n) < C[g] * s).astype(int)
            data[g] = (s, u)
        # per-language: delta split over the 2 groups
        for g, (s, u) in data.items():
            lam = fixed_sequence(s, u, grid, args.alpha, args.delta / 2)
            viol[("per_language", g)] += true_risk(g, lam) > args.alpha
        # marginal: pooled sample with the given Hinglish share
        n_h = int(round(p * args.n_per_group * 2))
        n_e = args.n_per_group * 2 - n_h
        s = np.concatenate([data["english"][0][: min(n_e, args.n_per_group)], data["hinglish"][0][: min(n_h, args.n_per_group)]])
        u = np.concatenate([data["english"][1][: min(n_e, args.n_per_group)], data["hinglish"][1][: min(n_h, args.n_per_group)]])
        lam = fixed_sequence(s, u, grid, args.alpha, args.delta)
        for g in C:
            viol[("marginal", g)] += true_risk(g, lam) > args.alpha
        viol_marg_pooled += ((1 - p) * true_risk("english", lam) + p * true_risk("hinglish", lam)) > args.alpha

    t = args.trials
    out = {"setup": vars(args) | {"risk_curves": "R_g(lam) = c_g lam^2 / 2", "c": C},
           "violation_rate": {f"{m}/{g}": {"rate": round(v / t, 4), "ci95": cp_ci(v, t)} for (m, g), v in viol.items()},
           "marginal_pooled_violation_rate": {"rate": round(viol_marg_pooled / t, 4), "ci95": cp_ci(viol_marg_pooled, t)}}
    ok = all(viol[("per_language", g)] / t <= args.delta + 2 * np.sqrt(args.delta / t) for g in C)
    out["per_language_valid"] = bool(ok)
    (BENCH / "simulation_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
