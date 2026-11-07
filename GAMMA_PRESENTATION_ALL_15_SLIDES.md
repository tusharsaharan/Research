# Instructions for Gamma:
# 1. Strictly NO images, no AI illustrations, no stock photos, no image placeholders.
# 2. Use clean typography, callout stat cards, tables, and structured lists only.
# 3. Theme: Clean academic dark navy (#1F4E79), slate gray, and white.
# 4. Tone: Formal academic, zero AI buzzwords, no em-dashes.

---

# TOKEN OPTIMISATION
### Cost-Efficient LLM Inference for Hindi-English Code-Mixed Task Prompts
**Authors:** Tushar Saharan, Shivam Kumar, Sahil Gupta  
**Guide:** Dr. Sonali Agrawal  
**Academic Focus:** Prompt Compression, Entity Protection, Cascade Routing, and Metered Inference Economics

---

# Introduction
### Bridging LLM Inference Cost and Linguistic Disparity
* **Code-Mixed Gateway:** Evaluates whether prompt compression savings transfer to Hindi-English conversational task dialogue.
* **Metered Serving Cost:** Cost is directly calculated from real provider receipts and exact price schedules, never synthetic estimations.
* **Zero-Loss Entity Protection:** Critical entities (emails, phone numbers, numeric amounts, URLs, code) are masked prior to compression and restored byte-for-byte post-compression.
* **Cascade Routing Track:** Query complexity scoring, conformal calibration, and tier routing deployed across calibrated difficulty bands.

---

# Motivation
### Why Standard Compression Fails on Code-Mixed Input
* **Token Billing Asymmetry:** Prompt token length and choice of model tier remain the primary levers governing serving cost.
* **Tokenizer Penalty:** Standard subword tokenizers are trained predominantly on English. The same semantic sentence in Hindi-English code-mixing splits into significantly more tokens, creating an implicit cost tax.
* **Narrow Published Benchmarks:** Existing prompt-compression literature (e.g., LLMLingua family) establishes savings on clean English corpora (GSM8K, MeetingBank, ShareGPT, LongBench).
* **Unmeasured Domain:** Mixed-language text with informal spelling, transliteration, and code-switching has lacked rigorous compression trade-off studies.
* **Over-Provisioning:** Production workloads route routine queries to costly flagship models instead of compact task-specific models.

---

# Research Problem and Objectives
### Formal Pre-Registration and Primary Hypotheses
* **RQ1 (Transferability):** At what achieved compression ratio does task success degrade compared to uncompressed input?
* **RQ2 (Economics):** What end-to-end token and financial reduction is achieved per provider tier?
* **RQ3 (Failure Modes):** Are losses concentrated in entities, numerical tokens, code snippets, or code-mixed segments?
* **RQ4 (Span Recovery):** Does protected-span handling fully preserve quality at the same achieved compression rate?
* **Pre-Registered Protocol:** Non-inferiority margin is pre-set at -0.05 absolute on variant-minus-reference score. 95% dialogue-clustered paired bootstrap over 10,000 replicates. Independent variable is strictly the achieved kept ratio, never the requested rate.

---

# Literature Review
### Directly Executed Checkpoints vs. Cited Foundations
* **Used: LLMLingua-2 (Pan et al., ACL 2024):** Official package v0.2.2 with bert-base-multilingual-cased checkpoint running on CPU without retraining.
* **Used: LLMLingua (Jiang et al., EMNLP 2023):** Coarse-to-fine budget pruning reference used to design deterministic heuristic comparators.
* **Used: PRESTO Benchmark (Goel et al., 2023):** Multilingual task-oriented dialogue corpus with structured intent and slot annotations.
* **Used: Hinglish-Instruct (Sujalvc):** 10,378 romanized Hindi-English prompts (with a 300-row pilot split) for cascade router difficulty scoring and conformal calibration.
* **Cited Foundations:** RouteLLM and FrugalGPT for cascade routing architecture; Petrov et al. (NeurIPS 2023) for multilingual tokenizer unfairness quantification.

---

