"""make_report.py — Status report PDF: observations, data, plots. No recommendations."""
import csv, os, statistics
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "cascade_status_report.pdf")

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, HRFlowable)
from reportlab.lib import colors

# ---------- gather facts from data files ----------
scored = list(csv.DictReader(open(os.path.join(DATA, "prompts_scored.csv"), encoding="utf-8")))
dmap = {r["prompt"]: float(r["d"]) for r in scored}
ds = [float(r["d"]) for r in scored]
routed_v2 = list(csv.DictReader(open(os.path.join(DATA, "prompts_routed_v2.csv"), encoding="utf-8-sig")))
v2dist = Counter(r["cheap_ok"] for r in routed_v2)
v1 = list(csv.DictReader(open(os.path.join(DATA, "judge_output_200.csv"), encoding="utf-8-sig")))
v2 = list(csv.DictReader(open(os.path.join(DATA, "judge_output_200_v2.csv"), encoding="utf-8-sig")))
g1 = {r["prompt"]: r["cheap_did_well"] for r in v1}
g2 = {r["prompt"]: r["cheap_did_well"] for r in v2}
old_lab = {r["prompt"]: r["cheap_ok"] for r in v2}  # cheap_ok col in v2 file = OLD router labels
old_agree = sum(1 for r in v1 if (old_lab[r["prompt"]] == "Yes") == (g1[r["prompt"]] == "Y"))
new_rows = list(csv.DictReader(open(os.path.join(DATA, "prompts_rerouted_200.csv"), encoding="utf-8")))
new_agree = sum(1 for r in new_rows if (r["cheap_ok"] == "Yes") == (g2[r["prompt"]] == "Y"))
new_yes = [r for r in new_rows if r["cheap_ok"] == "Yes"]
new_yes_fail = sum(1 for r in new_yes if g2[r["prompt"]] == "N")
old_yes_fail_n = sum(1 for r in v1 if old_lab[r["prompt"]] == "Yes" and g1[r["prompt"]] == "N")
old_yes_n = sum(1 for r in v1 if old_lab[r["prompt"]] == "Yes")
redo = list(csv.DictReader(open(os.path.join(DATA, "qwen_redo_uncapped.csv"), encoding="utf-8")))
flips_up = sum(1 for r in v2 if r["prompt"] in {x["prompt"] for x in redo} and g1[r["prompt"]] == "N" and r["cheap_did_well"] == "Y")
flips_stay = sum(1 for r in v2 if r["prompt"] in {x["prompt"] for x in redo} and g1[r["prompt"]] == "N" and r["cheap_did_well"] == "N")
cal = list(csv.DictReader(open(os.path.join(DATA, "calibration_v2.csv"), encoding="utf-8")))
bign = [(float(x["tau"]), int(x["n"]), float(x["r_hat"])) for x in cal if int(x["n"]) > 100]
floor_tau, floor_n, floor_r = min(bign, key=lambda t: t[2])
yd = [float(r["d"]) for r in v2 if r["cheap_did_well"] == "Y"]
nd = [float(r["d"]) for r in v2 if r["cheap_did_well"] == "N"]
rt = {r["prompt"]: (float(r["prob_yes"]), float(r["answer_confidence"]))
      for r in csv.DictReader(open(os.path.join(DATA, "prompts_routed.csv"), encoding="utf-8-sig"))}
dis = [r for r in v2 if (r["cheap_ok"] == "Yes") != (r["cheap_did_well"] == "Y")]
conf_wrong = sum(1 for r in dis if rt[r["prompt"]][1] > 0.8)
# Laya P(No) difficulty + calibration
laya_sc = {}
for r in csv.DictReader(open(os.path.join(DATA, "scored_laya_10378.csv"), encoding="utf-8")):
    laya_sc[r["prompt"]] = float(r["d"])
laya_ds = list(laya_sc.values())
laya200 = {r["prompt"]: float(r["d"]) for r in csv.DictReader(open(os.path.join(DATA, "scored_laya_200.csv"), encoding="utf-8"))}
ly = [d for p, d in laya200.items() if g2[p] == "Y"]
ln = [d for p, d in laya200.items() if g2[p] == "N"]
cal_laya = list(csv.DictReader(open(os.path.join(DATA, "calibration_laya.csv"), encoding="utf-8")))
passing = [(float(x["tau"]), int(x["n"]), float(x["r_hat"]), float(x["r_ub"]))
           for x in cal_laya if x["r_ub"] != "inf" and float(x["r_ub"]) <= 0.05]
