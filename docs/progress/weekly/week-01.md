# Week 1 progress — Foundations fixed, real data flowing
_2026-10-15 → 2026-10-25 · generated 2026-10-24 07:09 by `backend/scripts/weekly_report.py`_

**Planned tasks done: 14/19**

| Owner | Done | Commits this week |
|---|---|---|
| All | 1/1 | 0 |
| Sahil | 0/2 | 0 |
| Shivam | 0/3 | 0 |
| Tushar | 13/13 | 114 |

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
- [Tushar] Compression benchmark on 8,000 prompts (GSM8K, ARC, MMLU, Hinglish-Instruct; 3 tokenizers; numbers/negation/question-word/option checks) → `docs/research/COMPRESSION_STUDY.md`
- [Tushar] New lossless compressor `tokopt` (tokenizer-aware spelling normalisation for romanized Hindi)
- [Tushar] Fixed CRF task-altering edits found by the benchmark (de-duplicated lists, broken intervals, edited quotes) + regression tests
- [Tushar] One-command daily runner `run_daily.py` (translate → answer → grade → certify → report)

## Still open
- [Shivam] Build all 1,319 items and translate them (`build_items.py`, `translate.py --shard i/3`)
- [Shivam] Annotation guide + verify first 300 Hinglish items in `verify_sheet.csv` (50 double-checked for agreement)
- [Sahil] Start daily answer collection (`collect.py`), target ≥ 600 graded pairs by Sunday
- [Sahil] First real (preliminary) `certify.py` run once ≥ 300 cert items have both answers
- [Shivam] Answer-level compression check (`compress_answers.py`, runs daily): first report with McNemar tests once ≥ 300 changed prompts are answered

## Evidence