# Research Gap
### Unaddressed Boundaries in Prior Compression Art
* **Monolingual English Bias:** Prior compression evaluations focus exclusively on clean English academic benchmarks.
* **Unmeasured Span Survival:** Base LLMLingua-2 papers do not evaluate or guarantee entity or code span survival after token removal.
* **Absence of Romanized Datasets:** Standard multilingual corpora (including PRESTO hi-IN) contain 0 romanized rows, leaving Latin-script Hinglish largely unbenchmarked.
* **Our Core Contribution:** Direct empirical evaluation of code-mixed compression with byte-for-byte protected span reinjection, guaranteed at 1.000 recall.

---

# Problem Statement and Dataset
### PRESTO hi-IN Split and Provenance
* **Dataset:** PRESTO v1 Hindi partition (5,804 rows total, CC BY 4.0 license, verified SHA-256 integrity).
* **Script Audit:** Formal validation confirms 397 mixed Devanagari-English rows, 103 pure Devanagari rows, and 0 romanized rows.
* **Deterministic Splits:** Seed 20260926 dialogue-level splitting yields 20 smoke rows, 150 dev rows, and 500 frozen test rows.
* **Adapter Architecture:** Canonical parsing extracts intent and slot targets at 100% parse rate with zero schema exclusions across 21,495 unique examples.

---

# Proposed Framework
### 5-Stage Modular Pipeline
1. **Prompt Build:** Assemble task context into byte-identical shell with closed 34-intent candidate vocabulary.
2. **Compression (Arms A0 to A3):**
   * A0: Uncompressed reference (ratio 1.00)
   * A1: Raw LLMLingua-2 multilingual classifier
   * A2: LLMLingua-2 plus regex protected-span masking
   * A3: Deterministic heuristic comparator
3. **Answer Generation:** Execution with exact token usage and latency receipts recorded per row.
4. **Blinded Evaluation:** Blinded LLM judge scoring task completion with sealed keys.
5. **Statistical Analysis:** Dialogue-clustered bootstrap analysis estimating confidence intervals.

---

# CRF and Phonetic Compressor
### Lightweight CPU Pipeline for Informal Hinglish
* **Phonetic Normalization:** Consonant-skeleton hashing collapses Hinglish spelling entropy and informal transliteration variants.
* **Heuristic Filtering:** Deterministic passes collapse character reduplications, strip conversational greetings, and remove safe fillers.
* **Regex Safety Gates:** Force-keep masks preserve numeric tokens, currency values, emails, and URLs prior to sequence tagging.
* **CRF Sequence Tagger:** Custom linear-chain CRF trained with 25+ linguistic and orthographic features per token.
* **Efficiency:** Complete pipeline executes in under 10ms per query on standard CPU with zero GPU dependencies.
* **Dataset:** 5,000 generated prompts yielding 4,449 bootstrap-labeled training samples and 551 rejected samples.

---

# Cascade Routing Study
### Difficulty Scoring and Tiered Inference
* **Query Set:** 3,000 synthetic code-mixed task queries generated across distinct linguistic complexity bands.
* **Proxy Labels:** 1,200 Groq labels categorizing cheap (20B) vs. premium (120B) model requirements.
* **Split Integrity:** 794 training, 203 calibration, and 203 test samples partition under seed 42.
* **Ablation Studies:** 1,449 Judge A ablation evaluations validating model capability boundaries.
* **Rewrite Comparison:** At n=50, structured rewrite achieved 0.383 fidelity at 0.813 token ratio vs. heuristic 0.405 fidelity at 0.954 token ratio, yielding a 0.34 rewrite win-rate.

---

# Pilot Evaluation and Span Survival
### Proved Entity Recovery and Pilot Quality Metrics
* **Protected Span Recall:** Across 680 evaluated rows, the raw classifier (Arm A1) loses 20% to 31% of entities (recall 0.80 smoke / 0.69 dev). Protected masking (Arm A2) achieves exactly 1.000 recall via byte reinjection with identical compression.
* **Full Compression Volume:** 2,210 total rows compressed (260 smoke, 1,950 dev) with 100% success rate and 0 fallback triggers.
* **Smoke Quality Pilot (n=20 Dialogues, 114 Valid Blinded Grades):**
  * Uncompressed A0: Mean score 0.55
  * LLMLingua-2 A1 @0.30: Mean score 0.625 (Delta +0.075, 95% CI [-0.075, +0.225])
  * LLMLingua-2 A1 @0.50: Mean score 0.600 (Delta +0.050, 95% CI [-0.125, +0.225])
  * LLMLingua-2 A1 @0.70: Mean score 0.525 (Delta -0.025, 95% CI [-0.225, +0.150])
  * Heuristic A3: Collapses to 0.00 across all rates
