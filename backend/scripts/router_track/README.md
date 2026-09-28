# router_track — conformal routing pipeline (run00–run07)

Calibrated cheap-vs-premium routing track: audit → queries → label → grade →
supervised → bandit → **conformal threshold** → eval. See `run06_conformal.py`
(threshold freeze) and `run07_eval.py` (single held-out evaluation).

| Step | Script | Does |
|---|---|---|
| 00 | `run00_audit.py` | dataset audit |
| 01 | `run01_queries.py` | query batching |
| 02 | `run02_label.py` / `run02b_refill.py` | labeling + refill |
| 03 | `run03_grade.py` | grading |
| 04 | `run04_supervised.py` | supervised policy |
| 05 | `run05_bandit.py` | bandit policy |
| 06 | `run06_conformal.py` | conformal threshold freeze (`thresholds.json`, `DECISION_04.json`) |
| 07 | `run07_eval.py` | held-out evaluation (run once, no retrain after) |

## For presentations (PPT agent) — routing part

The routing study's **results, figures and numbers** live in one source of truth:

👉 `backend/experiments/cascade_routing/cascade_full_report.pdf`

Lift for slides ONLY from that PDF (never from chat):
- Fig 4 (agreement 55% → 90.5% → 49.3%) — the iteration story
- Fig 5 (risk curve + tau* = 0.5528) — the certificate
- Fig 6 (flat pilot deciles) — the generalization finding
- Versions table — model/config provenance
- Section 10 (validity notes) — the limitations slide

Numbers in the PDF are computed live from data files at generation time
(`scripts/make_full_report.py`). If a number isn't in the PDF, don't put it on a slide.
