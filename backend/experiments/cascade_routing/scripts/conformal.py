"""
conformal.py — Conformal Risk Calibration (Learn-Then-Test / Hoeffding bound).

For thresholds tau in linspace(0, 1, m=200):
    S(tau)   = {i : d(x_i) <= tau}
    n        = |S(tau)|
    R_hat    = mean(1 - acceptable_i) over S(tau)   (failure rate)
    R_ub     = R_hat + sqrt( log(m / delta) / (2n) )   (n=0 -> R_ub = inf)

tau* = max{ tau : R_ub(tau) <= alpha }, alpha=0.05 default.

Usage:
    python conformal.py --db cascade.db --alpha 0.05 --delta 0.05 --m 200
    python conformal.py --csv prompts_scored_labeled.csv --d-col d --label-col acceptable
"""
from __future__ import annotations
import argparse
import csv
import math
import sqlite3


def calibrate(ds: list[tuple[float, int]], m: int = 200, alpha: float = 0.05,
              delta: float = 0.05) -> tuple[float | None, list[dict]]:
    import numpy as np
    taus = [i / (m - 1) for i in range(m)]  # 0..1 inclusive
    log_term = math.log(m / delta)
    rows = []
    tau_star = None
    for tau in taus:
        sel = [y for (d, y) in ds if d <= tau]
        n = len(sel)
        if n == 0:
            r_hat, r_ub = 0.0, float("inf")
        else:
            fails = sum(1 for y in sel if y == 0)
            r_hat = fails / n
            r_ub = r_hat + math.sqrt(log_term / (2 * n))
        rows.append({"tau": round(tau, 4), "n": n,
                     "r_hat": round(r_hat, 4) if n else 0.0,
                     "r_ub": round(r_ub, 4) if n else float("inf")})
        if r_ub <= alpha:
            tau_star = tau
    return tau_star, rows


def load_from_db(db: str) -> list[tuple[float, int]]:
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT d, acceptable FROM responses WHERE d IS NOT NULL AND acceptable IS NOT NULL"
    ).fetchall()
    con.close()
    return [(float(d), int(a)) for d, a in rows]


def load_from_csv(path: str, d_col="d", label_col="acceptable") -> list[tuple[float, int]]:
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append((float(r[d_col]), int(float(r[label_col]))))
            except (ValueError, KeyError):
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="cascade.db")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--d-col", default="d")
    ap.add_argument("--label-col", default="acceptable")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--m", type=int, default=200)
    ap.add_argument("--out", default="calibration.csv")
    a = ap.parse_args()

    ds = load_from_csv(a.csv, a.d_col, a.label_col) if a.csv else load_from_db(a.db)
    print(f"labeled={len(ds)} alpha={a.alpha} delta={a.delta} m={a.m}")
    if not ds:
        print("No labeled data (acceptable IS NULL). Run judge.py first.")
        return

    tau_star, rows = calibrate(ds, a.m, a.alpha, a.delta)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tau", "n", "r_hat", "r_ub"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {a.out}")
    if tau_star is None:
        print(f"No tau satisfies R_ub <= {a.alpha}. Route everything to premium (tau*=None).")
    else:
        sel = [y for d, y in ds if d <= tau_star]
        cov = len(sel) / len(ds)
        print(f"tau* = {tau_star:.4f}  coverage={cov:.3f} (n={len(sel)}/{len(ds)})")
        print(f"Policy: if d(x) <= {tau_star:.4f} -> Qwen 7B else -> Gemini {__import__('os').environ.get('GEMINI_MODEL','gemini-2.5-flash')}")


if __name__ == "__main__":
    main()
