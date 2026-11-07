# Test Report — Router + Compressor Track (autonomous run)

Date: Sep 2026 · Runner: agent (local, CPU) · Status: blocked on `human_check.csv`

## 1. What was tested

### 1.1 Cascade labeling (1200 queries, Groq free tier)
- Cheap `openai/gpt-oss-20b` vs premium-proxy `openai/gpt-oss-120b` (proxy=true;
  Llama/GPT-4o unavailable on free tier — retired / paid).
- 1200/1200 labeled, 0 transport errors. 6-key rotation pool across 5 accounts.
- Splits frozen (seed 42): train 794 / calib 203 / test 203, stratified by
  code-mix bucket. `DECISION_01` sha `e7b98d5d…`.

### 1.2 Refill (470 empty-sided rows)
- 448 cheap + 125 premium answers came back **empty with high token usage**.
- Root cause: gpt-oss emits hidden reasoning; content field empty when the
  model spends its budget thinking. Fix: `reasoning` field fallback +
  `reasoning_effort=low` (62 → 8 reasoning tokens) + 224-token budget.
- Verified 0 empties after refill.

### 1.3 Grading
- cheap-vs-premium fidelity: median **0.40** (BLEU/fuzzy scale built for
  compression, harsh on cross-model agreement). At bar 0.6 → 7.8% success.
- Finding: the scale punishes **script mismatch** (cheap=Roman, premium=
  Devanagari), not wrongness. Bars (ε, REWRITE_BAR) to be fit to human
  verdicts — currently provisional, flagged in every artifact.

### 1.4 Judge A — importance mining (1449 ablations, 400 queries × 6 variants)
Mean answer-change (Δ) by dropped class:

| Class | Mean Δ | Decision |
|---|---|---|
| Truncation (first 60%) | 0.71 | never truncate — new hard rule |
| Entities/numbers | 0.63 | protected (confirms span design) |
| Negations | 0.60 | protected — new guard the old metric couldn't see |
| Vocatives/aggressive | 0.56 | droppable with kinship guards |
| Lexicon fillers | 0.45 | droppable (lowest measured harm) |

- Per-word attribution was **killed, not shipped**: same words ranked safest
  and riskiest (whole-set confounding). Importance stays class-level.

### 1.5 Rewrite path (the "real" compressor)
- v1 (no length cap): ratio **1.05** — the model *expanded* text. 0/200 accepted.
  Failed honestly, forced the fix.
- v2 (60% word cap + joint selection fidelity−0.3·ratio): ratio **0.81** vs
  heuristic 0.95; answer fidelity 0.383 vs 0.405 (−0.02); win rate 0.34.
- Wired into `Compressor.compress()` (rewrite-first when `use_model`, gated
  on clean reinject + ratio<1.0). Live demo: 5/5 queries rewrote by meaning
  (0.46–0.53 ratios), `Rs. 2,500` preserved.
- Bug found & fixed: `"rewrite"` missing from `CompressResult.method`
  literal silently fell back to `model` (pydantic ValidationError).

### 1.6 Shivam merge (separate repo → main)
- `research/shivam` (token study, PRESTO, m12 semantic, LLMLingua-2) merged as
  `0bcf41f` + resolutions `05963cf`, pushed to `code-mixed-gateway`.
- 4 conflicts, all union-resolved; 1 duplicate `GlossRequest` removed.
- Full backend suite: **179 passed, 6 skipped**; 1 pre-existing failure
  (`test_fixed_sequence_dominates_hoeffding`, byte-identical before/after).
- Ruff 20 → 10 (remaining: friend's files, untouched). Compressor suites:
  **42 passed, 6 skipped** (skips = uninstalled `llmlingua` weights).

## 2. Key findings (for the paper)
1. Tier script-shift: cheap answers Roman, premium answers Devanagari.
2. Cheap-strictly-better cases exist (over-provisioning waste argument).
3. Truncation is the most destructive "compression" (Δ 0.71).
4. Pure drop-lists plateau at ratio ~0.9; rewrite reaches ~0.8 at equal meaning.
5. Free-tier 120B throttling is TPM-driven (reasoning burn), not RPM.

## 3. Blocked / next
- **Blocked**: `human_check.csv` column G (150 rows) → fits ε + REWRITE_BAR.
- Then: re-grade → supervised + bandit → conformal thresholds → one-shot
  eval → wire learned scorer → commit. No further user tasks after the CSV.
