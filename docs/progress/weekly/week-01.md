# Week 1 progress — Foundations fixed, real data flowing
_2026-10-15 → 2026-10-25 · generated 2026-10-15 19:57 by `backend/scripts/weekly_report.py`_

**Planned tasks done: 11/15**

| Owner | Done | Commits this week |
|---|---|---|
| All | 1/1 | 0 |
| Sahil | 0/2 | 0 |
| Shivam | 0/2 | 0 |
| Tushar | 10/10 | 12 |

## Done
- [Tushar] Tests always run offline (forced dry-run); no more quota burn or env-dependent failures
- [Tushar] Remove hardcoded Telegram token from `run_telegram_bot.py` (token lives only in `backend/.env`)
- [Tushar] Correct cost model: gpt-oss-20b/120b prices, input and output priced separately (was GPT-4o rates → savings shown ~20× too high)
- [Tushar] Router picks a per-language threshold (english / hinglish / mixed_script)
- [Tushar] Learned scorer no longer zero-pads embeddings at serve time
- [Tushar] Benchmark pipeline: items → Hinglish variants → cheap+premium answers → gold grading (5-item live smoke run passes)
- [Tushar] Merge calibration fixes from the parallel session (`from_pairs`, real bounds in sweeps, post-hoc α correction, valid CRC, validity simulation)
- [All] Commit the working tree so the branch runs from a clean checkout
- [Tushar] Pre-registration file `docs/research/PREREG.md`: groups, loss, α/δ grids, hypotheses, splits (committed before any result)
- [Tushar] Certification experiment `certify.py` (marginal vs per-language, re-splits, mix-shift) + known-truth simulation: per-language valid (2.6% / 3.3% violations at δ=10%); one shared threshold over-risks Hinglish in 69% of trials
- [Tushar] One-command daily runner `run_daily.py` (translate → answer → grade → certify → report)

## Still open
- [Shivam] Build all 1,319 items and translate them (`build_items.py`, `translate.py --shard i/3`)
- [Shivam] Annotation guide + verify first 300 Hinglish items in `verify_sheet.csv` (50 double-checked for agreement)
- [Sahil] Start daily answer collection (`collect.py`), target ≥ 600 graded pairs by Sunday
- [Sahil] First real (preliminary) `certify.py` run once ≥ 300 cert items have both answers

## Evidence

**Commits**
- Tushar:
  - 1ebec01 Daily runner, paired-first collection order, roadmap and prereg updates
  - b87ea75 Serve the certified per-language router; add ARC/MMLU and a results page
  - 2a542d2 Roadmap: calibration fixes merged; suite fully green
  - 7d75fb2 Fix m3 risk-control validity bugs and add known-truth simulation
  - fd4fdfb Roadmap: record pre-registration and certification experiment
  - 843b7cf Add certification experiment and known-truth validity simulation
  - 79fc95d Pre-register study R1: marginal vs per-language certified routing
  - 49ea5e1 weekly_report: count commits from midnight of the week's first day
  - 24cf4d3 weekly_report: credit commits to roadmap owners by first name
  - d784241 Add 4-week prototype roadmap and week-1 progress report
  - 9397435 Fix cost model, per-language routing and test isolation; add benchmark pipeline
  - d5b35cd Wire CRF compressor into the gateway and fix rewrite prompts

**Backend tests:** skipped

**Benchmark pipeline**
```json
{
  "items": 2491,
  "splits": {
    "cert": 1447,
    "scorer_train": 790,
    "pilot": 254
  },
  "hinglish_variants": 381,
  "hinglish_auto_checks_passed": 285,
  "answers_ok": {
    "cheap/english": 188,
    "cheap/hinglish": 140,
    "premium/english": 179,
    "premium/hinglish": 133
  },
  "answer_errors": 0,
  "graded_pairs": 261,
  "tokens_by_day": {
    "2026-10-15": {
      "openai/gpt-oss-20b": 197110,
      "openai/gpt-oss-120b": 97181
    }
  },
  "summary": {
    "english": {
      "n": 150,
      "cheap_accuracy": 0.92,
      "premium_accuracy": 0.9533,
      "u_rate_cheap_wrong_premium_right": 0.0467,
      "mean_prompt_tokens": 162.6,
      "cost_ratio_cheap_over_premium": 0.3728
    },
    "hinglish": {
      "n": 111,
      "cheap_accuracy": 0.9369,
      "premium_accuracy": 0.9189,
      "u_rate_cheap_wrong_premium_right": 0.009,
      "mean_prompt_tokens": 174.7,
      "cost_ratio_cheap_over_premium": 0.3752
    },
    "tokenizer_tax_hinglish_over_english": 1.0742
  }
}
```

**This week's demo:** tests green · live pipeline · first per-language accuracy table (`backend/data/bench/summary.json`).

## Next week — First real results
- [Sahil] Pair-1 (gpt-oss-20b → 120b) answers complete for all verified items, English + Hinglish
- [Shivam] All Hinglish items human-verified; failures repaired or dropped (logged)
- [Tushar] Second gold-answer sources through the same pipeline: ARC-Challenge (1,172) + MMLU sample (1,000), option-label checks and letter grading
- [Tushar] Train the router scorer on the `scorer_train` split; per-language AUROC
- [Tushar] Certify per-language thresholds on the `cert` split; marginal vs per-language risk over 1,000 re-splits
- [Sahil] Pair 2 ready (local ~4B model on Kaggle + a second provider); 100-item smoke run