**Commits**
- Tushar:
  - 6da0736 Record second overnight check and document-mode comparison
  - 1133d58 Add opt-in document compression and budget-matched evaluation
  - a285c91 Record first overnight check and broader two-GPU compressor run
  - 6eeb1f7 Use disjoint GPU workers and validate merged compressor coverage
  - 6d6688c Record overnight compressor continuation and active paired pilot
  - 98adb21 Refine measured compression rates and preserve soft line wraps
  - c6b3381 Run extracted Kaggle pilot sources from writable storage
  - b8e0e30 Fix benchmark resume and grading and validate Kaggle pilot sources
  - 76317e7 Add preservation-checked budgeted compressor and bounded Kaggle pilot
  - c8ba691 Log router CPU results and running Kaggle validation
  - d1c1201 Fix router calibration binding and add train-only CPU/Kaggle validation
  - 9c2a0f4 AGENT_LOG: -cc waiter restarted
  - 9a4377d Round 3 staged runner (max 4 processes, low priority)
  - c38a1e1 AGENT_LOG: -cc round running on teammate Kaggle
  - fb066de AGENT_LOG: Conformal Cascade run blocked by Kaggle quota
  - 9025d36 Conformal Cascade baseline: 16-sample Kaggle round (kaggle-cc) and analysis script
  - e3f86c6 Frontend: simplify to compressor, router and cost pages
  - 5bf021e AGENT_LOG: round 3 restarted
  - fd73ac4 baselines2: wire --methods/--out into the CLI (round 3 had not run)
  - 74b8666 Router baselines on paired GSM8K items (removes ARC task confound); paper uses paired set as main analysis
  - 2bf949d Router vs literature baselines (CRC, uncalibrated, marginal LTT, kNN, mix shift) and router paper draft
  - cb72196 Router v2 scorer comparison (not selected: too few positives); router agent rules and model-pinned subagents
  - 21ed94c BM25-relevance hybrid and graded compressors; round 3 orchestrator; LongLLMLingua dropped (not reproducible)
  - bb8217b KEY_RESULTS Q: stronger baselines narrow the compressor claim
  - 29e0010 Grade stronger compressor baselines
  - ae61918 Stronger baselines: LLMLingua-2 large, LongLLMLingua, BM25 sentence retrieval
  - c1158ab AGENT_LOG: overnight checks done
  - 00a8c29 KEY_RESULTS P: out-of-domain frozen-hybrid results (pre-registered criterion met)
  - 9604dfb KEY_RESULTS O3: Hinglish lexical-graded variant; budget-faithful selection
  - 6c26e8a Out-of-domain test of frozen hybrid settings (MuSiQue, 2Wiki, SQuAD v2, MeetingBank-QA); pre-registered
  - 3f60267 KEY_RESULTS O2: HotpotQA-500 hybrid vs LLMLingua-2 (+5 to +12 F1, p<=0.005)
  - 83c955d AGENT_LOG: fixed duplicate runner; graded2 queued
  - 033b7fa AGENT_LOG: teammate round re-pushed
  - 30e89dc AGENT_LOG: teammate kernel had no internet
  - c1eb3b3 Hinglish-focused graded variants (spread, lexical-weighted relevance); overnight orchestrator
  - 926c37d AGENT_LOG: teammate HotpotQA round running
  - db66dfc HotpotQA-500 Kaggle round on teammate account (launcher)
  - 2203e0e AGENT_LOG: quota exhausted; status
  - 54af6ba KEY_RESULTS O: coarse-to-fine hybrid results (HotpotQA, Belebele EN/HI)
  - 896244f hotpot: generic hybrid/graded methods, tighter budgets (0.25/0.2), Kaggle export
  - 4bf3f9d AGENT_LOG: hybrid round 1 results, grid+graded queued
  - 53f55c8 Relevance-graded coarse-to-fine variant (per-sentence keep rates, bisection to budget)
  - 20ce9c5 Hybrid split grid + dev/test split selection; 500-item human verification sheet for code-mixed Belebele
  - 35ea6ad AGENT_LOG: hybrid runs queued
  - 3152581 Language-aware coarse-to-fine hybrid compressor (sentence selection + guarded in-sentence deletion, budget split), Belebele + HotpotQA builders
  - bade3da KEY_RESULTS N: HotpotQA pilot (sentence selection vs deletion on long contexts); overnight log
  - 992ac6e AGENT_LOG: 7B round 2
  - c01137b KEY_RESULTS M2: correct the re-grade note
  - dcb6b3d KEY_RESULTS M2: correct the re-grade note
  - 70984ba KEY_RESULTS M2: Qwen2.5-7B Belebele results; grader accepts bare-letter replies
  - 7cea3df Second answering model: Qwen2.5-7B on Kaggle (KAGGLE_MODEL/TAG/ONE_WORKER), Belebele graders read tagged folders
  - 2f7c376 KEY_RESULTS M: same-language rewriting results
  - 29762c0 KEY_RESULTS M: code-mixed Belebele, deletion vs sentence selection, Hinglish vs English
  - ded434b hotpot: sentence-selection methods; overnight log
  - 0ff9553 kaggle_run: honour KAGGLE_CONFIG_DIR (teammate account in a separate folder)
  - 60be62d kaggle_run: KAGGLE_GPU env var selects the accelerator (P100 when T4 queues are long)
  - 6cd16f0 AGENT_LOG: Belebele extra prompts queued
  - 3301d14 Belebele: sentence selection (CPC/PC-SubMax style, hybrid embedding+lexical relevance) and same-language abstractive rewriting vs LLMLingua, Hinglish and English
  - 75deca7 translate_back eval: fix tokenizer key; log local MT results
  - c424911 Code-mixed Belebele test: Hinglish vs English vs Kaggle-translated vs compressed
  - d0cbfe9 PAPER_PLAN: translate-don't-delete framing, related-work gap, remaining experiments
  - ec976ea KEY_RESULTS L: slot retention on Hinglish-TOP; tokenizer tax on human Hinglish
  - 25ee622 translate_back: delimited few-shot prompt (1.5B model answered instead of translating); recon eval fix
  - 7b0c5f1 KEY_RESULTS G-K: meaning signals, tokopt withdrawal, certified gating, translate-then-send bound, pragmatic invariance
  - bc9b00b Meaning-preservation study: signal validation, certified gating, tokopt-safe fix (old tokopt withdrawn), Hinglish-TOP slots, reconstruction signal, label invariance, translate-then-send
  - b125c03 AGENT_LOG: daily job on gemma step; hotpot restarted
  - 117dc72 AGENT_LOG: overnight checks 1-8
  - b98f148 hotpot.py: fix chat-template call for new transformers; answer 200 items
  - f95eb97 HotpotQA long-context compression test (question-aware guard, Selective Context)
  - 08cdfff KEY_RESULTS E/F: output length and joint certified compress-or-route
  - bb5cf58 Output-length analysis and joint certified compress-or-route (LTT over method x threshold)
  - bb1d046 KEY_RESULTS D: CondaQA answer-level negation results (Qwen-3B)
  - 119f893 run_daily: resume CondaQA answering on Gemma-4-26B each day
  - dbe77a2 CondaQA API pilot: --ids/--answers options, stop on daily quota
  - 8195d1b api_answer.py: resumable Gemini/OpenAI answering of the shared prompt file (records served model version)
  - b744a09 AGENT_LOG: CondaQA offline results
  - 56d285d CondaQA negation stress test for prompt compression (+ affix-negation guard)
  - 3743a3d Equal-budget and negated-question analysis (KEY_RESULTS A2)
  - e269de6 Answer-level compression results and pair-2 certified routing (KEY_RESULTS.md)
  - 72cccf5 Negation-safe lexical compression (2609.13154 replication + Hinglish), two-stage combos, similarity scorer
  - 26d2044 Adaptive guarded compression: per-prompt rate under a similarity floor (finding 10)
  - b6d24c0 kaggle_run: --until-complete loops wait/download/re-push until all prompts are answered
  - 31e4bd4 Kaggle notebook: one worker per GPU (2x), 256-token cap, periodic merge so timeouts keep answers
  - bccbe42 kaggle_run: network-tolerant polling and downloads; --wait-only
  - 731acba Agent log: Kaggle run 1 root cause, run 2 started
  - dc61d24 Kaggle notebook: transformers-only, priority order, error-tolerant batches; runner carries over previous answers
  - d9866ea kaggle_run: UTF-8 for CLI on Windows; --download-only to fetch log/output of last run
  - 1906111 kaggle_run: create dataset first, version only if it exists (fixes 403)
  - 5d77d9b Kaggle runner: support new access_token credentials
  - 62751d4 Automated Kaggle GPU run (dataset, notebook push, wait, download, analysis) + waiter
  - 521a582 Rate-sweep results; Kaggle T4 local-answer pipeline (prepare, notebook, import)
  - 5f124a8 LLMLingua-2: cache forward pass across keep-rates; set torch threads per shard
  - e7d7161 summarize: drop duplicate (prompt, method) rows from overlapping runs
  - 04407dd Guarded results, embedding-blindness finding, digit-word guard fix, queued guarded2 rerun
  - b3d0a73 Rate sweep runner; answer check compares plain vs guarded LLMLingua-2
  - c92b6a7 Agent log: guarded compression run
  - c7d4bb1 Guarded LLMLingua-2 compressor, resumable shards, semantic-similarity check, detached runner
  - c65eb1a LLMLingua-2 baseline results, sharded compress_eval, sim_tax sweep, strict AGENTS.md + handoff log
  - 89e8a7c AGENTS.md: token discipline and model choice rules
  - e94c401 Compression study on 8,000 prompts; tokopt compressor; fix CRF task-altering edits
  - dbf11ae Windows Task Scheduler wrapper for the daily benchmark run
  - 4487a69 Week-1 report refresh
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
  "items": 3491,
  "splits": {
    "cert": 2049,
    "scorer_train": 1085,
    "pilot": 357
  },
  "hinglish_variants": 3420,
  "hinglish_auto_checks_passed": 2348,
  "answers_ok": {
    "cheap/english": 501,
    "cheap/hinglish": 450,
    "premium/english": 2374,
    "premium/hinglish": 2337
  },
  "answer_errors": 0,
  "graded_pairs": 936,
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
    }
  },
  "summary": {
    "english": {
      "n": 487,
      "cheap_accuracy": 0.9405,
      "premium_accuracy": 0.9671,
      "u_rate_cheap_wrong_premium_right": 0.0349,
      "mean_prompt_tokens": 168.6,
      "cost_ratio_cheap_over_premium": 0.4
    },
    "hinglish": {
      "n": 449,
      "cheap_accuracy": 0.9287,
      "premium_accuracy": 0.9243,
      "u_rate_cheap_wrong_premium_right": 0.0245,
      "mean_prompt_tokens": 181.8,
      "cost_ratio_cheap_over_premium": 0.4241
    },
    "tokenizer_tax_hinglish_over_english": 1.0733
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
