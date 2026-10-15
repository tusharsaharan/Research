# Prototype roadmap — Token Optimisation (Group 1)

Goal for the demo: a **full working prototype** where a live Hinglish or English
query is assigned a language group, compressed with protected spans, scored,
routed cheap/premium with a **per-language certified threshold** fitted on real
data, answered, and logged with **real cost**, plus a dashboard and an
evaluation report built only from real, held-out data.

After the demo the same data and code become the ACL 2027 paper (January ARR
deadline): see the research plan in the conversation / `docs/research/`.

**Demo date:** assumed Fri 13 Nov 2026 (end of week 4). Change the week-4 dates
below if yours differs; `weekly_report.py` reads them from this file.

**Status of the data (the only thing that can't be rushed):** all code for weeks 1–3 is in.
What remains is model calls on the free tier: about 7,000 calls per model for GSM8K + ARC + MMLU
in two languages. One Groq key does roughly 550 premium calls a day, so about 12 days on one key
or 4–5 days if all three of you run `run_daily.py --shard i/3` with your own key.

**How to use this file**
- Tick a box (`- [x]`) the moment a task is done and commit it. Each task names
  its owner in brackets. Owners are suggestions; swap freely.
- Every Sunday run `python backend/scripts/weekly_report.py` → it writes
  `docs/progress/weekly/week-NN.md` with commits per person, ticked tasks, test
  results and benchmark progress. That file is the weekly progress evidence.
- "Demo" lines are what you show the guide that week.

## Week 1 — Foundations fixed, real data flowing (2026-10-15 → 2026-10-25)

- [x] [Tushar] Tests always run offline (forced dry-run); no more quota burn or env-dependent failures
- [x] [Tushar] Remove hardcoded Telegram token from `run_telegram_bot.py` (token lives only in `backend/.env`)
- [x] [Tushar] Correct cost model: gpt-oss-20b/120b prices, input and output priced separately (was GPT-4o rates → savings shown ~20× too high)
- [x] [Tushar] Router picks a per-language threshold (english / hinglish / mixed_script)
- [x] [Tushar] Learned scorer no longer zero-pads embeddings at serve time
- [x] [Tushar] Benchmark pipeline: items → Hinglish variants → cheap+premium answers → gold grading (5-item live smoke run passes)
- [x] [Tushar] Merge calibration fixes from the parallel session (`from_pairs`, real bounds in sweeps, post-hoc α correction, valid CRC, validity simulation)
- [x] [All] Commit the working tree so the branch runs from a clean checkout
- [ ] [Shivam] Build all 1,319 items and translate them (`build_items.py`, `translate.py --shard i/3`)
- [ ] [Shivam] Annotation guide + verify first 300 Hinglish items in `verify_sheet.csv` (50 double-checked for agreement)
- [ ] [Sahil] Start daily answer collection (`collect.py`), target ≥ 600 graded pairs by Sunday
- [x] [Tushar] Pre-registration file `docs/research/PREREG.md`: groups, loss, α/δ grids, hypotheses, splits (committed before any result)
- [x] [Tushar] Certification experiment `certify.py` (marginal vs per-language, re-splits, mix-shift) + known-truth simulation: per-language valid (2.6% / 3.3% violations at δ=10%); one shared threshold over-risks Hinglish in 69% of trials
- [ ] [Sahil] First real (preliminary) `certify.py` run once ≥ 300 cert items have both answers

- [x] [Tushar] One-command daily runner `run_daily.py` (translate → answer → grade → certify → report)

Demo: tests green · live pipeline · first per-language accuracy table (`backend/data/bench/summary.json`).

## Week 2 — First real results (2026-10-26 → 2026-11-01)

- [ ] [Sahil] Pair-1 (gpt-oss-20b → 120b) answers complete for all verified items, English + Hinglish
- [ ] [Shivam] All Hinglish items human-verified; failures repaired or dropped (logged)
- [x] [Tushar] Second gold-answer sources through the same pipeline: ARC-Challenge (1,172) + MMLU sample (1,000), option-label checks and letter grading
- [ ] [Tushar] Train the router scorer on the `scorer_train` split; per-language AUROC
- [ ] [Tushar] Certify per-language thresholds on the `cert` split; marginal vs per-language risk over 1,000 re-splits
- [ ] [Sahil] Pair 2 ready (local ~4B model on Kaggle + a second provider); 100-item smoke run

Demo: first real result — does a single (marginal) threshold over-risk Hinglish users?

## Week 3 — End-to-end prototype on real thresholds (2026-11-02 → 2026-11-08)

- [x] [Tushar] Gateway loads the trained scorer + per-language thresholds (`m4_router/certified.py`); `/healthz` shows router source and thresholds
- [x] [Tushar] Results page `/research` (+ `/v1/research/summary`): per-dataset accuracy, certification table, simulation, tokenizer tax
- [ ] [Sahil] Pair-2 answers collected and graded
- [ ] [Shivam] Open-ended Hinglish set: 1,000 prompts, both answers, two human labels each (labelling starts)
- [ ] [Tushar] Stress tests: language-mix shift and labels-vs-savings ("certification tax") curve

Demo: live query → language group → compression → certified route → answer, with real cost.

## Week 4 — Full working prototype (2026-11-09 → 2026-11-13)

- [ ] [All] Frozen test-split evaluation with bootstrap confidence intervals (replaces the synthetic `eval_report.json`)
- [ ] [Sahil] Telegram bot + web UI running on the live gateway
- [ ] [Shivam] Human-label agreement report; LLM-judge vs human, per language
- [ ] [Tushar] Results write-up and figures 1–3
- [ ] [All] Demo rehearsal; slides use real numbers only

Demo: the full prototype.
