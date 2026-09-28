"""calibrate_v2.py — Join m9 d + fine-tuned v2 labels -> tau* via Hoeffding LTT grid.

Label: cheap_ok Yes -> 1 (cheap suffices), No -> 0.
Writes data/calibration_v2.csv (tau, n, r_hat, r_ub).
Usage: python scripts/calibrate_v2.py [--alpha 0.05 --delta 0.05 --m 200]
"""
import argparse, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from conformal import calibrate  # noqa: E402

DATA = os.path.join(HERE, "..", "data")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--m", type=int, default=200)
    a = ap.parse_args()
    dmap = {r["prompt"]: float(r["d"]) for r in csv.DictReader(open(os.path.join(DATA, "prompts_scored.csv"), encoding="utf-8"))}
    routed = list(csv.DictReader(open(os.path.join(DATA, "prompts_routed_v2.csv"), encoding="utf-8-sig")))
    ds, missing = [], 0
    for r in routed:
        if r["prompt"] in dmap:
            ds.append((dmap[r["prompt"]], 1 if r["cheap_ok"] == "Yes" else 0))
        else:
            missing += 1
    print(f"joined={len(ds)} missing={missing} base_rate={sum(y for _, y in ds)/len(ds):.3f}", flush=True)
    tau_star, rows = calibrate(ds, a.m, a.alpha, a.delta)
    with open(os.path.join(DATA, "calibration_v2.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tau", "n", "r_hat", "r_ub"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote data/calibration_v2.csv ({len(rows)} grid points)", flush=True)
    if tau_star is None:
        print(f"RESULT: no tau satisfies R_ub <= {a.alpha} -> route everything to premium")
    else:
        sel = [y for d, y in ds if d <= tau_star]
        print(f"RESULT: tau* = {tau_star:.4f} coverage={len(sel)/len(ds):.3f} "
              f"(n={len(sel)}/{len(ds)}) r_hat={sum(1 for y in sel if y==0)/max(1,len(sel)):.4f}")

if __name__ == "__main__":
    main()