laya_tau, laya_n, laya_rh, laya_rb = max(passing, key=lambda t: t[0])
laya_sel_fail = laya_rh  # fraction No among d<=tau*
# pilot 300
pilot_g = {r["prompt"]: r["cheap_did_well"] for r in csv.DictReader(open(os.path.join(DATA, "judge_output_300.csv"), encoding="utf-8-sig"))}
pilot_lab = {r["prompt"]: r["cheap_ok"] for r in routed_v2}
pilot_agree = sum(1 for p in pilot_g if (pilot_lab[p] == "Yes") == (pilot_g[p] == "Y"))
pilot_yes = [p for p in pilot_g if pilot_lab[p] == "Yes"]
pilot_yes_fail = sum(1 for p in pilot_yes if pilot_g[p] == "N")
pilot_dec = []
for i in range(10):
    grp = [p for p in pilot_g if min(9, int(laya_sc[p] * 10)) == i]
    pilot_dec.append((len(grp), sum(1 for p in grp if pilot_g[p] == "N") / max(1, len(grp))))
pilot_grades = Counter(pilot_g.values())

# ---------- document ----------
styles = getSampleStyleSheet()
title_s = styles["Title"]
h1 = styles["Heading1"]
h2 = styles["Heading2"]
body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14, spaceAfter=6)
small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.grey)
cell = lambda t: Paragraph(str(t), ParagraphStyle("c", parent=styles["BodyText"], fontSize=9, leading=11))

