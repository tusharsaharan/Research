# Academic Research Brief: Token Optimisation for Hindi-English LLM Inference
## Project: Code-Mixed LLM Gateway
**Authors:** Tushar Saharan, Shivam Kumar, Sahil Gupta  
**Faculty Guide:** Dr. Sonali Agrawal  
**Institutional Record:** 2026-09-28  

---

### 1. Executive Summary & Problem Formulation
Large Language Model (LLM) serving costs scale directly with input prompt length and chosen model tier. While established prompt-compression techniques (e.g., the LLMLingua family) demonstrate substantial token reductions at negligible semantic loss, their empirical validation is restricted almost exclusively to standard English academic datasets (GSM8K, MeetingBank, ShareGPT, LongBench). 

Furthermore, subword tokenizers (e.g., Llama, GPT, Gemma) exhibit severe linguistic asymmetry: due to subword fragmentation, equivalent semantic content in Hindi-English code-mixed language consumes up to 15x more tokens than pure English (Petrov et al., NeurIPS 2023). This introduces an implicit economic penalty on multilingual and code-mixed users.

This project investigates:
1. Does prompt compression transfer to Hindi-English code-mixed task dialogue without catastrophic quality degradation?
2. Can lightweight sequence tagging (CRF + phonetic normalization) compress informal romanized transliterations on standard CPUs in <10ms?
3. Does deterministic protected-span masking eliminate entity mangling, and does cascade routing optimize provider cost?

---

### 2. Research Questions and Pre-Registered Statistical Protocol
Pre-registered in `docs/research/DECISIONS.md` prior to full-scale evaluation:
* **RQ1 (Transferability):** At what achieved compression ratio does code-mixed task success degrade relative to the uncompressed prompt?
* **RQ2 (Economics):** What input-token and dollar savings follow at each level for a declared provider and pricing schedule?
* **RQ3 (Failure Modes):** Are losses concentrated in named entities, digits, code snippets, or code-mixed phrases?
* **RQ4 (Recovery):** Does regex protected-span masking restore quality at identical compression rates?

**Statistical Standards:**
* Non-inferiority margin: -0.05 absolute on variant-minus-reference task score.
* Bound: Lower 95% dialogue-clustered paired-bootstrap confidence interval over 10,000 replicates (seed 20260926).
* Protected span recall threshold: 0.995 lower confidence bound.
* Primary independent variable: Achieved kept token ratio, never requested compression target.

---

### 3. System Architecture & Compressor Engineering
The serving system encompasses an OpenAI-compatible 12-module gateway (M1–M12) and a 5-stage CPU-efficient prompt compressor:

1. **Phonetic Normalization:** Consonant-skeleton hashing collapses informal Hinglish transliteration spelling entropy (e.g., "kyu", "kyun", "q" mapped to invariant root representations).
2. **Deterministic Heuristic Filtering:** Pre-tagging routines strip conversational greetings, collapse character reduplications (e.g., "heyyy" -> "hey"), and prune safe filler tokens.
3. **Regex Safety Gates:** Force-preservation guards protect numeric sequences, monetary values, timestamps, emails, and URLs prior to sequence tagging.
4. **Linear-Chain CRF Sequence Tagger:** Custom CRF tagger with 25+ linguistic, morphological, and orthographic token features. Executes in <10ms on CPU without GPU overhead.
5. **Gateway Modules (M1–M12):** Tokenizer benchmarking (M1), trained LLMLingua-2 baseline (M2), conformal calibrator with Hoeffding bounds (M3), cascade router (M4), OpenAI-compatible API (M5), Telegram/SQLite bridge (M6), evaluation suite (M7), monitoring dashboard (M8), reasoning budget estimator (M9), distillation scaffold (M10), ECE calibration (M11), and semantic similarity with Hinglish gloss (M12).

---

### 4. Cascade Routing Track
* **Dataset:** 3,000 synthetic code-mixed queries generated across distinct complexity bands.
* **Tier Labels:** 1,200 Groq labels categorizing cheap (20B) vs. premium (120B) model necessity.
* **Splits:** 794 training, 203 calibration, 203 test under seed 42 (`backend/data/router_track/splits.json`).
* **Judge Ablations:** 1,449 Judge A ablation evaluations.
* **Rewrite Comparison:** At n=50, structured rewrite achieved 0.383 fidelity at 0.813 token ratio vs. heuristic 0.405 fidelity at 0.954 token ratio (0.34 rewrite win-rate).

---

### 5. Empirical Token Study: Pilot Scale Results
* **Benchmark:** PRESTO v1 hi-IN partition (5,804 human task dialogue rows, CC BY 4.0 license, SHA-256 verified). Audit confirms 397 mixed Devanagari-English rows, 103 pure Devanagari rows, and 0 romanized rows.
* **Compression Volume:** 2,210 total dialogue rows compressed (260 smoke, 1,950 dev) with 100% success rate and 0 fallback triggers.
* **Proved Entity Recovery:** Across 680 rows, the raw classifier (A1) achieves only 0.80 (smoke) / 0.69 (dev) entity recall, mangling entities into token fragments. Protected-span masking (A2) achieves exactly 1.000 recall via byte-for-byte reinjection with identical compression.
* **Smoke Quality Pilot (n=20 Dialogues, 114 Valid Blinded Grades, Gemini 3.6 Flash):**
  * Uncompressed A0: Mean score 0.55
  * LLMLingua-2 A1 @0.30: Mean score 0.625 (Delta +0.075, 95% CI [-0.075, +0.225])
  * LLMLingua-2 A1 @0.50: Mean score 0.600 (Delta +0.050, 95% CI [-0.125, +0.225])
  * LLMLingua-2 A1 @0.70: Mean score 0.525 (Delta -0.025, 95% CI [-0.225, +0.150])
  * Heuristic A3: Collapses to 0.00 across all rates.
  * *Interpretation:* All LLMLingua-2 confidence intervals cross zero and lie within the -0.05 margin, establishing a statistical tie at pilot scale. No claim of compression improving reasoning is made.
* **Metered Serving Cost:** 572,318 input tokens and 260,340 output tokens totaled $0.2421 at list prices ($0.00 billed via free tier).

---

### 6. Debugging War Log: Engineering Failures & Fixes
1. *Simulated Baseline:* Replaced mock heuristic discount with official local `llmlingua` v0.2.2 and multilingual checkpoint.
2. *Entity Mangling:* Raw classifier fragmented emails and codes; resolved via regex masking and digit reservation.
3. *Context Filter Desync:* Disabled context filtering after observing 4 input segments yielding 3 output segments with index shifts.
4. *Cloudflare 1010 Block:* Migrated scripting requests from standard requests to `httpx` with browser user-agent headers.
5. *Reasoning Budget Cap:* Increased 256-token ceiling to 1024 tokens to prevent reasoning models from exhausting token budgets before emitting answers.
6. *Template Schema Alignment:* Corrected domain vs. intent prompt discrepancies that produced false 0.0 exact-match scores.

---

### 7. Constraints, Blocked Items & Limitations
* **Active Quota Wall:** Daily 429 quota exhaustion across all 6 Gemini evaluator keys paused automated batch evaluation; ~2,000 dev-split evaluations remain queued.
* **Human Audit:** 100 blinded evaluation pairs exported to sealed audit file; bilingual human annotator verification is pending.
* **Frozen Test Set:** 500-sample test partition remains frozen with zero rows called.
* **Romanized Coverage:** PRESTO hi-IN partition lacks romanized Latin-script Hinglish; findings cannot be generalized to romanized campus chat.