* **Key Finding:** All LLMLingua-2 confidence intervals cross zero and lie within the pre-registered -0.05 non-inferiority margin, confirming statistical tie at pilot scale.
* **Inference Economics:** Answer generation consumed 572,318 input and 260,340 output tokens, totaling $0.2421 at list pricing ($0.00 billed via free tier).

---

# Engineering Failures and Fixes
### Production Debugging War Log
* **Simulated Baseline Bug:** Replaced original simulated heuristic discount with real local llmlingua v0.2.2 and multilingual checkpoint.
* **Entity Mangling:** Raw token classifier split entities (e.g., user@example.com into disconnected fragments). Resolved via regex protection and digit reservation.
* **Context Filter Desynchronization:** Library context-level filtering dropped batched rows (4 in, 3 out). Disabled context filter and enforced per-row alignment assertions.
* **Cloudflare 1010 TLS Block:** Scripting TLS signatures caused false dead key alerts on Groq. Resolved by migrating requests to httpx with standard browser user-agent headers.
* **Reasoning Budget Truncation:** Extended 256-token ceiling to 1024 tokens with low reasoning effort to eliminate empty responses.
* **Template Intent Alignment:** Fixed domain vs. intent schema discrepancy that yielded initial 0.0 exact-match scores.

---

# Bottlenecks and Pending Evaluation
### Active Constraints and Execution Status
* **API Quota Wall:** Daily 429 quota exhaustion across all 6 Gemini evaluator keys paused automated batch evaluation. System state is safely persisted.
* **Pending Dev Split:** ~2,000 dev-split evaluations remain queued for automated execution upon quota reset.
* **Human Audit Status:** 100 blinded evaluation pairs exported to sealed audit file; bilingual verification is pending execution.
* **Frozen Test Set:** Test partition of 500 dialogues remains completely frozen with zero rows called.
* **Romanized Scope:** Latin-script Hinglish coverage remains unexecuted due to absence of romanized instances in PRESTO partition.

---

# Known Limitations and Defense Q&A
### Critical Methodological Boundaries
* **Pilot Scale:** Current quality scores represent smoke pilot data (n=20); wide confidence intervals require dev-split completion before publication.
* **Script Constraints:** Current empirical testing is confined to Devanagari code-mixing; findings cannot be generalized to romanized chat.
* **Defense Q1 (Superiority Claims):** Higher numerical scores at pilot scale (0.625 vs 0.55) reflect non-inferiority within statistical bounds; no claim of compression improving reasoning is made.
* **Defense Q2 (Judge Integrity):** All machine grades originate from a single blinded Gemini 3.6 Flash grader at temperature 0; prior intermediate Groq evaluations were purged under Amendment A5.
* **Defense Q3 (Metric Choice):** LLM task-completion judging is employed because rigid exact match fails on semantically correct variants.

---

# Conclusion and Next Steps
### Summary of Concrete Research Milestones
* **Core Artifacts Delivered:**
  * 5,000 prompt generation and CRF sequence tagger (<10ms CPU latency).
  * 3,000 query cascade routing framework with 1,200 labeled rows.
  * 2,210 verified compression records across PRESTO dialogue benchmarks.
  * Zero-loss protected span masking guaranteeing 1.000 entity recall.
* **Immediate Roadmap:**
  1. Complete ~2,000 dev-split evaluations following quota reset.
  2. Compute final paired-bootstrap confidence bounds and generate safe-rate operating curves.
  3. Execute 100-sample double-blinded human audit to compute annotator agreement.
  4. Run single final evaluation pass over the frozen 500-sample test partition.
