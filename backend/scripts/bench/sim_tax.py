"""Overnight CPU simulations for the paper's theory figures (no API calls).

Known-truth model (as simulate_validity.py): scores s ~ U(0,1), P(u=1|s,g) = c_g*s,
risk R_g(lam) = c_g*lam^2/2, savings (cheap share) S_g(lam) = lam, oracle
lam*_g = min(1, sqrt(2*alpha/c_g)). Certification = certify.fixed_sequence.

  tax        certified savings gap (lam* - lam_hat) and violation vs n_g  -> Fig. 2 (expect slope ~ -1/2)
  mixshift   violation of marginal vs per-language as Hinglish share moves -> Fig. 3
  allocation total certified savings: proportional vs optimal (pi*rho)^(2/3) label split -> Cor. 5

    python backend/scripts/bench/sim_tax.py --trials 2000 --workers 14
"""

from __future__ import annotations

import argparse
import json
import math
from multiprocessing import Pool

import numpy as np
from certify import fixed_sequence
from common import BENCH

C = {"english": 0.3, "hinglish": 0.6}
GRID = np.linspace(0, 1, 201)


def oracle(c: float, alpha: float) -> float:
    return min(1.0, math.sqrt(2 * alpha / c))


def certify_once(rng, c: float, n: int, alpha: float, delta: float) -> float:
    s = rng.uniform(0, 1, n)
    u = (rng.uniform(0, 1, n) < c * s).astype(int)
    lam = fixed_sequence(s, u, GRID, alpha, delta)
    return max(lam, 0.0)


def job(task: tuple) -> dict:
    kind, params, seed, trials = task
    rng = np.random.default_rng(seed)
    if kind == "tax":
        g, n, alpha, delta = params
        c = C[g]
        lams = [certify_once(rng, c, n, alpha, delta) for _ in range(trials)]
        viol = np.mean([c * x * x / 2 > alpha for x in lams])
        return {"kind": kind, "group": g, "n": n, "alpha": alpha, "delta": delta,
                "gap_mean": float(oracle(c, alpha) - np.mean(lams)), "violation": float(viol)}
    if kind == "mixshift":
        share, n, alpha, delta = params
        out = {"marginal": 0, "per_language": 0}
        for _ in range(trials):
            nh = int(round(share * n))
            s_e, s_h = rng.uniform(0, 1, n - nh), rng.uniform(0, 1, nh)
            u_e = (rng.uniform(0, 1, n - nh) < C["english"] * s_e).astype(int)
            u_h = (rng.uniform(0, 1, nh) < C["hinglish"] * s_h).astype(int)
            lam = max(fixed_sequence(np.r_[s_e, s_h], np.r_[u_e, u_h], GRID, alpha, delta), 0)
            # calibrated at the training mix (share), served to Hinglish users: per-group risk
            out["marginal"] += C["hinglish"] * lam * lam / 2 > alpha
            lh = max(fixed_sequence(s_h, u_h, GRID, alpha, delta / 2), 0) if nh else 0.0
            out["per_language"] += C["hinglish"] * lh * lh / 2 > alpha
        return {"kind": kind, "hinglish_share": share, "n": n, "alpha": alpha,
                "hinglish_violation_marginal": out["marginal"] / trials,
                "hinglish_violation_per_language": out["per_language"] / trials}
    if kind == "allocation":
        budget, pi_h, alpha, delta = params
        pis = {"english": 1 - pi_h, "hinglish": pi_h}
        rho = {g: 1.0 / (C[g] * oracle(C[g], alpha)) for g in C}  # savings per unit risk at the margin
        w = {g: (pis[g] * rho[g]) ** (2 / 3) for g in C}
        plans = {"proportional": {g: pis[g] for g in C},
                 "optimal": {g: w[g] / sum(w.values()) for g in C},
                 "uniform": {g: 0.5 for g in C}}
        res = {}
        for name, frac in plans.items():
            tot = []
            for _ in range(trials):
                tot.append(sum(pis[g] * certify_once(rng, C[g], max(10, int(budget * frac[g])), alpha, delta / 2)
                               for g in C))
            res[name] = float(np.mean(tot))
        return {"kind": kind, "budget": budget, "hinglish_share": pi_h, "alpha": alpha, "certified_savings": res}
    raise ValueError(kind)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--delta", type=float, default=0.10)
    args = ap.parse_args()
    d = args.delta
    tasks = []
    k = 0
    for g in C:
        for n in (50, 100, 200, 400, 800, 1600, 3200):
            for a in (0.05, 0.10, 0.20):
                tasks.append(("tax", (g, n, a, d / 2), k, args.trials)); k += 1
    for share in (0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        for a in (0.05, 0.10):
            tasks.append(("mixshift", (share, 1000, a, d), k, args.trials)); k += 1
    for budget in (200, 500, 1000, 2000):
        for pi_h in (0.1, 0.2, 0.3):
            tasks.append(("allocation", (budget, pi_h, 0.10, d), k, args.trials // 4)); k += 1
    with Pool(args.workers) as pool:
        results = pool.map(job, tasks, chunksize=1)
    out = BENCH / "sim_tax_report.json"
    out.write_text(json.dumps({"delta": d, "trials": args.trials, "c": C, "results": results}, indent=2))
    tax = [r for r in results if r["kind"] == "tax" and r["alpha"] == 0.10]
    for g in C:
        pts = [(r["n"], r["gap_mean"]) for r in tax if r["group"] == g and r["gap_mean"] > 0]
        slope = np.polyfit(np.log([p[0] for p in pts]), np.log([p[1] for p in pts]), 1)[0]
        print(f"{g}: log-log slope of savings gap vs n = {slope:.3f} (theory -0.5); "
              f"max violation {max(r['violation'] for r in tax if r['group'] == g):.3f}")
    print("report ->", out)


if __name__ == "__main__":
    main()
