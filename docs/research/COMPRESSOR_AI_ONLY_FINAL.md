# Final AI-only Hinglish compressor report

Finalized 16 November 2026 under the owner's instruction to proceed without human review.
The implementation, AI annotation, fixed GPU experiments, analysis, checkpoint, and evidence packaging are complete for this exploratory scope. No human action is required to use these deliverables.

## Main finding

Neither tested student demonstrates better answer quality than the strong compression baselines. Neither establishes an end-to-end speedup. This is a completed negative development study, not an unfinished request for manual labels. A better-compressor or fresh-test superiority claim is unsupported.

## Data and working labels

The 500-row AI review is the accepted working annotation file. It changes 286 rows relative to the earlier AI pass. All original text, source gold, raw GPU responses and AI adjudications remain available. Human columns remain unfilled because no human review occurred.
The 183 development questions belong to 97 exact source-passage groups, separate from the 717 training questions / 391 groups. Both partitions have historical exposure; this is not a fresh source-family-audited test.

## Native Mistral results

Every method retains all 183 questions. Invalid and capped answers count incorrect. Original/no-context are common controls, not independently replicated budget runs.

| Method | Accuracy | Context kept | Full prompt kept | Output tokens mean | Compression + generation seconds | Invalid |
|---|---:|---:|---:|---:|---:|---:|
| original | 48.09% | 100.00% | 100.00% | 11.15 | 0.3586 | 0 |
| no_context | 27.32% | 0.00% | 36.53% | 19.20 | 0.5972 | 4 |
| teacher_prefix@0.5 | 47.54% | 45.54% | 65.23% | 13.86 | 0.8856 | 1 |
| teacher_prefix@0.33 | 48.09% | 28.84% | 54.57% | 13.34 | 0.8682 | 1 |
| teacher_atomic@0.5 | 47.54% | 45.54% | 65.23% | 13.86 | 0.8856 | 1 |
| teacher_atomic@0.33 | 47.54% | 28.42% | 54.31% | 14.01 | 0.8885 | 1 |
| student_atomic@0.5 | 40.98% | 46.05% | 65.56% | 12.67 | 0.4018 | 0 |
| student_atomic@0.33 | 42.08% | 28.34% | 54.26% | 14.74 | 0.4642 | 1 |
| bm25_atomic@0.5 | 41.53% | 45.65% | 65.30% | 12.39 | 0.3928 | 0 |
| bm25_atomic@0.33 | 40.98% | 28.06% | 54.08% | 14.39 | 0.4531 | 1 |
| shuffled@0.5 | 38.80% | 45.29% | 65.07% | 11.99 | 0.3807 | 0 |
| shuffled@0.33 | 32.79% | 28.34% | 54.26% | 13.87 | 0.4370 | 1 |
| llml2_strict@0.5 | 42.08% | 47.05% | 66.20% | 13.43 | 0.4382 | 0 |
| llml2_strict@0.33 | 36.61% | 30.21% | 55.44% | 15.11 | 0.4773 | 1 |
| xprovence_strict@0.5 | 42.08% | 39.10% | 61.13% | 13.05 | 0.4225 | 0 |
| xprovence_strict@0.33 | 42.08% | 28.88% | 54.60% | 12.94 | 0.4185 | 0 |
| student_neural@0.5 | 37.16% | 45.95% | 65.50% | 12.88 | 0.4150 | 0 |
| student_neural@0.33 | 38.80% | 28.40% | 54.30% | 14.22 | 0.4552 | 2 |

Timings are local component accounting, including exact-reply reuse and historical teacher rank cost. They are not deployment throughput guarantees. Model setup is separate.

## Qwen reference-budget results

These use Qwen2.5 reference-token text budgets, not verified native Qwen3.5 serving caps. The 2,196 records include 1,586 archive reuses, 31 within-run reuses and 579 new calls.

| Method | Accuracy | Invalid |
|---|---:|---:|
| qwen3.5:4b|original | 71.04% | 0 |
| qwen3.5:4b|no_context | 37.16% | 0 |
| qwen3.5:4b|teacher_prefix@0.5 | 66.67% | 0 |
| qwen3.5:4b|teacher_prefix@0.33 | 60.11% | 0 |
| qwen3.5:4b|teacher_atomic@0.5 | 66.67% | 0 |
| qwen3.5:4b|teacher_atomic@0.33 | 59.56% | 0 |
| qwen3.5:4b|student_atomic@0.5 | 53.01% | 0 |
| qwen3.5:4b|student_atomic@0.33 | 51.91% | 0 |
| qwen3.5:4b|bm25_atomic@0.5 | 55.19% | 0 |
| qwen3.5:4b|bm25_atomic@0.33 | 53.01% | 0 |
| qwen3.5:4b|shuffled@0.5 | 49.73% | 0 |
| qwen3.5:4b|shuffled@0.33 | 46.99% | 0 |

## All native paired comparisons

Intervals are paired passage-cluster bootstrap 95% intervals, exploratory and unadjusted. Holm p-values adjust across these 24 comparisons, not all historical project explorations.

