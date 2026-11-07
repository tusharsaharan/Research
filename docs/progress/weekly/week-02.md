# Week 2 progress — First real results
_2026-10-26 → 2026-11-01 · generated 2026-10-28 07:06 by `backend/scripts/weekly_report.py`_

**Planned tasks done: 1/6**

| Owner | Done | Commits this week |
|---|---|---|
| Sahil | 0/2 | 0 |
| Shivam | 0/1 | 0 |
| Tushar | 1/3 | 5 |

## Done
- [Tushar] Second gold-answer sources through the same pipeline: ARC-Challenge (1,172) + MMLU sample (1,000), option-label checks and letter grading

## Still open
- [Sahil] Pair-1 (gpt-oss-20b → 120b) answers complete for all verified items, English + Hinglish
- [Shivam] All Hinglish items human-verified; failures repaired or dropped (logged)
- [Tushar] Train the router scorer on the `scorer_train` split; per-language AUROC
- [Tushar] Certify per-language thresholds on the `cert` split; marginal vs per-language risk over 1,000 re-splits
- [Sahil] Pair 2 ready (local ~4B model on Kaggle + a second provider); 100-item smoke run

## Evidence

**Commits**
- Tushar:
  - 4d00b1d Repair evidence segmentation and refill measured token budgets
  - 1f44cb8 Record completed v12 compressor results and failure analysis
  - 6943196 Record tested and queued Kaggle compressor pilot v12
  - 0f00d18 Record Hinglish evidence validation and prepared paired pilot
  - 28d89ca Add opt-in Hinglish evidence coverage compressor

**Backend tests:** skipped

**Benchmark pipeline**
```json
{
  "items": 3491,
  "splits": {
    "cert": 2049,
    "scorer_train": 1085,
    "pilot": 357
  },
  "hinglish_variants": 3491,
  "hinglish_auto_checks_passed": 2388,
  "answers_ok": {
    "cheap/english": 549,
    "cheap/hinglish": 498,
    "premium/english": 3491,
    "premium/hinglish": 2389
  },
  "answer_errors": 1,
  "graded_pairs": 1046,
  "tokens_by_day": {
    "2026-10-15": {
      "openai/gpt-oss-20b": 200123,
      "openai/gpt-oss-120b": 190124
    },
    "2026-10-16": {
      "openai/gpt-oss-20b": 108413
    },
    "2026-10-18": {
      "openai/gpt-oss-20b": 193144,
      "openai/gpt-oss-120b": 190083
    },
    "2026-10-19": {
      "openai/gpt-oss-20b": 195140,
      "openai/gpt-oss-120b": 190108
    },
    "2026-10-20": {
      "openai/gpt-oss-20b": 130209,
      "openai/gpt-oss-120b": 7365
    },
    "2026-10-21": {
      "openai/gpt-oss-20b": 195024,
      "openai/gpt-oss-120b": 190090
    },
    "2026-10-22": {
      "openai/gpt-oss-20b": 195167,
      "openai/gpt-oss-120b": 190078
    },
    "2026-10-23": {
      "openai/gpt-oss-20b": 195013,
      "openai/gpt-oss-120b": 190444
    },
    "2026-10-24": {
      "openai/gpt-oss-20b": 195007,
      "openai/gpt-oss-120b": 190069
    },
    "2026-10-25": {
      "openai/gpt-oss-20b": 4215
    },
    "2026-10-26": {
      "openai/gpt-oss-20b": 62888,
      "openai/gpt-oss-120b": 190061
    },
    "2026-10-28": {
      "openai/gpt-oss-120b": 142020,
      "openai/gpt-oss-20b": 195212
    }
  },
  "summary": {
    "english": {
      "n": 549,
      "cheap_accuracy": 0.9417,
      "premium_accuracy": 0.9672,
      "u_rate_cheap_wrong_premium_right": 0.0328,
      "mean_prompt_tokens": 170.3,
      "cost_ratio_cheap_over_premium": 0.4012
    },
    "hinglish": {
      "n": 497,
      "cheap_accuracy": 0.9256,
      "premium_accuracy": 0.9256,
      "u_rate_cheap_wrong_premium_right": 0.0282,
      "mean_prompt_tokens": 183.3,
      "cost_ratio_cheap_over_premium": 0.4284
    },
    "tokenizer_tax_hinglish_over_english": 1.0722
  }
}
```

**This week's demo:** first real result — does a single (marginal) threshold over-risk Hinglish users?

## Next week — End-to-end prototype on real thresholds
- [Tushar] Gateway loads the trained scorer + per-language thresholds (`m4_router/certified.py`); `/healthz` shows router source and thresholds
- [Tushar] Results page `/research` (+ `/v1/research/summary`): per-dataset accuracy, certification table, simulation, tokenizer tax
- [Sahil] Pair-2 answers collected and graded
- [Shivam] Open-ended Hinglish set: 1,000 prompts, both answers, two human labels each (labelling starts)
- [Tushar] Stress tests: language-mix shift and labels-vs-savings ("certification tax") curve
