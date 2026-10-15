# Week 1 progress — Foundations fixed, real data flowing
_2026-10-15 → 2026-10-25 · generated 2026-10-15 19:29 by `backend/scripts/weekly_report.py`_

**Planned tasks done: 6/12**

| Owner | Done | Commits this week |
|---|---|---|
| All | 0/1 | 0 |
| Sahil | 0/2 | 0 |
| Shivam | 0/2 | 0 |
| Tushar | 6/7 | 0 |

## Done
- [Tushar] Tests always run offline (forced dry-run); no more quota burn or env-dependent failures
- [Tushar] Remove hardcoded Telegram token from `run_telegram_bot.py` (token lives only in `backend/.env`)
- [Tushar] Correct cost model: gpt-oss-20b/120b prices, input and output priced separately (was GPT-4o rates → savings shown ~20× too high)
- [Tushar] Router picks a per-language threshold (english / hinglish / mixed_script)
- [Tushar] Learned scorer no longer zero-pads embeddings at serve time
- [Tushar] Benchmark pipeline: items → Hinglish variants → cheap+premium answers → gold grading (5-item live smoke run passes)

## Still open
- [Tushar] Merge calibration fixes from the parallel session (`from_pairs`, real bounds in sweeps, post-hoc α correction, valid CRC, validity simulation)
- [All] Commit the working tree so the branch runs from a clean checkout
- [Shivam] Build all 1,319 items and translate them (`build_items.py`, `translate.py --shard i/3`)
- [Shivam] Annotation guide + verify first 300 Hinglish items in `verify_sheet.csv` (50 double-checked for agreement)
- [Sahil] Start daily answer collection (`collect.py`), target ≥ 600 graded pairs by Sunday
- [Sahil] Pre-registration file `docs/research/PREREG.md`: groups, loss, α/δ grids, hypotheses, splits

## Evidence

**Commits**
- no commits in this date range (uncommitted work does not count as evidence)

**Backend tests:** 1 failed, 307 passed, 6 skipped in 98.04s (0:01:38)
  - FAILED tests/test_phase2.py::test_fixed_sequence_dominates_hoeffding - Assert...

**Benchmark pipeline**
```json
{
  "items": 1319,
  "splits": {
    "cert": 769,
    "scorer_train": 412,
    "pilot": 138
  },
  "hinglish_variants": 103,
  "hinglish_auto_checks_passed": 78,
  "answers_ok": {
    "cheap/english": 5,
    "cheap/hinglish": 4,
    "premium/english": 5,
    "premium/hinglish": 4
  },
  "answer_errors": 0,
  "graded_pairs": 8,
  "tokens_by_day": {
    "2026-10-15": {
      "openai/gpt-oss-20b": 31900,
      "openai/gpt-oss-120b": 2400
    }
  },
  "summary": {
    "english": {
      "n": 5,
      "cheap_accuracy": 1.0,
      "premium_accuracy": 1.0,
      "u_rate_cheap_wrong_premium_right": 0.0,
      "mean_prompt_tokens": 157.8,
      "cost_ratio_cheap_over_premium": 0.3479
    },
    "hinglish": {
      "n": 3,
      "cheap_accuracy": 0.6667,
      "premium_accuracy": 1.0,
      "u_rate_cheap_wrong_premium_right": 0.3333,
      "mean_prompt_tokens": 167.0,
      "cost_ratio_cheap_over_premium": 0.4577
    },
    "tokenizer_tax_hinglish_over_english": 1.0865
  }
}
```

**This week's demo:** tests green · live pipeline · first per-language accuracy table (`backend/data/bench/summary.json`).

## Next week — First real results
- [Sahil] Pair-1 (gpt-oss-20b → 120b) answers complete for all verified items, English + Hinglish
- [Shivam] All Hinglish items human-verified; failures repaired or dropped (logged)
- [Shivam] Second gold-answer source (multiple-choice) through the same pipeline
- [Tushar] Train the router scorer on the `scorer_train` split; per-language AUROC
- [Tushar] Certify per-language thresholds on the `cert` split; marginal vs per-language risk over 1,000 re-splits
- [Sahil] Pair 2 ready (local ~4B model on Kaggle + a second provider); 100-item smoke run
