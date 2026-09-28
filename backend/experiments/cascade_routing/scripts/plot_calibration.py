"""plot_calibration.py — Risk-vs-tau curve + d histograms (v2 labels, m9 d)."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

cal = list(csv.DictReader(open(os.path.join(DATA, "calibration_v2.csv"), encoding="utf-8")))
taus = [float(r["tau"]) for r in cal]
ns = [int(r["n"]) for r in cal]
rh = [float(r["r_hat"]) for r in cal]
rb = [float(r["r_ub"]) if r["r_ub"] != "inf" else float("nan") for r in cal]

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(taus, rh, label="empirical risk R_hat(tau)", color="steelblue")
ax.plot(taus, rb, label="Hoeffding bound R_ub(tau)", color="firebrick")
ax.axhline(0.05, color="green", linestyle="--", label="alpha = 0.05")
ax.set_xlabel("tau (route to cheap if d(x) <= tau)")
ax.set_ylabel("failure rate")
ax.set_title("Conformal calibration: fine-tuned router labels + m9 d (n=10378)")
ax.legend(fontsize=8)
ax.set_ylim(0, 1)
fig.tight_layout()
fig.savefig(os.path.join(DATA, "risk_curve_v2.png"), dpi=150)

sc = list(csv.DictReader(open(os.path.join(DATA, "prompts_scored.csv"), encoding="utf-8")))
rt = {r["prompt"]: r["cheap_ok"] for r in csv.DictReader(open(os.path.join(DATA, "prompts_routed_v2.csv"), encoding="utf-8-sig"))}
dy = [float(r["d"]) for r in sc if rt.get(r["prompt"]) == "Yes"]
dn = [float(r["d"]) for r in sc if rt.get(r["prompt"]) == "No"]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(dy, bins=50, alpha=0.6, label=f"Yes (n={len(dy)})", color="seagreen")
ax.hist(dn, bins=50, alpha=0.6, label=f"No (n={len(dn)})", color="darkorange")
ax.set_xlabel("m9 difficulty d(x)")
ax.set_ylabel("prompts")
ax.set_title("Difficulty distribution by router label")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(DATA, "difficulty_hist_v2.png"), dpi=150)
print("plots saved")