| Candidate | Baseline | Difference, percentage points | 95% interval | Holm p |
|---|---|---:|---|---:|
| student_atomic@0.5 | bm25_atomic@0.5 | -0.55 | [-3.80, 2.72] | 1.0000 |
| student_atomic@0.5 | llml2_strict@0.5 | -1.09 | [-7.78, 5.95] | 1.0000 |
| student_atomic@0.5 | xprovence_strict@0.5 | -1.09 | [-7.87, 5.62] | 1.0000 |
| teacher_atomic@0.5 | bm25_atomic@0.5 | 6.01 | [0.00, 11.96] | 0.9621 |
| teacher_atomic@0.5 | llml2_strict@0.5 | 5.46 | [-1.08, 12.09] | 1.0000 |
| teacher_atomic@0.5 | xprovence_strict@0.5 | 5.46 | [-1.10, 12.23] | 1.0000 |
| teacher_prefix@0.5 | bm25_atomic@0.5 | 6.01 | [0.00, 11.96] | 0.9621 |
| teacher_prefix@0.5 | llml2_strict@0.5 | 5.46 | [-1.08, 12.09] | 1.0000 |
| teacher_prefix@0.5 | xprovence_strict@0.5 | 5.46 | [-1.10, 12.23] | 1.0000 |
| student_neural@0.5 | bm25_atomic@0.5 | -4.37 | [-10.06, 1.12] | 1.0000 |
| student_neural@0.5 | llml2_strict@0.5 | -4.92 | [-10.81, 1.08] | 1.0000 |
| student_neural@0.5 | xprovence_strict@0.5 | -4.92 | [-11.11, 1.61] | 1.0000 |
| student_atomic@0.33 | bm25_atomic@0.33 | 1.09 | [-2.12, 4.30] | 1.0000 |
| student_atomic@0.33 | llml2_strict@0.33 | 5.46 | [-2.16, 12.99] | 1.0000 |
| student_atomic@0.33 | xprovence_strict@0.33 | 0.00 | [-6.78, 6.74] | 1.0000 |
| teacher_atomic@0.33 | bm25_atomic@0.33 | 6.56 | [0.54, 12.64] | 0.8173 |
| teacher_atomic@0.33 | llml2_strict@0.33 | 10.93 | [2.79, 18.72] | 0.1837 |
| teacher_atomic@0.33 | xprovence_strict@0.33 | 5.46 | [-2.22, 13.56] | 1.0000 |
| teacher_prefix@0.33 | bm25_atomic@0.33 | 7.10 | [1.08, 13.26] | 0.6051 |
| teacher_prefix@0.33 | llml2_strict@0.33 | 11.48 | [3.31, 19.34] | 0.1384 |
| teacher_prefix@0.33 | xprovence_strict@0.33 | 6.01 | [-1.65, 13.97] | 1.0000 |
| student_neural@0.33 | bm25_atomic@0.33 | -2.19 | [-7.53, 2.79] | 1.0000 |
| student_neural@0.33 | llml2_strict@0.33 | 2.19 | [-5.38, 9.66] | 1.0000 |
| student_neural@0.33 | xprovence_strict@0.33 | -3.28 | [-10.00, 3.72] | 1.0000 |

## What was completed

- All 500 AI labels, with 497 valid initial GPU reviews and 30 source-based AI adjudications, including three invalid initial reviews.
- Ordinal teacher training data, six-weight lexical student, and fixed two-epoch neural student; safely saved and reloaded neural checkpoint.
- Qwen development comparisons and independent-family native Mistral comparisons, BM25, LLMLingua-2, XProvence and negative controls.
- Exact native token and prompt replay: 3,294 verified prompts, zero native cap violations. Twelve capped and two other invalid answers remain incorrect.
- Local replay of all reported metrics and 30 contrasts, 48 targeted checks covered, figures and raw evidence archive.
- Failed downloads/setup attempts and negative stress-repair findings retained; no performance-driven retry or serving promotion.

## Scope closure

No human review, inter-annotator agreement, newly human-validated corpus, or sealed confirmatory run is represented as performed. The owner has removed human review from the current workflow. Those tasks are outside this AI-only delivery, rather than pending work assigned to the owner.
Future method improvements or a separate confirmatory study may use a new protocol and new data. This report does not require either to close the current delivery, and does not claim that the original superiority objective was achieved.

## Deliverables

- Working labels: `docs/annotation/belebele_cm_ai_reviewed.csv` and adjacent `.manifest.json`.
- Workbook: `outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/belebele_ai_review_corrected.xlsx`.
- Machine-readable closeout: `docs/research/COMPRESSOR_AI_ONLY_FINAL.json`.
- Checkpoint/raw neural outputs: `backend/data/bench/neural_student_20261116/results/`.
- Figures: `backend/data/bench/compressor_figures_20261116/`.
- Complete dated methods/reproduction record: `docs/research/COMPRESSOR_STATUS_20261116.md`.
- Final internal archive: `outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip`.

Upstream data/model licenses still apply. The archive is internal; no public upload or Git push is part of this delivery. The separate router study is unchanged.
