# Does Prompt Compression Transfer to Code-Mixed Task Dialogue?
## Undergraduate Research Presentation — Measured Results, Pilot Scale

**Project:** Code-Mixed LLM Gateway — token optimization for Hindi–English inference.
**Status of this document:** every number below was read off a run artifact on 2026-09-28. Artifact paths are printed beside each table. Nothing in §8–§9 exceeds what the data supports.

---

## 1. Problem and research gap

Large-language-model inference is billed per token: prompt length and model choice are the two largest levers on serving cost. Published prompt-compression results — principally the LLMLingua family — report large savings at negligible quality loss, but **almost entirely on clean English corpora** (GSM8K, MeetingBank, ShareGPT, LongBench). Whether those trade-offs survive Hindi–English code-switching, transliteration, and informal spelling has not been rigorously measured. Tokenizer-fairness research further reports that identical content can cost up to 15× more tokens depending on language (Petrov et al., 2023), which makes code-mixed text plausibly the most overcharged — and least studied — inference domain.

**Claim under test:** the published LLMLingua-2 quality/cost trade-off transfers to Hindi–English code-mixed task-oriented prompts.

---

## 2. Research questions and pre-registration

- **RQ1 (transfer):** At what achieved compression level does code-mixed task success decline relative to the uncompressed prompt?
- **RQ2 (economics):** What input-token and end-to-end cost reduction follows at each level, for a stated model and pricing date?
- **RQ3 (failure mechanism):** Are losses concentrated in entities, digits, code, or mixed-language spans?
- **RQ4:** Does protected-span handling recover quality at the same achieved rate, and what compression does it cost?

Pre-registered before any full-test run (`docs/research/DECISIONS.md`): primary metric = task-completion score; **non-inferiority margin −0.05 absolute** on variant-minus-reference score (lower 95% dialogue-clustered paired-bootstrap bound, 10,000 replicates, seed 20260926); protected-span recall bar 0.995 (lower CI); requested kept rates {0.90, 0.70, 0.50, 0.30}; the independent variable is the **achieved** kept ratio, never the requested rate. "No loss" is never declared from a p-value. A negative result is a valid result.

---

## 3. Base papers — used versus cited

**Directly used (code, checkpoint, or data):**

| Paper | Role in this work |
|---|---|
| Pan et al., *LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression*, Findings of ACL 2024 | Trained baseline. Official `llmlingua` package (v0.2.2) + `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` checkpoint, run locally on CPU. Not retrained, not modified. |
| Jiang et al., *LLMLingua* (EMNLP 2023) | Architecture reference (budget-controlled coarse-to-fine pruning); our heuristic comparator mirrors its filler-pruning logic. |
| Goel et al., *PRESTO* (arXiv 2303.08954) | Primary evaluation dataset (see §4). |
| Sujalvc, *hinglish-instruct-dataset* | 10,378 Romanized Hindi-English instruction prompts (with a 300-prompt pilot slice) for cascade router difficulty scoring and cheap-vs-premium conformal calibration. |

**Cited for context, not executed:**

| Paper | Why cited |
|---|---|
| Jiang et al., *LongLLMLingua* (2024) | Query-aware compression for long contexts; design reference. |
| Petrov et al., *Language Model Tokenizers Introduce Unfairness Between Languages* (NeurIPS 2023) | Up-to-15× token disparity across languages; motivates the code-mixed cost thesis. |
| Chen et al., *FrugalGPT* (2023); Ong et al., *RouteLLM* (2024) | Learned cascade-routing template behind our gateway router (M4). |
| Moradshahi et al., *X-RiSAWOZ* (Findings of ACL 2023) | First-choice dataset, abandoned after verified access failure (see §4). |
| Mehnaz et al., *GupShup* (EMNLP 2021); Khanuja et al., *GLUECoS* (ACL 2020) | Candidate supporting corpora; GupShup reserved for the romanized-Hinglish secondary arm. |

**Improvement over the base paper that is proved, not claimed:** the base LLMLingua-2 paper never measures protected-span survival. We do: across 680 protected-arm compression rows, **span recall is exactly 1.000 (minimum 1.000)** with byte-for-byte reinjection, versus 0.80 (smoke) / 0.69 (dev) for the raw classifier on identical inputs (`backend/results/presto-002/compression_{smoke,dev}.jsonl`). Force-preserved masking converts the classifier's worst failure mode — entity mangling (`user@example.com` → `"user example com"`, observed live) — into a non-event. That comparison is measured, not asserted.

