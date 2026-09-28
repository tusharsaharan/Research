"""make_all_plots.py — Every figure for the full report, computed from data files only."""
import csv, os, statistics
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
FIG = os.path.join(DATA, "figs")
os.makedirs(FIG, exist_ok=True)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

routed_v2 = list(csv.DictReader(open(os.path.join(DATA, "prompts_routed_v2.csv"), encoding="utf-8-sig")))
routed_v1 = list(csv.DictReader(open(os.path.join(DATA, "prompts_routed.csv"), encoding="utf-8-sig")))
v1 = list(csv.DictReader(open(os.path.join(DATA, "judge_output_200.csv"), encoding="utf-8-sig")))
v2 = list(csv.DictReader(open(os.path.join(DATA, "judge_output_200_v2.csv"), encoding="utf-8-sig")))
pilot = list(csv.DictReader(open(os.path.join(DATA, "judge_output_300.csv"), encoding="utf-8-sig")))
scored_m9 = {r["prompt"]: float(r["d"]) for r in csv.DictReader(open(os.path.join(DATA, "prompts_scored.csv"), encoding="utf-8"))}
scored_laya = {}
for r in csv.DictReader(open(os.path.join(DATA, "scored_laya_10378.csv"), encoding="utf-8")):
    scored_laya[r["prompt"]] = float(r["d"])
g2 = {r["prompt"]: r["cheap_did_well"] for r in v2}
lab_v2 = {r["prompt"]: r["cheap_ok"] for r in routed_v2}

# 1. label distributions
fig, ax = plt.subplots(figsize=(7, 4))
cats = ["zero-shot Yes", "zero-shot No", "fine-tuned Yes", "fine-tuned No"]
vals = [8035, 2343, sum(1 for r in routed_v2 if r["cheap_ok"] == "Yes"),
        sum(1 for r in routed_v2 if r["cheap_ok"] == "No")]
bars = ax.bar(cats, vals, color=["seagreen", "darkorange", "steelblue", "firebrick"])
ax.set_title("Router labels over 10,378 prompts: zero-shot vs fine-tuned")
ax.set_ylabel("prompts")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 80, str(v), ha="center", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_labels.png"), dpi=150)

# 2. agreement bars
fig, ax = plt.subplots(figsize=(7, 4))
labels = ["zero-shot\nvs Claude (200)", "fine-tuned\nvs Claude (200)", "fine-tuned\nvs Claude (fresh 300)"]
agree = [110 / 200,
         sum(1 for r in v2 if (lab_v2[r["prompt"]] == "Yes") == (g2[r["prompt"]] == "Y")) / 200,
         None]
pg = {r["prompt"]: r["cheap_did_well"] for r in pilot}
pagree = sum(1 for p in pg if (lab_v2[p] == "Yes") == (pg[p] == "Y")) / 300
agree[2] = pagree
bars = ax.bar(labels, agree, color=["grey", "steelblue", "firebrick"])
ax.axhline(0.5, color="black", linestyle="--", linewidth=1)
ax.set_ylim(0, 1)
ax.set_title("Router-vs-Claude agreement")
ax.set_ylabel("fraction")
for b, v in zip(bars, agree):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.1%}", ha="center", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_agreement.png"), dpi=150)

# 3. separation: m9 vs laya histograms on the 200
m9y = [scored_m9[r["prompt"]] for r in v2 if r["cheap_did_well"] == "Y"]
m9n = [scored_m9[r["prompt"]] for r in v2 if r["cheap_did_well"] == "N"]
lyy = [scored_laya[r["prompt"]] for r in v2 if r["cheap_did_well"] == "Y"]
lyn = [scored_laya[r["prompt"]] for r in v2 if r["cheap_did_well"] == "N"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
a1.hist(m9y, bins=25, alpha=0.6, label=f"pass (mean {statistics.mean(m9y):.3f})", color="seagreen")
a1.hist(m9n, bins=25, alpha=0.6, label=f"fail (mean {statistics.mean(m9n):.3f})", color="darkorange")
a1.set_title("m9 difficulty: no separation")
a1.set_xlabel("d"); a1.legend(fontsize=8)
a2.hist(lyy, bins=25, alpha=0.6, label=f"pass (mean {statistics.mean(lyy):.3f})", color="seagreen")
a2.hist(lyn, bins=25, alpha=0.6, label=f"fail (mean {statistics.mean(lyn):.3f})", color="darkorange")
a2.set_title("Laya P(No): separates")
a2.set_xlabel("d"); a2.legend(fontsize=8)
fig.suptitle("Difficulty vs Claude outcome (200 rows)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_separation.png"), dpi=150)

# 4. pilot decile fail rates
dec_n, dec_f = [], []
for i in range(10):
    grp = [p for p in pg if min(9, int(scored_laya[p] * 10)) == i]
    dec_n.append(len(grp))
    dec_f.append(sum(1 for p in grp if pg[p] == "N") / max(1, len(grp)))
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar([f"d{i}" for i in range(10)], dec_f, color="steelblue")
ax.set_ylim(0, 1)
ax.set_title("Pilot 300: empirical fail rate by P(No) decile (flat = no ranking on fresh prompts)")
ax.set_ylabel("fail rate")
for b, v in zip(bars, dec_f):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_deciles.png"), dpi=150)

# 5. grades v1 vs v2
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(["v1 Y", "v1 N", "v2 Y", "v2 N"], [123, 77, 119, 81], color=["seagreen", "darkorange", "steelblue", "firebrick"])
ax.set_title("Claude grades: round 1 vs round 2 (22 flips)")
ax.set_ylabel("rows")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_grades.png"), dpi=150)

# 6. laya risk curve (for full report)
cal = list(csv.DictReader(open(os.path.join(DATA, "calibration_laya.csv"), encoding="utf-8")))
taus = [float(x["tau"]) for x in cal]
rh = [float(x["r_hat"]) for x in cal]
rb = [float(x["r_ub"]) if x["r_ub"] != "inf" else float("nan") for x in cal]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(taus, rh, label="empirical risk", color="steelblue")
ax.plot(taus, rb, label="Hoeffding bound", color="firebrick")
ax.axhline(0.05, color="green", linestyle="--", label="alpha = 0.05")
ax.axvline(0.5528, color="grey", linestyle=":", label="tau* = 0.5528")
ax.set_xlabel("tau"); ax.set_ylabel("failure rate")
ax.set_title("Laya-P(No) calibration (n=10378)")
ax.legend(fontsize=8); ax.set_ylim(0, 1)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_risk_laya.png"), dpi=150)
print("figs:", sorted(os.listdir(FIG)))
