# Key results (2026-10-18) — every number from a committed script + data file

## A. Answer-level effect of compression (the core test)

Qwen2.5-3B-Instruct answered every gold question (GSM8K, ARC-Challenge, MMLU;
English 3,491, Hinglish 578) in its original and compressed forms on a Kaggle
GPU (42,960 answers so far). Δ = accuracy change vs the original prompt,
paired per question; p = exact McNemar. Source: `backend/data/bench/kaggle/answer_report.json`
(`kaggle_import.py`).

| Lang | Method | Accuracy | Δ pts | p |
|---|---|---|---|---|
| EN | original | 72.4% | — | — |
| EN | heuristic (filler pruning) | — | +0.3 | 0.73 |
| EN | CRF + tokopt (ours, mild) | 71.3% | −1.1 | 0.13 (n.s.) |
| EN | plain LLMLingua-2 @0.8 | 60.7% | −11.6 | <0.001 |
| EN | **guarded @0.8** | 67.9% | **−4.4** | <0.001 |
| EN | plain LLMLingua-2 @0.7 | 50.2% | −22.2 | <0.001 |
| EN | **guarded @0.7** | 62.5% | **−9.8** | <0.001 |
| EN | plain LLMLingua-2 @0.5 | 23.9% | −48.4 | <0.001 |
| EN | **guarded @0.5** | 47.5% | **−24.8** | <0.001 |
| HI | original | 63.5% | — | — |
| HI | heuristic | — | 0.0 | 1.0 |
| HI | CRF + tokopt | 54.1% | −9.3 | <0.001 |
| HI | plain LLMLingua-2 @0.8 | 39.5% | −24.1 | <0.001 |
| HI | guarded @0.8 | 41.9% | −21.6 | <0.001 |
| HI | plain @0.5 / guarded @0.5 | 15.4% / 14.0% | −48.1 / −49.5 | <0.001 |

Findings:
1. **Compression is far more harmful than token or similarity metrics suggest.**
   Even the gentlest LLMLingua-2 setting (keep 0.8) costs 11.6 pts (EN) and
   24.1 pts (HI) of accuracy for a 3B model.
2. **Guards halve the English accuracy loss at the same keep-rate** (−48 → −25 at
   0.5; −22 → −10 at 0.7; −12 → −4 at 0.8). Part of this comes from keeping
   multiple-choice options verbatim (guarded compresses less); at matched prompt
   tokens the gain is smaller and not consistent — report both.
3. **Code-mixed prompts are much more fragile.** Hinglish loses 9.3 pts even
   with mild CRF + tokopt (English: −1.1, n.s.), and guards do not help on
   Hinglish. Practical rule from the data: do not compress code-mixed prompts
   beyond filler pruning (heuristic: 0.0 pts).
4. Token/embedding metrics missed all of this (findings 8 and 10 in
   COMPRESSION_STUDY.md): answer-level evaluation is required.

## B. Language-conditional certified routing (pair 2)

Cheap = Qwen2.5-3B (local GPU), premium = gpt-oss-120b. u = cheap wrong and
premium right. 1,000 random calibration/test re-splits, δ = 0.10.
Source: `backend/data/bench/certify_report_grades_pair2.json` (`certify.py --grades grades_pair2.jsonl`).

- u-rate: **English 12.6%, Hinglish 30.5%** — the cheap model fails code-mixed
  queries 2.4× more often.
- One shared (marginal) threshold **violates the guarantee**: English 39%
  (α=0.05) and 67% (α=0.10) of re-splits; Hinglish 42% (α=0.20). Allowed: 10%.
- Per-language thresholds **hold it for every group and α** (violation ≤ 4.2%),
  saving 27–48% of English cost and 5–45% of Hinglish cost.
- Matches the known-truth simulation (simulate_validity.py): marginal valid on
  average, invalid per language; per-language valid.

## C. Offline compression results (8,000 prompts, see COMPRESSION_STUDY.md)

Negation loss of plain LLMLingua-2 rises 11% → 82% with compression; guards
remove it; adaptive guarded compression gives the same compression with
+2–3 pts similarity; embedding similarity is blind to negation; CRF
task-altering bug found and fixed; negation-safe lexical baseline
(2609.13154 replication + Hinglish) keeps 71.5% of English tokens at 0.95
similarity (answer-level test pending).

## Caveats
- One answering model per pair (3B local; gpt-oss-120b premium); Hinglish
  items are model-translated and not yet human-verified.
- 7,668 of 50,628 compressed prompts still unanswered (low-priority rates);
  the runner continues automatically.
