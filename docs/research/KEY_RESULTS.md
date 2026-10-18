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

### A2. Equal-budget check (the fair comparison)

Guarded compresses less than plain at the same keep-rate, so compare at
matched prompt tokens (linear interpolation on plain's rate curve):
- **All questions:** guarded ≈ plain at equal tokens (EN −1.8 / −0.9 pts;
  HI −0.8 to +3.2). Most of the "halves the loss" effect above is guarded
  compressing less. This agrees with CAVEWOMAN (2606.24083): degradation is
  driven by compression rate more than by method.
- **Questions that contain a negation (EN, n = 514):** guarded wins at equal
  tokens — at ~0.76 kept: guarded −9.7 [−14.0, −5.1] vs plain −17.1
  [−22.4, −12.3] (+7.4 pts, CIs disjoint); at ~0.85 kept: −3.9 vs −9.7
  (+5.8 pts). HI has only 27 negated questions — too few to conclude.
- So the guards matter exactly where they should (negated questions) and are
  neutral elsewhere. A negation-heavy evaluation set is the right next test.

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

## D. Negation stress test: CondaQA (answer level, Qwen2.5-3B)

CondaQA test split (Ravichander et al. 2022): 1,857 questions whose answer depends
on a negation cue in the passage (477 lexical "not/never", 1,380 affixal "un-/-less"/other).
Only the passage is compressed. Source: `condaqa.py grade` on `kaggle/answers.jsonl`
(18,530 answers; 6.5% unparsed, counted wrong). Base accuracy is low (40.0%), so the
3B model is a weak probe; stronger-model runs are in progress (`data/bench/api/`).

| Method | kept | cue dropped | Δ acc (all) | Δ (lexical cues) |
|---|---|---|---|---|
| filler pruning | 1.00 | 0% | 0.0 | 0.0 |
| stopwords, unsafe (2609.13154 warning case) | 0.70 | 15.7% | −6.9 | −10.3 |
| stopwords, negation-safe | 0.71 | 3.9% | −4.0 | −5.7 |
| LLMLingua-2 @0.7 / guarded / guarded+affix | 0.68 | 13.0 / 8.7 / 5.0% | −4.2 / −4.5 / −3.3 | −5.2 / −3.8 / −2.5 (n.s.) |
| LLMLingua-2 @0.5 / guarded / guarded+affix | 0.49 | 37.7 / 28.6 / 13.9% | −10.1 / −10.5 / −9.2 | −13.0 / −10.1 / −8.6 |

Paired method-vs-method (exact McNemar):
- Negation-safe vs unsafe stopword removal: +2.9 pts overall (p<0.001), +4.6 on lexical-cue
  questions (p=0.004) — first answer-level confirmation of 2609.13154's design choice.
- Affix guard vs negation-word guard: +1.2 pts at both rates (p=0.017 @0.5, p=0.004 @0.7).
- Affix guard vs plain LLMLingua-2: +4.4 pts on lexical-cue questions @0.5 (p=0.019); overall +0.8–0.9 (n.s.).
- Rate still dominates: at 0.5 every LLMLingua-2 variant loses 9–10 pts.