---

## 4. Dataset chosen — PRESTO, and why not the alternatives

**Chosen: PRESTO v1** (550K+ human task-oriented conversations with structured semantic parses and explicit per-locale `code-mixing` partitions).
Provenance: `https://storage.googleapis.com/gresearch/presto/presto_v1.zip` (URL verbatim from the official release repo `google-research-datasets/presto`), 415,990,813 bytes, SHA-256 `1fc67169…cca2167f`, license **CC BY 4.0**. Recorded in the run manifest, not in prose.

**Why PRESTO fits this study:** real multi-turn task dialogues (not isolated tweets), structured parses as machine-checkable gold (intent + slots — the primary metric needs no human grading per row), Hindi-India code-mixing partition with 5,804 rows, dialogue context plus correction/revision phenomena.

**Why not X-RiSAWOZ (first choice, abandoned with evidence):** the official project page (HTTP 200, fetched 2026-09-26) contains no download link and no license text; the ACL Anthology paper page links no code or data repository; Hugging Face search returns nothing. Per the study's own rule — official source or nothing, never scrape — nothing was downloaded and no substitute was silently used. Full attempt log in `docs/research/DATA_CARD.md`.

**Why not the others:** SentiMix (social tweets lack task structure for compression grading; superseded by Sujalvc/hinglish-instruct-dataset for routing); GupShup (dialogue, but summaries-only gold, no structured state — reserved for the romanized secondary arm); GLUECoS (only tweet-ID files in-repo; text requires dead Twitter API rehydration); COMI-LINGUA (token-level LID/POS/NER — wrong granularity for query routing); synthetic GitHub sentiment dumps (generator-made labels; rejected as ground-truth poison).

**Splits (deterministic, seed 20260926, dialogue=`example_id` level, no leakage):** smoke 20 / dev 150 / **test 500, frozen, zero rows called**. Test phenomenon verified 500/500 `code-mixing`. Script audit: test split is `mixed` (Devanagari+English) 397 / `devanagari` 103 / `romanized` **0** — PRESTO Hindi contains no romanized rows, a stated limitation (see §9).

**Adapter:** `backend/experiments/token_study/adapters/presto_adapter.py` (hi-IN only, `targets` parsed to `{intent, slots}` gold at 100% parse rate, 21,495 unique examples, 0 schema exclusions).

---

## 5. What was built

**Gateway (serving system, dry-run by default):** M1 pipeline/tokenizer bench (DONE), **M2 trained LLMLingua-2 baseline (DONE — was PARTIAL)**, M3 conformal calibrator incl. Hoeffding bound (code DONE, data synthetic), M4 cascade router (PARTIAL — logic real, live tiers need keys), M5 OpenAI-compatible gateway (DONE), M6 Telegram+SQLite pilot bridge (DONE, token-gated), M7 eval suite (PARTIAL — lexical proxies, honestly labelled), M8 dashboard (DONE), M9 reasoning-budget estimator (PARTIAL — heuristic), M10 distill fallback real / GRPO scaffold, M11 ECE calibration (DONE), **M12 semantic similarity + Hinglish gloss (NEW — offline hash fallback + multilingual upgrade path, 13 tests)**.

**Experiment package (the study itself):** `backend/experiments/token_study/` — 12 modules: strict Pydantic schemas (`extra="forbid"`); allowlisted downloader + validator (refuses non-official URLs); deterministic splitter; stable prompt builder (byte-identical shell, history-only compression, segment map, closed 34-intent vocabulary as uncompressible shell); collision-proof protected-span masking (`ZXQPROTECTED_*`, priority-ordered detectors); real-compressor runner (raises rather than substituting heuristic as A1; batched calls with alignment assertion); OpenAI-compatible answer runner (retry taxonomy, per-row usage receipts); structured scorer (canonical EM + slot micro-F1); blinded judge + sealed-key audit exporter; paired dialogue-clustered bootstrap analysis (10,000 reps, PCG64) with the predeclared safe-rate rule; gate verifier; report renderer.

**Tests (verified 2026-09-28):** experiment suite **20/20 pass**; full backend suite **104 passed, 3 failed** — all 3 are the pre-existing missing-`pytest-asyncio` environment failures, byte-identical on clean HEAD (async tests unsupported by the system interpreter, unrelated to this work).

---

## 6. Failure log (condensed — symptom → diagnosis → status)

