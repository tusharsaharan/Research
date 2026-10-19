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

## E. Output length under compression (Qwen2.5-3B, all 4,069 gold items)

Source: `output_length.py` -> `output_length_report.json` (paired, 95% bootstrap CI).
- English: compressed prompts get *shorter* answers (output ×0.79–0.93), so total
  tokens fall 8–28%. Part is a layout effect: filler pruning joins option lines and
  the model answers more tersely (output ×0.84 at input ×0.99; checked on examples).
- Hinglish: LLMLingua-2 / guarded prompts get *longer* answers (output ×1.05–1.08,
  CIs above 1), eating most of the saving: guarded@0.7 keeps 0.81 of input but 0.96
  of total tokens. Output expansion (cf. 2603.23527) appears only for code-mixed input.

## F. Joint certified compress-or-route (pair 2, 1,000 re-splits, δ = 0.10)

Source: `joint_certify.py` -> `joint_certify_report.json`. Configuration = (compression
method for the cheap path, routing threshold); LTT: fixed sequence over thresholds,
Bonferroni over 11 methods, cheapest certified config chosen on calibration. Variant B
picks the method on the disjoint scorer_train split and certifies only that one.

| Policy (per-language) | EN α=.05 / .10 / .20 saving (violation) | HI α=.05 / .10 / .20 saving (violation) |
|---|---|---|
| routing only | 13.0 / 24.3 / 46.0% (≤6.3%) | 2.9 / 9.1 / 23.7% (≤7.7%) |
| joint, LTT over methods | 9.4 / 21.0 / 42.1% (≤4.1%) | 1.5 / 6.2 / 17.7% (≤2.2%) |
| joint, method picked on train split | 13.0 / 24.3 / 40.7% (≤7.2%) | 2.9 / 9.1 / 23.7% (≤7.7%) |

- All per-language policies hold the guarantee (violation ≤ 10%); one shared threshold
  violates it again (EN up to 64.7%, HI 41.8%).
- **Under a certified quality constraint, compression does not pay.** The joint search
  picks only mild methods (filler pruning for EN; none/CRF for HI), never LLMLingua-2
  below 0.8, and its multiplicity correction makes it slightly *worse* than routing alone.
  Selection on the train split picks "no compression" in 5 of 6 cases. Savings come from routing.
- Caveat: one cheap model (3B), cheap path priced at gpt-oss-20b list rates as a stand-in.

## G. What actually predicts meaning loss? (Qwen2.5-3B answers as ground truth)

Source: `meaning_signals.py` -> `meaning_signals_report.json` (47,450 original/compressed pairs).
- **Noise floor.** Meaning-preserving edits (filler pruning) still change the 3B model's
  final answer in 27% (EN) / 29% (HI) of edited prompts, with breaks ≈ fixes
  (9.7 / 9.6% EN; 6.6 / 7.2% HI). "Answer changed" is mostly churn for a small model;
  the meaningful quantity is breaks − fixes (what all accuracy deltas above report).
- **No cheap signal predicts damage well.** AUROC for "compression broke a correct answer":
  share of words kept 0.758 (EN) / 0.687 (HI); multilingual embedding cosine 0.744 / 0.670;
  a learned combination of 25 signals (fit on scorer_train, scored on cert items) 0.760 / 0.670.
  Number / negation / option retention alone: 0.50–0.59. Embedding similarity adds nothing
  beyond "how much was deleted".
- **Hinglish fragility is dose, not word class.** Logistic model of breaks on per-class
  deletion shares + amount deleted (bootstrap CIs over items): deleting Hindi case markers
  (−0.20 [−0.39, −0.01] log-odds/SD) and auxiliaries (−0.20 [−0.35, −0.07]) is *less* harmful
  than deleting other words; the amount deleted dominates and hurts Hinglish twice as much
  as English (+1.45 [0.90, 2.10] vs +0.69 [0.55, 0.86] per SD). (Our hypothesis that Hindi
  grammar words carry the meaning was not supported.)

## H. Correction: `tokopt` changed words (withdrawn)

All 63 respellings learned by `tokopt` replace a word with a different word (single-annotator
check; list in COMPRESSION_STUDY.md correction): e.g. *kiya→kya*, *abhi→bhi*, *apni→pani*,
*khel→kal*, *wahan→when*. The target was the cheapest o200k spelling, which is often an
English word. This explains section A's CRF+tokopt Hinglish loss (−9.3 vs −1.1 English).
`tokopt.py --strict` (variant_form + distributional check on 200k Hinglish-Everyday-
Conversations lines) leaves 2 merges: tokenizer-driven respelling gives no safe saving here.

## I. Certified meaning-gated compression

Source: `gated_compress.py` -> `gated_compress_report.json` (cert items, 500 re-splits, δ=0.10).
Per prompt, pick the most compressed version whose risk score ≤ λ; λ certified so that the
accuracy drop ≤ α (Clopper–Pearson on breaks and fixes separately, fixed-sequence LTT).
- **Headroom exists:** choosing per prompt the most compressed version that does not lose the
  answer (oracle) saves 29.6% (EN) / 28.6% (HI) of prompt tokens with no accuracy loss.
- **Cheap gates cannot reach it:** at α = 5 points the best certified gate saves 4.4% (EN,
  similarity gate) and ~0% (HI); one fixed method certified the same way saves 1.7% (EN).
  Guarantee holds (violation ≤ 1.6% of re-splits vs 10% allowed).
- So the bottleneck is a per-prompt meaning check, not the compressor.

## J. Translate-then-send: upper bound (cf. 2606.03618)

Source: `translate_back.py eval` -> `mt_report.json` (oracle block). The 578 Hinglish items
are translations of known English questions, so the English original is a perfect translation:
the 3B model scores **85.1% (English) vs 63.5% (Hinglish)** on the same items (155 vs 30
discordant, p = 1.6e-21) with 14% fewer prompt tokens (Qwen template) and equal output length.
The realistic version (small local translator) is in progress.

## K. Pragmatic meaning on human Hinglish chat (pilot)

Source: `label_invariance.py` -> `labels/report.json`. 71 human messages (Yugrathee28,
strong-signal labels, ≥12 words), Gemini 3.5 Flash-Lite reads intent + emotion; measure =
same labels as for the original message (gold labels are automatic, so not used).

| Version | kept | both labels same (texts actually changed) |
|---|---|---|
| same message asked again (noise ceiling) | 1.00 | 90.1% |
| filler pruning | 0.98 | 78.1% (n = 32) |
| CRF | 0.94 | 68.4% |
| negation-safe stopwords | 0.91 | 63.9% |
| LLMLingua-2 @0.7 plain / guarded | 0.68 | 54.9% / 57.8% |

Even mild deletion changes the perceived intent/emotion of chat messages 20+ points below the
noise ceiling. n = 71: a pilot; needs a larger run.