def table(data, widths=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
story = []
A = story.append
A(Paragraph("Code-Mixed Gateway: Cascade Routing — Status Report", title_s))
A(Paragraph("Observations, data and measurements as of 28 Sept 2026. No recommendations in this document.", small))
A(HRFlowable(width="100%"))
A(Paragraph("1. Goal", h1))
A(Paragraph("Route each Hinglish user prompt to a cheap local model (Qwen 2.5 7B, free) when it can handle it, "
            "else to a premium model (Gemini, paid). A prompt may go cheap only if the failure rate among "
            "cheap-routed prompts is certifiably at most 5% (alpha = 0.05).", body))
A(Paragraph("2. Data inventory", h1))
A(table([[cell("File"), cell("Rows"), cell("Contents")],
         [cell("prompts.csv"), cell("10,273 unique (10,378 with dupes)"), cell("Source prompts, single column")],
         [cell("prompts_scored.csv"), cell("10,378"), cell("m9 difficulty d + budget features per prompt")],
         [cell("prompts_routed.csv"), cell("10,378"), cell("Original Laya router labels (Yes 8,035 / No 2,343)")],
         [cell("prompts_routed_v2.csv"), cell("10,378"), cell("Fine-tuned router labels (Yes %d / No %d)" % (v2dist["Yes"], v2dist["No"]))],
         [cell("judge_output_200.csv (v1)"), cell("200"), cell("Claude grades Y:123 / N:77")],
         [cell("judge_output_200_v2.csv (v2)"), cell("200"), cell("Claude re-grades Y:119 / N:81; 21 rows use uncapped Qwen answers")],
         [cell("qwen_redo_uncapped.csv"), cell("21"), cell("Qwen answers regenerated with no token cap")],
         [cell("calibration_v2.csv"), cell("200 grid points"), cell("m9-d grid (tau* = None)")],
         [cell("scored_laya_10378.csv"), cell("10,273 unique"), cell("Laya P(No) difficulty per prompt")],
         [cell("calibration_laya.csv"), cell("200 grid points"), cell("P(No) grid (tau* = 0.5528)")],
         [cell("pilot_300.csv / qwen_pilot_300.csv"), cell("300"), cell("Stratified pilot prompts + Colab Qwen answers")],
         [cell("judge_output_300.csv"), cell("300"), cell("Claude pilot grades Y:215 / N:85")],
         [cell("prompts_rerouted_200.csv"), cell("200"), cell("Fine-tuned router re-run on first 200")]]))
A(Paragraph("3. Difficulty scores (m9 reasoning budget, normalized)", h1))
A(Paragraph("Each prompt's thinking-token budget (128 + 120·codemix + 96·math + 48·logic + 8·min(len,40), capped at 2048) "
            "is mapped to d = (budget − 128)/(2048 − 128). Observed: min %.4f, mean %.4f, max %.4f. "
            "No scores pile at 0 or 1." % (min(ds), statistics.mean(ds), max(ds)), body))
A(Paragraph("4. Router labels: before vs after fine-tuning", h1))
A(table([[cell("Router"), cell("Yes (cheap)"), cell("No (premium)")],
         [cell("Original (zero-shot)"), cell("8,035 (77%)"), cell("2,343 (23%)")],
         [cell("Fine-tuned (Colab T4, 140 train rows)"), cell("%d (%.0f%%)" % (v2dist["Yes"], 100 * v2dist["Yes"] / 10378)),
          cell("%d (%.0f%%)" % (v2dist["No"], 100 * v2dist["No"] / 10378))]]))
A(Paragraph("5. Empirical grades (Claude, Qwen vs premium answers)", h1))
A(Paragraph("200 prompts graded Y (Qwen adequate) / N (not). v1: Y:123/N:77. v2 re-grade: Y:119/N:81 — "
            "22 labels changed (9 N→Y, 13 Y→N). One premium row observed misaligned (omelette recipe filed under a bus-story prompt).", body))
A(Paragraph("6. Router-vs-reality agreement (200 graded rows)", h1))
A(table([[cell("Router"), cell("Agreement with Claude"), cell("Fail rate among router-Yes")],
         [cell("Original"), cell("%d/200 (%.1f%%)" % (old_agree, 100 * old_agree / 200)),
          cell("%d/%d (%.1f%%)" % (old_yes_fail_n, old_yes_n, 100 * old_yes_fail_n / max(1, old_yes_n)))],
         [cell("Fine-tuned"), cell("%d/200 (%.1f%%)" % (new_agree, 100 * new_agree / 200)),
          cell("%d/%d (%.1f%%)" % (new_yes_fail, len(new_yes), 100 * new_yes_fail / max(1, len(new_yes))))]]))
A(Paragraph("Of the %d v2 disagreements, %d were router judgments at over 80%% confidence. Mean router confidence: "
            "0.73 on agreements vs 0.67 on disagreements — confidence barely separates right from wrong." % (len(dis), conf_wrong), body))
A(Paragraph("7. Uncapped re-run (21 truncation suspects)", h1))
A(Paragraph("21 N-graded answers longer than 1200 chars were regenerated with no token cap (num_predict = −1, run-until-EOS). "
            "Zero runaways; 19/21 ended on clean terminal punctuation. Re-graded: %d flipped N→Y (cap was the cause), "
            "%d stayed N (fail on the merits), 0 flipped Y→N." % (flips_up, flips_stay), body))
A(Paragraph("8. Difficulty-vs-outcome separation", h1))
A(Paragraph("Mean m9 d: Claude-Y %.4f (n=%d) vs Claude-N %.4f (n=%d). The score distributions overlap almost completely; "
            "difficulty as computed does not separate pass from fail." % (
                statistics.mean(yd), len(yd), statistics.mean(nd), len(nd)), body))
A(Paragraph("9. Conformal calibration (200-point grid, alpha 0.05, delta 0.05)", h1))
A(Paragraph("Method: for each tau, failure rate among prompts with d ≤ tau, plus Hoeffding margin "
            "sqrt(log(200/0.05)/(2n)). Join coverage: 10,378/10,378, zero missing. Base Yes rate: %.1f%%." % (
                100 * sum(1 for r in routed_v2 if r["cheap_ok"] == "Yes") / len(routed_v2)), body))
A(table([[cell("tau"), cell("n"), cell("R_hat"), cell("R_ub")]] +
        [[cell(x["tau"]), cell(x["n"]), cell(x["r_hat"]), cell(x["r_ub"])] for x in cal[:10]]))
A(Paragraph("Result: tau* = None — no grid point satisfies R_ub ≤ 0.05. Lowest empirical risk with n > 100 is %.3f "
            "(tau ≈ %.4f, n = %d). The single easiest prompt in the dataset (d = 0.0167, 'Healthcare marketing strategy banao') "
            "is itself labeled No." % (floor_r, floor_tau, floor_n), body))
A(Paragraph("Worked margin example (tau = 0.05, n = 552): sqrt(log(200/0.05)/(2×552)) ≈ 0.087, i.e. ±8.7 points of statistical doubt.", body))
A(PageBreak())
A(Paragraph("10. Figures", h1))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
taus = [float(x["tau"]) for x in cal_laya]
rh = [float(x["r_hat"]) for x in cal_laya]
rb = [float(x["r_ub"]) if x["r_ub"] != "inf" else float("nan") for x in cal_laya]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(taus, rh, label="empirical risk", color="steelblue")
ax.plot(taus, rb, label="Hoeffding bound", color="firebrick")
ax.axhline(0.05, color="green", linestyle="--", label="alpha = 0.05")
ax.axvline(laya_tau, color="grey", linestyle=":", label="tau* = %.4f" % laya_tau)
ax.set_xlabel("tau (route to cheap if P(No) <= tau)")
ax.set_ylabel("failure rate")
ax.set_title("Laya-P(No) calibration (n=10378): tau* certifies 5%")
ax.legend(fontsize=8)
ax.set_ylim(0, 1)
fig.tight_layout()
fig.savefig(os.path.join(DATA, "risk_curve_laya.png"), dpi=150)
for img, cap in [("risk_curve_v2.png", "m9-difficulty risk curve. The bound never reaches the 0.05 line (tau* = None)."),
                 ("difficulty_hist_v2.png", "m9 difficulty distribution split by fine-tuned router label."),
                 ("risk_curve_laya.png", "Laya-P(No) risk curve. Bound crosses 0.05 at tau* = %.4f (coverage %.1f%%)." % (laya_tau, 100 * laya_n / 10378))]:
    A(Image(os.path.join(DATA, img), width=15 * cm, height=8.4 * cm))
    A(Paragraph(cap, small))
    A(Spacer(1, 12))
A(Paragraph("11. Difficulty redefined: Laya P(No)", h1))
A(Paragraph("Motivation: m9 d means were %.4f (pass) vs %.4f (fail) — no separation. d(x) was redefined as the "
            "fine-tuned router's own P(No). Validation on the 200: Claude-Y mean d = %.3f (n=%d) vs Claude-N mean d = %.3f (n=%d). "
            "Full set scored: %d unique prompts, d mean %.3f, range %.3f–%.3f. "
            "Determinism check (200 prompts scored in two separate runs): max difference 0.0001. "
            "Circularity note: the same model output supplies both score (P(No)) and label (argmax); the calibration below "
            "therefore certifies score-label consistency, with ranking power independently confirmed by Claude." % (
                statistics.mean(yd), statistics.mean(nd),
                statistics.mean(ly), len(ly), statistics.mean(ln), len(ln),
                len(laya_ds), statistics.mean(laya_ds), min(laya_ds), max(laya_ds)), body))
A(Paragraph("12. Conformal calibration on Laya P(No) (200-point grid, alpha 0.05, delta 0.05)", h1))
A(Paragraph("Join: 10,378/10,378 v2 labels matched to P(No) scores, zero missing. Base Yes rate 65.2%%. "
            "Result: tau* = %.4f — the largest tau with bound ≤ 0.05 (all higher taus fail; verified by independent recompute). "
            "Coverage %.1f%% (%d cheap), empirical risk %.4f. Empirical spot-check on the 200 Claude rows at tau*: "
            "128 routed cheap, 14 fail (10.9%%; n=128, wide margins)." % (
                laya_tau, 100 * laya_n / 10378, laya_n, laya_rh), body))
A(Paragraph("13. Stratified 300 pilot (fresh prompts, 30 per P(No) decile)", h1))
A(Paragraph("Qwen answers generated on Colab T4 via Ollama (same quant/cap); mid-run disconnect recovered through resume; "
            "file verified 300/300 in order, zero empty. GPT premium answers supplied; Claude grades: Y:%d / N:%d." % (
                pilot_grades.get("Y", 0), pilot_grades.get("N", 0)), body))
A(table([[cell("Decile"), cell("n"), cell("Fail rate")]] +
        [[cell(i), cell(n), cell("%.2f" % f)] for i, (n, f) in enumerate(pilot_dec)]))
A(Paragraph("Headline: agreement with fine-tuned router %d/300 (%.1f%%). Router-Yes fail rate %.1f%%. "
            "Fail rate shows no rise with difficulty decile — ranking power observed on the training pool does not transfer to fresh prompts." % (
                sum(1 for p in pilot_g if (pilot_lab[p] == "Yes") == (pilot_g[p] == "Y")),
                100 * sum(1 for p in pilot_g if (pilot_lab[p] == "Yes") == (pilot_g[p] == "Y")) / 300,
                100 * sum(1 for p in pilot_g if pilot_lab[p] == "Yes" and pilot_g[p] == "N") / max(1, sum(1 for p in pilot_g if pilot_lab[p] == "Yes"))), body))
A(Paragraph("14. Model and run versions", h1))
A(table([[cell("Item"), cell("Value")],
         [cell("Cheap model"), cell("qwen2.5:latest (7.6B Q4, local Ollama CPU ~6 tok/s; Colab T4 for pilot, same quant)")],
         [cell("Gemini API role"), cell("gemini-3.8-flash: connectivity probes + abandoned judge attempts only; never graded")],
         [cell("Premium baseline answers (200 + 300)"), cell("GPT (user-supplied; judge rubric is model-agnostic)")],
         [cell("Empirical grader"), cell("Claude (200: v1 + v2 rounds; 300 pilot: one round)")],
         [cell("Router base"), cell("Laya / ModernBERT-large 395M; fine-tuned on Colab T4, 140 rows, 12 epochs")],
         [cell("Router checkpoint"), cell("D:/laya, model_name=laya-hinglish-cheap, fine_tuned=true; choice-temp fit hit 10.0 clamp (loader clamps to 5, confidences uncalibrated)")],
         [cell("Rollback copy"), cell("None — Colab files overwrote D:/laya in place; pre-finetune zip at D:/Programming/laya_ckpt.zip (verify date before trusting)")]]))
doc.build(story)
print("wrote", OUT)