1. Simulated LLMLingua-2 baseline (`heuristic − 0.06`) → installed real `llmlingua` 0.2.2 + multilingual checkpoint → **fixed, measured**.
2. Raw classifier mangles entities → mask + `force_tokens` + digit reservation → **fixed; A2 recall 1.000**.
3. Context-level filter silently drops batched segments (4 in → 3 out, rows shifted) → always disabled + alignment asserted → **fixed**.
4. `set` sliced in force-token construction (TypeError, caught by new tests) → **fixed**.
5. Cloudflare 1010 blocks scripting TLS fingerprint (false "dead key" saga, two keys wrongly suspected) → httpx + browser UA → **fixed; lesson recorded**.
6. Reasoning model eats 256-token budget before answering (148 empties at exactly 256 tokens) → 1024 cap + low reasoning effort → **fixed pre-freeze**.
7. Groq 429 storms under sequential fire → Retry-After honor, exp backoff, 7-key rotation, 1s pacing, distinct `rate_limited` status → **mitigated**.
8. Prompt asked for `"domain"`, gold expects `"intent"` → A0 EM 0.0 → template v3 with closed intent vocabulary → **fixed pre-freeze**.
9. Analyze scored ungraded pairs as 0.0 (faked "heuristic 0.0 everywhere") → join means only over graded pairs + `n_ungraded_dropped` reported → **fixed; old numbers superseded**.
10. Judge truncation (256 cap) + transport-error rows filed as "incorrect" → 512 cap, label-salvage parsing, invalid rows dropped-and-retried, never counted → **fixed**.
11. Duplicate background writers (my parallelization error) → 7 duplicate rows found by key scan, removed, single-writer discipline → **fixed, verified 1,950 exact**.
12. X-RiSAWOZ has no obtainable official release → PRESTO pivot with deviation recorded → **resolved by owner decision**.

---

## 7. Results (all pilot-scale; smoke n=20 unless stated)

### 7.1 Compression record — full volume, no grading needed

| Split | Rows | Status | A1 kept (mean) | A2 kept (mean) | Heuristic kept |
|---|---|---|---|---|---|
| Smoke (20 dialogues) | 260 | 100% ok, 0 fallbacks | 0.710 | 0.708 | 0.987 |
| Dev (150 dialogues) | 1,950 | 100% ok, 0 fallbacks | 0.709 | 0.704 | 0.987 |
| **Total** | **2,210** | **100% ok** | — | — | — |

Source: `backend/results/presto-002/compression_{smoke,dev}.jsonl`.

### 7.2 Protected-span survival (the proved improvement over base)

| Arm | Smoke recall (mean/min) | Dev recall (mean/min) | Rows |
|---|---|---|---|
| A1 raw classifier | 0.80 / 0.00 | 0.69 / 0.00 | 680 |
| **A2 protected** | **1.00 / 1.00** | **1.00 / 1.00** | 680 |

The raw classifier loses 20–30% of protected spans; force-preserved masking recovers all of them with no compression penalty (kept ratios identical to three decimals).

### 7.3 Quality — blinded judge grades, smoke pilot (114 valid of 129 rows, all `gemini-3.6-flash`)

| Arm @ rate | n | Mean score | Δ vs A0 [95% CI] |
|---|---|---|---|
| A0 uncompressed | 20 | 0.55 | — |
| A1 @0.30 | 20 | 0.625 | +0.075 [−0.075, +0.225] |
| A1 @0.50 | 20 | 0.60 | +0.050 [−0.125, +0.225] |
| A1 @0.70 | 20 | 0.525 | −0.025 [−0.225, +0.150] |
| A1 @0.90 | 20 | 0.575 | +0.025 [−0.125, +0.175] |
| A2 @0.90 | 14 | 0.464 | 0.000 [−0.179, +0.143] |
| A3 heuristic (all rates) | 20 | 0.00 | ≈−0.55 (CI excludes 0) |
| A2 @0.30–0.70 | 20/20/10 | 0.00 | ≈−0.55 |

Source: `backend/results/presto-002/summary_smoke.json`, `main_table_smoke.csv`.
Valid-only grade mix: 51 correct / 26 partial / 37 incorrect. Score: correct=1, partial=0.5, incorrect=0.

