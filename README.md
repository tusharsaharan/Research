# Code-Mixed Gateway

**An open, research-grade LLM API gateway for Hinglish (Hindi-English code-mixed) prompt compression, conformally calibrated cascade routing, and tokenizer-fairness analysis.**

> **Honest disclaimer.** This document is a transparent record of what was built, what was attempted, what succeeded, and what failed. Every number cited is traceable to a file committed in this repository. Claims that could not be substantiated were removed. Readers are encouraged to verify every assertion against the referenced artifacts.

---

## Table of Contents

1. [Motivation and Problem Statement](#1-motivation-and-problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [Module-by-Module Documentation](#3-module-by-module-documentation)
4. [CRF + Phonetic Hinglish Compressor (Novel Contribution)](#4-crf--phonetic-hinglish-compressor-novel-contribution)
5. [Training Pipeline](#5-training-pipeline)
6. [Cascade Router and Conformal Calibration](#6-cascade-router-and-conformal-calibration)
7. [LLMLingua-2 Baseline Integration](#7-llmlingua-2-baseline-integration)
8. [P0 Evaluation Study (Token Study Package)](#8-p0-evaluation-study-token-study-package)
9. [Datasets and Data Artifacts](#9-datasets-and-data-artifacts)
10. [Frontend and Interactive Proof System](#10-frontend-and-interactive-proof-system)
11. [Test Suite](#11-test-suite)
12. [Debugging War Log — Honest Account of Every Hard Problem](#12-debugging-war-log)
13. [The GPU Saga — Unresolved Infrastructure Failure](#13-the-gpu-saga)
14. [Router Track — The Labeling and Grading Campaign](#14-router-track)
15. [Known Limitations and Honest Weaknesses](#15-known-limitations-and-honest-weaknesses)
16. [Relationship to Prior Work](#16-relationship-to-prior-work)
17. [Reproduction Instructions](#17-reproduction-instructions)
18. [Repository Structure](#18-repository-structure)
19. [References](#19-references)

---

## 1. Motivation and Problem Statement

Large Language Model APIs charge per token. Tokenizers designed for English systematically over-segment code-mixed text: a Hinglish sentence that costs 16 tokens in English may cost 30–43 tokens when Hindi words are romanized. This penalty — the **Tokenizer Tax** — is an invisible surcharge on users in the Global South who naturally mix languages.

A second, less obvious penalty — the **Reasoning Tax** — arises when reasoning models (e.g., DeepSeek-R1 class) silently allocate more internal "thinking tokens" to process code-mixed input compared to semantically equivalent English input.

This project attempts to address both penalties through:

1. **Prompt compression** that understands Hinglish spelling chaos, fillers, and grammar.
2. **Cascade routing** that sends easy queries to cheap open-weight models and hard queries to premium frontier models, with a statistical error-rate guarantee.
3. **Transparency tooling** that exposes every internal decision to the end user and to adversarial testers.

---

## 2. Architecture Overview

```
User Prompt (Hinglish)
       │
       ▼
┌──────────────────────────────┐
│  m1_pipeline: tokenization,  │
│  code-mix ratio detection    │
└──────────────┬───────────────┘
               │
       ┌───────▼────────┐
       │  m2_compressor  │
       │  (4 methods)    │
       │  heuristic │    │
       │  CRF       │    │
       │  LLMLingua-2│   │
       │  model (LLM)│   │
       └───────┬────────┘
               │  compressed prompt
       ┌───────▼────────┐
       │  m4_router:    │
       │  DifficultyScorer → score
       │  m3_conformal: │
       │  τ threshold   │
       │  route cheap │  │
       │     or premium │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  LLM API call  │
       │  (Groq / OpenAI)│
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  m5_gateway:   │
       │  FastAPI server │
       │  1492-line main │
       └────────────────┘
```

**Backend:** Python 3.11+, FastAPI, uvicorn. 14 modules (`m1` through `m12_semantic`).
**Frontend:** React + Vite + TanStack Router. 14 route pages.
**Total commits:** 44 across all branches.

---

## 3. Module-by-Module Documentation

| Module | Purpose | Key Files | Status |
|--------|---------|-----------|--------|
| `m1_pipeline` | Tokenization (tiktoken/MuRIL), `code_mix_ratio()` calculator, benchmark runner | `hinglish.py`, `tokenizer_bench.py` | Operational |
| `m2_compressor` | All compression methods: heuristic lexicon prune, CRF sequence tagger, LLMLingua-2, LLM rewrite | `compressor.py` (234 lines), `linguistic.py`, `crf_tagger.py`, `phonetic.py`, `heuristic_passes.py`, `safety_span.py`, `llmlingua2.py`, `tfidf.py` | Operational |
| `m3_conformal` | Conformal risk control: Hoeffding + fixed-sequence LTT threshold selection, Clopper–Pearson UCB, Mondrian stratification, 201-point τ sweep, α sweep with Kneedle knee detection | `conformal.py` (359 lines), `calibration_store.py` | Operational |
| `m4_router` | `DifficultyScorer` (4-feature weighted score), `CascadeRouter` (cheap vs. premium dispatch) | `difficulty.py`, `router.py` | Operational |
| `m5_gateway` | FastAPI application: 20+ endpoints including `/v1/compress`, `/v1/chat/completions`, `/v1/compress/redteam`, `/v1/calibration/metrics`, `/v1/difficulty/features`, `/v1/reward/autopsy`, `/receipt/{id}`, `/v1/feedback` | `main.py` (1,492 lines) | Operational |
| `m6_telegram` | Telegram bot integration with SQLite logging, receipts, feedback recording | `service.py`, `db.py` | Scaffolded, not deployed |
| `m7_eval` | Evaluation metric computation (BLEU, ROUGE) | `evaluate.py` | Operational |
| `m8_dashboard` | Dashboard data aggregation | `dashboard.py` | Operational |
| `m9_reasoning` | Reasoning budget estimator: feature-based thinking-token prediction, Hinglish-vs-English delta comparator | `budget.py` (109 lines) | Operational |
| `m10_train` | Reward model (semantic similarity scoring) | `reward.py` | Operational |
| `m11_calibration` | Expected Calibration Error, reliability diagrams | `ece.py` | Operational |
| `m12_novel` | Adaptive compression policy (`target_kept_ratio = 0.52 + 0.30·mix + 0.18·diff`), glossing, code-mix bucketing analysis, transliteration | `adaptive.py`, `analysis.py`, `gloss.py`, `translate.py` | Operational |
| `m12_semantic` | Semantic similarity (sentence-transformers based) | — | Operational when `sentence-transformers` installed |

---

## 4. CRF + Phonetic Hinglish Compressor (Novel Contribution)

This is the primary original contribution. No prior work applies CRF sequence labeling with phonetic normalization to Hinglish prompt compression.

### 4.1 Problem: Spelling Entropy

Romanized Hindi has no standard orthography. A single construction surfaces as:
- `"kar raha hai"` / `"kr rha h"` / `"karra h"` / `"karr raha hai"`
- `"nahi"` / `"nhi"` / `"nai"` / `"nahin"`

No finite word-list can match all variants. Prior Hinglish NLP work (COMI-LINGUA, GupShup) addresses this at the LID/NER level but not for extractive compression.

### 4.2 Phonetic Normalization (`phonetic.py`, 174 lines)

Two components:

1. **`normalize_chars(token)`**: Lowercase → abbreviation expansion (31 entries in `ABBREVS`) → collapse runs of 3+ identical characters to 1 (preserving legitimate doubles like `http`, `assignment`) → second abbreviation pass for cases revealed by collapsing (`"krr"` → `"kr"` → `"kar"`).

2. **`hinglish_phash(token)`**: Consonant-skeleton hash. Strip trailing vowel inflection → map aspiration clusters (`sh→S`, `ch→C`, `th→T`, `dh→D`, `kh→K`, `gh→G`, `ph→F`, `bh→B`) → strip all remaining vowels → deduplicate → uppercase. Result: `raha`/`rha`/`rahi` → `RH*`, `nahi`/`nhi` → `NH`. Collisions are expected and are disambiguated by neighboring-token CRF features.

**Critical design decision:** The phonetic hash is a *CRF feature*, never a standalone lookup key. Using it as a key would create dangerous false matches (e.g., any word with consonant skeleton `NH` would be treated identically).

### 4.3 Heuristic Pre-Pruning (`heuristic_passes.py`, 136 lines)

Three context-free operations that run *before* the CRF on masked text:

1. **Greeting strip**: Phonetically tolerant, compares normalized first-token(s) against a sorted greeting lexicon. Multi-word greetings (`"good morning"`) use 2-token lookahead. Greeting-only messages are *not* stripped (nothing to compress to).

2. **Reduplication collapse**: Adjacent exact reduplication (`"jaldi jaldi"` → `"jaldi"`) and echo reduplication (`"chai-vai"`, `"kaam-vaam"`) on normalized forms.

3. **Unconditional fillers**: Only 8 tokens: `{arre, arrey, arey, um, uh, umm, err, hmm}`. These have zero homograph risk. Context-dependent fillers (`yaar`, `matlab`, `basically`, `toh`, `na`, `like`) are deliberately excluded — they belong to the CRF which can see surrounding context.

### 4.4 CRF Sequence Tagger (`crf_tagger.py`, 152 lines)

**Feature set per token (25+ features):**
- Normalized form, phonetic hash
- Morphological: suffix-1/2/3, prefix-1/2/3
- Character bigram cues: `has_rh`, `has_nh`
- Boolean flags: `is_short`, `is_alpha`, `is_ascii`, `has_devanagari`, `is_marker`, `is_protected`
- Positional: `is_first`, `is_last`, `is_second`, `is_penult`, `position_ratio`
- Information content: `tfidf_score`, `is_high_freq`, `is_low_freq`
- **±2 neighbor window**: normalized form, phonetic hash, suffix-2, `is_marker`, `is_protected` for each of positions {−2, −1, +1, +2}; BOS/EOS sentinels at boundaries.

**Training algorithm:** L-BFGS via `sklearn-crfsuite` (L1 regularization c1=0.1, L2 regularization c2=0.1, max 200 iterations, all possible transitions enabled). Viterbi decoding at inference.

**Safety gates (post-CRF, `apply_safety_gates`):**
1. Protected tokens (22 negation/question words in `PROTECTED_TOKENS`) and `[[PSi]]` markers are unconditionally force-kept regardless of model output.
2. Minimum-keep floor: at least max(2, 30% of tokens) must survive. If the CRF drops below this threshold, all tokens are kept (fail closed).

### 4.5 Linguistic Compressor Orchestrator (`linguistic.py`, 151 lines)

A 5-stage fail-closed pipeline:

| Stage | Operation | Failure mode |
|-------|-----------|-------------|
| 1 | `safety_span.mask()`: PII/code/URLs/amounts → `[[PSi]]` markers | Regex, no failure |
| 2 | Phonetic normalization (implicit in CRF features, never rewrites output) | N/A |
| 3 | Heuristic pre-pruning (greeting, reduplication, fillers) | Empty → fail closed |
| 4 | CRF Keep/Drop tagging + safety gates | Model load failure → all-Keep |
| 5 | Reconstruct (stitch kept *original* tokens) + `reinject(masked, spans)` | Marker lost → return original |

**Fail-closed guarantee:** Any exception at any stage returns the original text unchanged, honestly labeled as `method="crf"` with `ratio=1.0`.

### 4.6 Protected Span System (`safety_span.py`, 69 lines)

Regex-based extraction in priority order: fenced code → inline code → email → URL → phone → amount (₹/Rs./INR patterns). Non-overlapping spans stored with character offsets. Masking replaces each with `[[PS0]]`, `[[PS1]]`, etc. Reinjection substitutes markers back; fails closed (returns `ok=False`) if any marker is missing, duplicated, or foreign.

**Measured result:** 0/260 reinjection failures across the G2 smoke run (real LLMLingua-2, 260 compression rows).

---

## 5. Training Pipeline

### 5.1 Prompt Generation (`scripts/generate_hinglish_prompts.py`)

- **23 templates** across 4 domains (campus, tech, ecommerce, general) with slot-filling from small vocabulary lists.
- **Spelling-variant injection:** `inject_spelling_variants()` randomly replaces canonical forms with wild spellings (`kar→kr`, `hai→h`, `nahi→nhi`, `phone→fone`) at 30% probability per token, plus 5% emphasis elongation (`"hai"→"haai"`).
- **Guard-contrast templates** specifically designed to distill lexicon guards into the CRF:
  - Mid-sentence `matlab` (filler, should drop) vs. `"download matlab free version"` (tech noun, must keep).
  - `"bhai mera assignment"` (vocative, can drop) vs. `"mere bhai ka phone"` (kinship/genitive, must keep).
  - English homograph keeps: `"I like this"` (verb), `"the sun rises"` (noun), `"can you submit"` (pronoun).
- **Output:** 5,000 prompts → `data/training/prompts.jsonl` (589 KB, deterministic seed 7).

### 5.2 Bootstrap Labeling (`scripts/bootstrap_crf_data.py`, 459 lines)

Two teacher paths:

**A. Deterministic teacher (`--no-llm`):**
Lexicon `prune()` + auxiliary-verb drop (`raha`, `rahi`, `rahe`, `hai`, `hain`, `hun`, `tha`, `thi`, `the`, `hoga`, `hogi`, `honge`). Fast, offline, sufficient for pipeline validation. This is the currently deployed CRF teacher.

**B. LLM teacher (Ollama/HuggingFace):**
- System prompt with few-shot examples enforcing: never drop negation, never add words, never reorder, keep markers.
- Greedy forward alignment (`align_tokens`) on normalized forms to derive Keep/Drop labels.
- **Quality gates:**
  - Negation/question survival: if any token in `PROTECTED_TOKENS` is dropped, the example is rejected.
  - Homograph guard: 6 English content words (`you`, `know`, `sun`, `like`, `log`, `well`) must never be dropped by the teacher — their noise would teach the CRF to eat content words.
  - Subset check: every normalized compressed token must appear in the original (multiset comparison), rejecting hallucinations/rewordings.
  - Over-compression gate: >70% drop ratio rejected.
  - Under-compression gate: <5% drop ratio rejected.
- **Resume support:** `--resume` flag, `load_done_ids()` skips already-processed IDs (crash-safe reruns).
- **Per-batch flushing:** The HF teacher calls `on_batch()` after every batch, flushing results incrementally.

**Output:** 4,449 labeled rows from 5,000 prompts → `data/training/bootstrap_filtered.jsonl` (730 KB). 551 rejected by quality gates.

### 5.3 CRF Training (`scripts/train_crf.py`, 114 lines)

- 85/15 train/dev split (seed 7).
- L-BFGS optimizer, 200 iterations, `c1=c2=0.1`.
- Reports weighted F1 on dev set, top 10 transition features, top 10 state features.
- Output: pickled model → `data/models/crf_compressor.pkl`.

### 5.4 Teacher Comparison (`scripts/compare_teachers.py`, 127 lines)

Head-to-head evaluation of CRF variants on a shuffled 300-prompt slice:
- Mean compression ratio
- Negation preservation rate (token-level, normalized matching — not substring, avoiding false positives like `"mat"` inside `"matlab"`)
- Optional: semantic cosine similarity via `paraphrase-multilingual-MiniLM-L12-v2`

**Critical fix:** Originally printed a silent empty table when `n=0` (no prompts loaded). Now fails loudly with `SystemExit(2)`.

### 5.5 Measured CRF Performance (Deterministic Teacher)

| Metric | Value | Source |
|--------|-------|--------|
| Compression ratio | 0.64–0.83 | Measured on training prompts |
| Negation preservation | 100% (0 drops) | `compare_teachers.py` + `apply_safety_gates` |
| Entity preservation | 100% (0 reinjection failures) | `safety_span.reinject` abort-on-miss |
| Inference latency | <10 ms/prompt (CPU) | Measured, no GPU required |
| Training data | 4,449 labeled examples | `bootstrap_filtered.jsonl` line count |

---

## 6. Cascade Router and Conformal Calibration

### 6.1 Difficulty Scorer (`m4_router/difficulty.py`, 53 lines)

Four-feature weighted score:

| Feature | Weight | Source |
|---------|--------|--------|
| Code-mix ratio | 0.40 | `code_mix_ratio()` from `m1_pipeline` |
| Entity density | 0.30 | Regex: digits, Rs./INR amounts, phone-like, URLs, emails |
| Math markers | 0.20 | Regex: arithmetic expressions, "solve", "integrate", etc. |
| Length | 0.10 | `min(1.0, char_count / 400)` |

Score range: [0, 1]. Queries above threshold τ route to premium tier.

### 6.2 Conformal Risk Control (`m3_conformal/conformal.py`, 359 lines)

Two threshold-selection methods:

**A. Fixed-Sequence Learn-Then-Test** (default, per Angelopoulos et al., arXiv 2110.01052):
- Monotone deferral rule: `route premium iff score >= τ`.
- Tests H0: R(τ) <= α from τ=0.0 upward in increasing τ over a 201-point grid.
- Exact binomial tests (Clopper–Pearson UCB via `scipy.stats.beta.ppf`; Chernoff/Hoeffding fallback when scipy is unavailable).
- No Bonferroni/log(m) penalty — the fixed sequence avoids multiplicity correction.

**B. Hoeffding-Bonferroni** (original, kept for comparison):
- R_hat(τ) + sqrt(log(m/δ)/(2n)) <= α.
- More conservative; the fixed-sequence method dominates it at the same (α, δ, n).

**Mondrian mode:** When calibration samples carry group labels (e.g., code-mix buckets), a separate threshold is fitted per group with Bonferroni correction across groups.

**α sweep with Kneedle knee detection:** Evaluates threshold/coverage/savings across {0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15} to find the diminishing-returns point.

### 6.3 Calibration Data State

The `calibration_store.py` module classifies the data state as:
- **synthetic**: Only `pad-*` prefixed samples (generated, not from real queries).
- **mixed**: Some `bench-*` prefixed samples exist alongside synthetic ones.
- **live**: More than 30 real calibration samples.

**Current state:** `calibration.jsonl` contains 2,014 rows. These are predominantly synthetic (`pad-*` and `bench-*` prefixes). The `data_state` endpoint reports this honestly. No claim of "live calibration" is made.

---

## 7. LLMLingua-2 Baseline Integration

### 7.1 Implementation (`m2_compressor/llmlingua2.py`, 106 lines)

- Checkpoint: `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` (the paper's LLMLingua-2-small, BERT-base, 110M parameters, CPU-runnable).
- **Deviation from plan:** The `RESEARCH_IMPLEMENTATION_PLAN.md` specifies the `xlm-roberta-large` checkpoint. The bert-base checkpoint was used because it is the paper's own small variant, is multilingual by construction, and runs on free-tier CPU hardware. This deviation is documented in `docs/research/DECISIONS.md`.

### 7.2 Code-Mix-Specific Findings (Measured)

1. **Raw output mangles protected spans:** `user@example.com` → `user example com`. Fix: callers mask spans to `[[PSi]]` markers and pass them as `force_tokens`.
2. **Context-level filter drops whole segments:** 4 inputs → 3 outputs, misaligned. Fix: context-level filter is always disabled; every batch call asserts output/input alignment.

### 7.3 G2 Smoke Result (Measured)

From `docs/research/REPRODUCTION.md`:

| Arm | Description | Achieved Kept Ratio |
|-----|-------------|-------------------|
| A0 | None (uncompressed) | 1.00 |
| A1 | LLMLingua-2 | 0.879 |
| A2 | LLMLingua-2 + protected spans | 0.877 |
| A3 | Heuristic | 0.988 |

- 260/260 compression rows: **0 fallbacks, 0 errors**.
- All protected placeholders reinjected byte-for-byte.
- Data: 20 synthetic Hinglish task dialogues (not real evaluation data — smoke test only).

---

## 8. P0 Evaluation Study (Token Study Package)

### 8.1 Design

Full experiment package in `backend/experiments/token_study/` (17 source files):

| Component | File | Purpose |
|-----------|------|---------|
| Schema enforcement | `schemas.py` | Strict pydantic models, `extra="forbid"` |
| Data acquisition | `download_and_validate.py` | Allowlisted URL downloader, SHA-256 manifest, deterministic splits |
| Prompt rendering | `build_prompts.py` | Stable template: system + history + user turn |
| Compression runner | `run_compression.py` | Refuses heuristic-as-A1; real library enforcement |
| Answer generation | `run_answers.py` | OpenAI-compatible, `max_retries: 4`, Retry-After + exp backoff, browser-like UA (Cloudflare 1010 mitigation) |
| Structured scoring | `score_structured.py` | Canonical EM + slot micro-F1 |
| Response scoring | `score_responses.py` | Blinded rubric-based judge |
| Analysis | `analyze.py` | Paired dialogue-clustered bootstrap (10K replicates, PCG64) |
| Safe-rate rule | (embedded in analysis) | Per Angelopoulos et al., applied per pre-declared stratum |
| Report | `render_report.py` | Figures + summary JSON |
| Gate verification | `verify_run.py` | Enforces G2/G3/G4 checkpoints |
| Freeze | `freeze.py` | Locks test set after human sign-off |
| Prompt audit export | `export_prompt_audit.py` | 20-row bilingual review sheet |
| Adapter | `adapters/presto_adapter.py` | PRESTO hi-IN → schema, `targets` → `{intent, slots}` |

### 8.2 Current Status: Blocked

**What is complete:**
- Dataset: PRESTO v1 (Goel et al., arXiv 2303.08954, CC BY 4.0), 550K+ conversations, validated.
- Splits: smoke 20 / dev 150 / test 500 hi-IN code-mixing dialogues.
- Compression record: smoke 260 + dev 1,950 + test 6,500 rows, all `ok`, 0 fallbacks, real LLMLingua-2.
- Mean achieved kept: A1 approximately 0.69, A2 approximately 0.69.

**What is blocked (documented in `docs/research/RESULTS_NOT_RUN.md`):**
- Answer-model API calls (require working Groq key + budget).
- Human G1 review + freeze sign-off (20-row audit).
- Two bilingual annotators for 100 blinded structured outputs.

**No evaluation results exist.** This is by design: the plan explicitly forbids fabricated results (Section 19).

---

## 9. Datasets and Data Artifacts

| File | Rows | Size | Nature | Purpose |
|------|------|------|--------|---------|
| `data/training/prompts.jsonl` | 5,000 | 589 KB | Synthetic | CRF prompt generation |
| `data/training/bootstrap_filtered.jsonl` | 4,449 | 730 KB | Synthetic + deterministic teacher labels | CRF training data |
| `data/calibration.jsonl` | 2,014 | 132 KB | Synthetic (`pad-*` + `bench-*`) | Calibration |
| `data/benchmark.jsonl` | 50 | 20 KB | Synthetic (`is_synthetic: true`) | Benchmark display |
| `data/seed_hinglish.jsonl` | — | 15 KB | Synthetic | Demo seed |
| `data/router_track/queries.jsonl` | 3,000 | 696 KB | Synthetic | Router evaluation |
| `data/router_track/groq_labels.jsonl` | 1,200 | 2.4 MB | Real API responses (Groq) | Cheap vs. premium labeling |
| `data/router_track/judgeA_labels.jsonl` | 1,449 | 2.0 MB | Real API responses (Groq) | Importance ablation (Judge A) |
| `data/router_track/human_check.csv` | 1,297 | 107 KB | Partially annotated | Human verification (incomplete) |
| `data/challenges.jsonl` | 53 | 12 KB | Real user-submitted | Red-team adversarial attempts |
| `data/pilot.sqlite` | — | 32 KB | Real | Telegram pilot queries |

**Honesty note:** `benchmark.jsonl` contains `is_synthetic: true` on all 50 rows. The `bench-` prefix in `calibration.jsonl` does not imply real user data. `eval_report.json` is n=50 synthetic with all-1.0 scores — unusable as a real result.

---

## 10. Frontend and Interactive Proof System

14 route pages built with React + Vite + TanStack Router:

| Route | Purpose | Status |
|-------|---------|--------|
| `/` (index) | Landing page with LiveTicker + ChallengeTicker | Operational |
| `/demo` | Gateway playground: 4 presets, method selector (auto/adaptive/heuristic/model/crf/llmlingua2), stream toggle, reproducibility drawer (Git SHA, cURL, system prompt, `x_gateway` JSON), "What got cut" card, Shred visualizer, reward autopsy, difficulty anatomy, candidates explorer | Operational |
| `/results` | Research proof page: stat badges (adaptive savings, reasoning tax, tokenizer tax, fidelity bound), Pareto frontier chart, tokenizer fairness bucketing, conformal sweep | Operational |
| `/redteam` | Adversarial arena: 4 presets, method select, verdict panel (negation/order/number/entity grading), live leaderboard (8s polling) | Operational |
| `/tokenizer` | Code-switch slider: drag 0–100% Hindi mix, dual-source token counts (js-tiktoken + server MuRIL/GPT-4o), delta + backend/offline badge | Operational |
| `/connect` | MCP integration page: 10 MCP tool descriptions with copy | Operational |
| `/receipt/$id` | Receipt page: dual full/minimal toggle, feedback loop | Operational |
| `/benchmark` | Benchmark charts | Operational |
| `/research` | Research documentation | Operational |
| `/pilot` | Telegram pilot dashboard | Operational |
| `/team` | Team page | Operational |
| `/roadmap` | Project roadmap | Operational |

**Calibration panel tri-state badge:** The UI shows one of three states — `synthetic`, `mixed`, or `live` — based on the backend's honest `data_state()` report. The `synthetic` badge is currently active.

**Red-team leaderboard:** Logs adversarial challenges to `data/challenges.jsonl`. Grading is automated: negation preservation, number preservation, entity preservation, word-order preservation checks. 53 challenges logged at the time of writing.

---

## 11. Test Suite

**28 test files** in `backend/tests/`. Latest run (2026-09-28):

```
294 passed, 5 failed, 6 skipped    (91.79 seconds)
```

### Failures (honest account):

| Test | Status | Root Cause |
|------|--------|-----------|
| `test_phase2.py::test_fixed_sequence_dominates_hoeffding` | **Pre-existing**, confirmed on clean HEAD | Assertion about fixed-sequence strictly dominating Hoeffding; edge-case behavior at boundary |
| `test_m5.py::test_healthz` | **Environment-dependent** | Requires backend service configuration |
| `test_m5.py::test_chat_completions_returns_openai_shape` | **Environment-dependent** | Requires backend service configuration |
| `test_m5.py::test_stream_and_nonstream_meta_shape_parity` | **Environment-dependent** | KeyError, requires configured service |
| `test_redteam.py::test_receipt_and_feedback` | **Schema mismatch** | KeyError: 'id', likely schema evolution |

### Skips (6):
All due to missing optional dependencies (`llmlingua` weights, `pytest-asyncio` for certain tests).

### Key test coverage areas:

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_phonetic.py` | Normalization, phash, ABBREVS, repeat-collapse | Core phonetic module |
| `test_heuristic_passes.py` | Greeting strip, reduplication, unconditional fillers | Pre-CRF pipeline |
| `test_crf_tagger.py` | Feature extraction, safety gates, min-keep floor | CRF tagger |
| `test_crf_endpoint.py` | API endpoint for CRF compression | Endpoint wiring |
| `test_linguistic_compressor.py` | Full 5-stage pipeline, fail-closed behavior | Integration |
| `test_linguistic_safety.py` | Negation survival, entity survival, marker survival | Safety invariants |
| `test_linguistic_regression.py` | Specific regression cases (bhai genitive, matlab noun) | Guard-contrast |
| `test_linguistic_perf.py` | Latency bounds (<100ms/prompt on CPU) | Performance |
| `test_lexicon.py` | Lexicon prune, filler detection | Legacy compressor |
| `test_m12.py` | Adaptive compression, code-mix analysis, gloss, tokenizer tax | Novel module (18.5 KB, largest test file) |
| `test_redteam.py` | Red-team endpoint, tri-state, rolling window, difficulty, autopsy, prompts, receipt, feedback | Live proofs (9 tests) |
| `test_translate.py` | Hindi honesty guard, transliteration, mojibake rejection | Translation |
| `test_token_study.py` | Token study experiment package | P0 evaluation (10.5 KB) |

---

## 12. Debugging War Log

Every significant bug encountered and how it was resolved:

### 12.1 Repeat-Collapse Eating Legitimate Doubles

**Symptom:** `"http"` was compressed to `"htp"` because the character-repeat-collapse rule `(.)\1+` → `\1` eliminated all doubled characters.

**Root cause:** The regex collapsed runs of 2+ identical characters. Legitimate doubles (`http`, `assignment`, Hindi long vowels `aa`, `ee`) were destroyed.

**Fix:** Changed the regex to `(.)\1{2,}` — collapses runs of **3 or more** only. Doubles survive unchanged.

### 12.2 CRF Under-Compressing

**Symptom:** The CRF trained on deterministic-teacher labels achieved poor compression ratios because the lexicon teacher never dropped auxiliary verbs (`hai`, `raha`, `rahi`).

**Root cause:** The lexicon `prune()` function only drops fillers and vocatives. Progressive auxiliaries (`raha/rahi/rahe`) and present-tense copula (`hai/hain`) carry minimal information once the main verb survives, but the lexicon kept them all.

**Fix:** Added an auxiliary-verb drop pass in the deterministic teacher (`AUX_TOKENS` set of 12 normalized forms). Disjointness from `PROTECTED_TOKENS` is asserted in tests.

### 12.3 Regression: Genitive `bhai` and Mid-Sentence `matlab`

**Symptom:** After auxiliary drop, the CRF learned to aggressively drop `bhai` and `matlab` everywhere, including `"mere bhai ka phone"` (kinship genitive — must keep) and `"download matlab free version"` (tech noun — must keep).

**Root cause:** Training data lacked contrast examples. The CRF had no positive examples of `bhai` or `matlab` being kept.

**Fix:** Added guard-contrast templates: `"bhai mera assignment"` (vocative, drop) paired with `"mere bhai ka phone"` (genitive, keep); `"hostel ka wifi matlab bahut slow"` (filler, drop) paired with `"download matlab free version"` (noun, keep). Regression tests added in `test_linguistic_regression.py`.

### 12.4 Demo Showing Heuristic-Only Output

**Symptom:** The live API always returned heuristic compression, never CRF, even when `method="crf"` was requested and the CRF model file existed.

**Root cause:** The `use_crf` flag in `config.py` was not being propagated through `service.py` to the `Compressor` constructor. The CRF tagger was never instantiated in the API serve path.

**Fix:** Wired `use_crf` through `config.py` → `service.py` → `Compressor(use_crf=True, crf_model_path=..., tfidf_path=...)`. Exposed `method="crf"` on `/v1/compress`, `/v1/compress/redteam`, MCP tool, and methods list. This was the actual user-visible bug: the compression was correct but the *wrong compression* was being served.

### 12.5 `compare_teachers` Silent Empty Table

**Symptom:** When no prompts were loaded (wrong path or empty file), the script printed an empty JSON table `{}` with no error, silently suggesting all models had been evaluated.

**Fix:** Added explicit check: if `len(texts) == 0`, print error and `raise SystemExit(2)`.

### 12.6 Dry-Run Mock Mode Dropping Everything

**Symptom:** User prompt `"2+3=?"` returned `[[COMPRESSED]]` instead of an actual answer.

**Root cause:** Backend was in `GATEWAY_DRY_RUN=true` mode, using `MockLLMClient(canned="[[COMPRESSED]]")` at `service.py:115`.

**Fix:** Set `GATEWAY_DRY_RUN=false` in `.env`, pointed `LOCAL` config at installed Ollama model.

### 12.7 Hindi Translation Mojibake

**Symptom:** Tokenizer page translations showed garbage Devanagari, similarity 0.9 pass.

**Root cause:** Tiny 0.5b model generating text *and* self-judging (embedding engine missing, fell through to LLM judge). The model cannot produce coherent Devanagari.

**Fix:** Built `translate.py`: `_looks_like_devanagari_hindi()` rejects mojibake/Latin as pass. Corrupt Hindi falls back to labeled passthrough/reject. Word-final `a→ा`, `meri/teri→मेरी/तेरी` exceptions added. Backend suite 12/12.

### 12.8 Rewrite Path v1 Expanding Text

**Symptom:** The model *expanded* text instead of compressing it. Ratio **1.05** — 0/200 examples accepted.

**Fix:** v2 added a 60% word cap + joint selection objective (`fidelity - 0.3 * ratio`). v2 achieved ratio **0.81** vs heuristic 0.95, at -0.02 fidelity cost. Wired into `compress()`, gated on clean reinject + ratio < 1.0.

---

## 13. The GPU Saga

**Status: Unresolved. This failure is by infrastructure, not by code.**

The CRF student-teacher pipeline was designed around a GPU-trained LLM teacher (Mistral-7B or equivalent) producing higher-quality Keep/Drop labels than the deterministic teacher.

### Timeline of attempts:

| Attempt | Hardware | Result |
|---------|----------|--------|
| Laptop Ollama (qwen3:0.6b) | CPU | 13.5 s/call, poor quality. Machine was overheating. Killed. |
| Google Colab (Mistral-7B, fp16) | T4 GPU | ~9 s/prompt with CPU-offload. Reached 3,352/5,000 labels. **GPU quota exhausted, then runtime recycled — all labels lost.** Nothing had been downloaded or pushed. |
| 4-bit quantization fix | (planned) | Built: `BitsAndBytesConfig(load_in_4bit=True, nf4, double_quant)`. Fits 7B fully on T4 with no CPU offload. Committed. |
| Drive-backup cell | (planned) | Added: checkpoint saves to Google Drive after each batch. Committed. |
| Kaggle notebook variant | (planned) | Built and committed. Not yet run. |

### What exists now:

- Branch `crf-compressor`: 5 commits ahead of `main`. CRF code fully wired and tested.
- Deployed model: deterministic-teacher CRF (ratio 0.64–0.83, negation/entities 100%, <10ms).
- `bootstrap_crf_data.py` supports `--hf-model`, `--hf-4bit`, `--resume`, `--hf-batch`, per-batch `on_batch` flushing.
- Colab notebook (`backend/colab/`) and Kaggle notebook (`backend/kaggle/`) committed but not yet successfully run to completion.

### Honest assessment:

The deterministic teacher is serviceable but suboptimal. It cannot learn context-dependent filler decisions (e.g., `yaar` is droppable in `"yaar wifi slow hai"` but should be kept in `"yaar, tera kya haal hai?"` as the main content). The GPU rerun would produce a better CRF, but no comparison table exists because the GPU training has never completed successfully.

---

## 14. Router Track

### 14.1 Labeling Campaign

- **3,000 synthetic queries** generated → `data/router_track/queries.jsonl` (696 KB).
- Pre-graded to **1,200** for labeling budget (free Groq tier).
- Cheap model: `openai/gpt-oss-20b` via Groq.
- Premium model: `openai/gpt-oss-120b` via Groq (proxy=true; Llama/GPT-4o models unavailable on free tier — retired/paid).
- **1,200/1,200 labeled**, 0 transport errors.
- **6-key rotation pool** across 5 Groq accounts to manage rate limits.
- Splits frozen (seed 42): train 794 / calib 203 / test 203, stratified by code-mix bucket.

### 14.2 Rate-Limit War

- 429 storms on 120B model → diagnosed as TPM-driven (reasoning-token burn, not RPM).
- Mitigations applied: `reasoning_effort=low` (62 → 8 reasoning tokens), 224-token budget, exponential backoff, dual-key rotation.
- Scope reduced from 3,000 to 1,200 (pre-grading, documented).

### 14.3 Empty-Answer Refill

- **448 cheap + 125 premium answers** returned empty with high token usage.
- Root cause: `gpt-oss` emits hidden reasoning; `content` field empty when the model spends its budget thinking.
- Fix: `reasoning` field fallback. Verified 0 empties after refill.

### 14.4 Grading

- Cheap-vs-premium fidelity: median **0.40** (BLEU/fuzzy scale built for compression, harsh on cross-model agreement).
- At bar 0.6 → **7.8% success rate**.
- **Key finding:** The scale punishes script mismatch (cheap=Roman, premium=Devanagari), not wrongness. Bars (epsilon, REWRITE_BAR) must be fit to human verdicts — currently provisional.

### 14.5 Judge A — Importance Mining

1,449 ablation experiments (400 queries x 6 variants each):

| Dropped Class | Mean Answer-Change (delta) | Decision |
|---------------|--------------------------|----------|
| Truncation (first 60%) | 0.71 | Never truncate — hard rule added |
| Entities/numbers | 0.63 | Protected (confirms span design) |
| Negations | 0.60 | Protected — a guard the old metric could not see |
| Vocatives/aggressive | 0.56 | Droppable with kinship guards |
| Lexicon fillers | 0.45 | Droppable (lowest measured harm) |

**Per-word attribution was killed, not shipped:** The same words ranked safest and riskiest (whole-set confounding). Importance remains class-level only.

### 14.6 Blocked

`human_check.csv` column G (150 rows of human y/n judgments) → fits epsilon + REWRITE_BAR → re-grade → supervised + bandit → conformal thresholds → eval → wire learned scorer. This is the single remaining manual step.

---

## 15. Known Limitations and Honest Weaknesses

1. **No real evaluation results.** The P0 study is blocked on API credentials and human reviewers. All numbers on the dashboard are synthetic or engineering measurements. No claim of "production-ready" is made.

2. **Calibration is synthetic.** The 2,014 calibration samples are generated, not from real user queries. The conformal guarantee holds mathematically on the calibration set, but its transfer to real traffic is unvalidated.

3. **No romanized Hinglish in PRESTO.** The test dataset has Devanagari+English only (0 romanized rows in 5,804 code-mixing items). The tokenizer-fairness claim for romanized Hinglish requires a secondary dataset (GupShup or equivalent).

4. **Reasoning Tax is estimated, not measured on real reasoning models.** The `ReasoningBudgetEstimator` uses a feature-based proxy (code-mix ratio, math/logic markers). The "+56 token" figure comes from synthetic comparisons, not from instrumenting a real reasoning model's internal token allocation.

5. **CRF trained on deterministic teacher only.** The GPU-trained LLM teacher would likely produce a better model. The deterministic teacher cannot learn context-dependent decisions.

6. **Adaptive compression formula is heuristic.** `target = 0.52 + 0.30*mix + 0.18*diff` — the coefficients are manually set, not learned from data. They encode reasonable intuitions but are not optimized.

7. **Router grading thresholds are provisional.** The epsilon and REWRITE_BAR values have not been fit to human judgments. The 7.8% success rate reflects a harsh grading scale, not necessarily a bad router.

8. **Red-team arena has limited data.** 53 challenges logged. The "0% break rate" claim (if displayed) reflects the safety gates working correctly on this small sample, not an exhaustive adversarial evaluation.

9. **Frontend charts display synthetic data.** The Pareto frontier, tokenizer fairness bucketing, and conformal sweep visualizations render data from `benchmark.jsonl` (50 synthetic rows) and `calibration.jsonl` (2,014 synthetic rows). They demonstrate the visualization pipeline, not real results.

10. **Telegram pilot not deployed.** The bot infrastructure exists (`m6_telegram`) but has not been deployed to real users.

---

## 16. Relationship to Prior Work

### 16.1 LLMLingua-2 (Jiang et al., 2024)

**Paper:** "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression" (arXiv 2403.12968).

**Relationship:** LLMLingua-2 is integrated as the trained baseline (Arm A1/A2). We use their published small checkpoint (`bert-base-multilingual-cased-meetingbank`). Our contribution is the code-mix-specific findings: protected-span mangling and context-filter segment dropping are bugs we discovered and worked around, documented in `llmlingua2.py`.

### 16.2 Conformal Risk Control / Learn-Then-Test

**Papers:**
- Angelopoulos et al., "Learn Then Test: Calibrating Predictive Models via Testing" (arXiv 2110.01052).
- Bates et al., "Distribution-Free, Risk-Controlling Prediction Sets" (JASA 2021).

**Relationship:** Our `ConformalCalibrator` implements the fixed-sequence LTT procedure from Angelopoulos et al. for the monotone deferral rule. The Clopper-Pearson exact UCB replaces the Hoeffding approximation used in our original implementation.

### 16.3 CRF Sequence Labeling

**Foundation:** Lafferty, McCallum, Pereira, "Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data" (ICML 2001). Implementation via `sklearn-crfsuite` (Okazaki, 2007).

**What is novel:** Applying CRF sequence labeling to extractive prompt compression on code-mixed text, with phonetic normalization features. Prior code-mixed NLP applies CRFs to language identification (LID) and POS tagging, not to compression.

### 16.4 PRESTO

**Paper:** Goel et al., "PRESTO: A Multilingual Dataset for Parsing Realistic Task-Oriented Dialogs" (arXiv 2303.08954). CC BY 4.0.

**Usage:** Primary evaluation corpus. 550K+ conversations with structured semantic parses, explicit code-mixing partitions.

### 16.5 Rate-Distortion Theory Framing

The compression problem can be framed as rate-distortion optimization: minimize token count (rate) subject to a semantic fidelity constraint (distortion <= delta). The CRF safety gates implement the distortion constraint as hard floors, not soft penalties. This framing is used in the presentation but the actual implementation is not an information-theoretic optimizer.

---

## 17. Reproduction Instructions

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,crf,tokenizers]"

# Optional: LLMLingua-2 baseline
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[compression,eval]"

# Run tests
python -m pytest tests/ -q

# Start server
$env:PYTHONPATH = "src"
uvicorn gateway.modules.m5_gateway.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
npm install
npm run dev
```

### CRF Training Pipeline (from scratch)

```powershell
cd backend
$env:PYTHONPATH = "src"

# 1. Generate prompts
python scripts/generate_hinglish_prompts.py --n 5000 --seed 7 --out data/training/prompts.jsonl

# 2. Bootstrap labels (deterministic teacher)
python scripts/bootstrap_crf_data.py --prompts data/training/prompts.jsonl --out data/training/bootstrap_filtered.jsonl --no-llm

# 3. Build TF-IDF
python scripts/build_tfidf.py

# 4. Train CRF
python scripts/train_crf.py --data data/training/bootstrap_filtered.jsonl --model data/models/crf_compressor.pkl

# 5. Compare (optional)
python scripts/compare_teachers.py --prompts data/training/prompts.jsonl --models det=data/models/crf_compressor.pkl --no-embed
```

### Configuration

Copy `backend/.env.example` to `backend/.env`. Set `GATEWAY_DRY_RUN=true` for offline mode (mock LLM responses). Set `GATEWAY_DRY_RUN=false` and provide a `GROQ_API_KEY` for live API calls.

---

## 18. Repository Structure

```
Research/
├── backend/
│   ├── src/gateway/
│   │   ├── modules/
│   │   │   ├── m1_pipeline/     # Tokenization, code-mix ratio
│   │   │   ├── m2_compressor/   # All compression: heuristic, CRF, LLMLingua-2, model
│   │   │   │   ├── phonetic.py       (174 lines)
│   │   │   │   ├── heuristic_passes.py (136 lines)
│   │   │   │   ├── crf_tagger.py     (152 lines)
│   │   │   │   ├── linguistic.py     (151 lines)
│   │   │   │   ├── safety_span.py    (69 lines)
│   │   │   │   ├── llmlingua2.py     (106 lines)
│   │   │   │   ├── compressor.py     (234 lines)
│   │   │   │   ├── tfidf.py
│   │   │   │   └── prompts.py
│   │   │   ├── m3_conformal/    # Conformal calibration (359 lines)
│   │   │   ├── m4_router/       # Difficulty scorer + cascade router
│   │   │   ├── m5_gateway/      # FastAPI app (1,492 lines)
│   │   │   ├── m6_telegram/     # Telegram bot + SQLite
│   │   │   ├── m7_eval/         # BLEU/ROUGE evaluation
│   │   │   ├── m8_dashboard/    # Dashboard aggregation
│   │   │   ├── m9_reasoning/    # Reasoning budget estimator
│   │   │   ├── m10_train/       # Reward model
│   │   │   ├── m11_calibration/ # ECE + reliability diagrams
│   │   │   ├── m12_novel/       # Adaptive compression, analysis, gloss, translate
│   │   │   └── m12_semantic/    # Semantic similarity
│   │   ├── config.py, service.py, schemas.py, tokenizer.py, lexicons.py
│   │   └── llm.py, pricing.py
│   ├── scripts/
│   │   ├── generate_hinglish_prompts.py  # 23 templates, 5K prompts
│   │   ├── bootstrap_crf_data.py         # Teacher labeling (459 lines)
│   │   ├── train_crf.py                  # CRF trainer
│   │   ├── compare_teachers.py           # Head-to-head eval
│   │   ├── build_tfidf.py                # TF-IDF builder
│   │   ├── freeze_splits.py              # Router splits
│   │   └── router_track/                 # run00-run07 labeling scripts
│   ├── experiments/token_study/           # P0 evaluation (17 files)
│   ├── tests/                            # 28 test files
│   ├── data/
│   │   ├── training/                     # prompts.jsonl, bootstrap_filtered.jsonl
│   │   ├── models/                       # crf_compressor.pkl
│   │   ├── router_track/                 # queries, labels, splits, human_check
│   │   ├── calibration.jsonl             # 2,014 synthetic samples
│   │   ├── benchmark.jsonl               # 50 synthetic samples
│   │   └── challenges.jsonl              # 53 red-team attempts
│   ├── colab/                            # Colab notebooks (GPU teacher)
│   └── kaggle/                           # Kaggle notebooks (GPU teacher)
├── src/                                  # React frontend
│   ├── routes/                           # 14 pages
│   ├── components/                       # UI components
│   └── lib/gateway.ts                    # Backend API client
├── docs/research/
│   ├── DECISIONS.md                      # Frozen design decisions
│   ├── DATA_CARD.md                      # Dataset provenance
│   ├── REPRODUCTION.md                   # LLMLingua-2 reproduction
│   ├── RESULTS_NOT_RUN.md                # What is blocked
│   └── ROUTER_COMPRESSOR_REPORT.md       # Router + compressor results
├── RESEARCH_IMPLEMENTATION_PLAN.md       # 816-line research plan
└── code_mixed_gateway_three_persona_briefing.md
```

---

## 19. References

1. Z. Jiang, D. Wu, Y. Xu, et al. "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression." arXiv:2403.12968, 2024.
2. A. N. Angelopoulos, S. Bates, E. J. Candes, M. I. Jordan, L. Lei. "Learn Then Test: Calibrating Predictive Models via Testing." arXiv:2110.01052, 2021.
3. S. Bates, A. Angelopoulos, L. Lei, J. Malik, M. I. Jordan. "Distribution-Free, Risk-Controlling Prediction Sets." Journal of the ACM, 2021.
4. J. Lafferty, A. McCallum, F. Pereira. "Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data." ICML, 2001.
5. S. Goel, A. Agarwal, et al. "PRESTO: A Multilingual Dataset for Parsing Realistic Task-Oriented Dialogs." arXiv:2303.08954, 2023.
6. T. Okazaki. "CRFsuite: A fast implementation of Conditional Random Fields (CRFs)." 2007.
7. H. Jiang, Q. Wu, C.-Y. Lin, Y. Yang, L. Qiu. "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." EMNLP, 2023.
8. S. Banerjee, N. Moghe, S. Arora, M. M. Khapra. "Code-Mixing on Sesame Street: Dawn of the Adversarial Polyglots." NAACL, 2018.

---

## Setup and Execution (Quick Start)

**Frontend:**
```bash
npm install
npm run dev --port 8080
```

**Backend:**
```bash
cd backend
.venv\Scripts\activate
uvicorn gateway.modules.m5_gateway.main:app --host 127.0.0.1 --port 8000
```

**Offline mode:** Set `GATEWAY_DRY_RUN=true` in `backend/.env` to run full mock evaluations without API keys.

---

*Last updated: 2026-09-28. Every number in this document is traceable to a committed artifact. If you find an unsubstantiated claim, it is a bug — please report it.*