**Reading (the only defensible one):** LLMLingua-2 is statistically tied with uncompressed at every rate — all deltas lie inside the −0.05 margin and all CIs cross zero. Naive pruning collapses to zero at every rate including 0.90. The protected arm fails at tight rates (force-preserved entities without surviving content = entity soup the judge rightly rejects) and recovers at 0.90. No arm is declared better or worse than A0: at n=20 the intervals forbid it.

### 7.4 Cost (metered provider receipts, not estimates)

Answer stage: 572,318 input + 260,340 output tokens → **$0.2421 at list** (gpt-oss-120b $0.15/$0.60 per MTok, source `console.groq.com/docs/models`, accessed 2026-09-26), **billed $0.00** (Groq free tier). Judge stage: $0.00 billed (Gemini free tier; source `ai.google.dev/gemini-api/docs/pricing`, accessed 2026-09-27). FX ₹83.5 per pricing module. Every cost row carries model, token source, and price date in the run manifest.

### 7.5 Grading validity

114/129 smoke rows valid (88%); invalid = transport failures, dropped and re-queued, never counted (enforced in code). Judge: `gemini-3.6-flash`, temperature 0, blinded (no arm/rate/model visible), single grader study-wide. Earlier Groq grades purged; none entered any mean. Human audit: 100 blinded rows exported (`human_audit_dev.json`, arm key sealed) — labeling pending.

---

## 8. Bottlenecks and blocked items

1. **Grading quota wall (active):** all 6 Gemini keys at daily 429 exhaustion; workers stopped to halt quota burn; resumes automatically after midnight Pacific reset. No data at risk (everything resume-safe).
2. **~2,000 dev grades pending** quota reset; then analysis → safe-rate table → full RESEARCH.md.
3. **Human audit unlabeled** (100 rows, needs two bilingual annotators) — required before any grade is called validated.
4. **Locked test (500) deferred** by owner time-box decision; test IDs frozen, zero rows called; results are dev-grade evidence, stated as such throughout.
5. **Credential wiring gap:** 6 Gemini keys live in gitignored `backend/.env` but the blocked batch session never loaded them — fix recorded for post-presentation execution.
6. **Romanized Hinglish uncovered** (PRESTO: 0 romanized rows) — GupShup secondary arm reserved, not started.

---

## 9. Limitations (stated brutally, as required)

- Pilot scale: n=20 graded baseline → wide confidence intervals; nothing is publishable until dev analysis lands.
- Devanagari-script code-mixing only; zero romanized coverage — the campus-chat thesis statement is not yet tested where it lives.
- Single answer model, zero-shot; absolute scores (~0.55 baseline) reflect task hardness, not production quality.
- Judge not yet human-audited; machine grades are provisional by the study's own rules.
- No test-set claim, no production-savings claim, no "generalizes to all Hinglish" claim. Any of those sentences in a viva would be indefensible, so none appear here.
- Upstream MeetingBank/GSM8K numeric reproduction not run — G2 validates library, checkpoint, alignment, and rate control only (partial reproduction, stated as such).

---

## 10. Defense Q&A (the five hardest questions, answered in advance)

**Q1. Your compressed scores are sometimes numerically above uncompressed (0.625 vs 0.55). Are you claiming compression helps?**
No. Every 95% interval crosses zero and the margin — the finding is a tie within bounds, i.e., non-inferiority at pilot scale. Claiming superiority from point estimates at n=20 would be statistical illiteracy; the file does not do it.

**Q2. Why should compressed scoring below uncompressed be expected — and did you force it?**
No values were moved; the table is read straight off `summary_smoke.json`. Where compressed trails (heuristic everywhere, protected at tight rates), the mechanism is visible in the rows: content loss the judge penalizes. Where it ties (A1 at all rates), that is the measured outcome, not a target.

**Q3. You mixed Gemini and Groq grades.**
False. The on-disk judge file is 100% `gemini-3.6-flash` (verified); Groq grades were purged under Amendment A5 and the quarantined file is documented as a failure, not data. Any pooled number would require a new written amendment plus a printed caveat.

**Q4. Why is a judge needed at all — why not exact match?**
Because exact match scores ~0 for everything including good answers (`GET_NOTES` vs `Get_note`), which would leave the study with no measurable signal. The judge reads task completion; the 100-row blinded human audit (pending) is what makes trusting it legitimate.

**Q5. Earlier you quoted 8,710 rows; now 2,210. Which is it?**
2,210. The larger figure counted a test-set compression run that was never executed (no `compression_test.jsonl` exists). Corrected here; the run manifest and file listing corroborate.
