# Hinglish compressor: completed development evaluation

Verified 75,600 answer records on 900 questions / 488 source passages; 10,000 stress texts / 80,000 stress outputs. Wall time 4.05 hours.
All saved data hashes, QA scores, duplicate-prompt consistency, reference token counts and stress counters checked.

Candidate: Qwen3.6-35B question-only evidence ranking with original-span packing.

| Answer model | Context target | Candidate % | BM25 % | LLML2 % | Delta vs BM25, pp [95% CI] |
|---|---:|---:|---:|---:|---|
| qwen3.5:4b | 0.5 | 63.44 | 58.67 | 60.44 | +4.78 [+1.79, +7.75] |
| qwen3.5:4b | 0.33 | 59.33 | 52.56 | 50.67 | +6.78 [+3.67, +9.94] |
| qwen3.5:4b | 0.75 | 66.56 | 60.44 | 66.00 | +6.11 [+3.59, +8.64] |
| qwen3.5:4b | 0.25 | 54.67 | 49.89 | 49.56 | +4.78 [+1.45, +8.14] |
| qwen3.6:35b | 0.5 | 71.78 | 65.78 | 71.22 | +6.00 [+3.30, +8.81] |
| qwen3.6:35b | 0.33 | 65.78 | 58.00 | 62.44 | +7.78 [+4.55, +10.96] |
| qwen3.6:35b | 0.75 | 76.33 | 71.44 | 76.56 | +4.89 [+2.43, +7.42] |
| qwen3.6:35b | 0.25 | 63.00 | 54.11 | 60.22 | +8.89 [+5.33, +12.39] |
| qwen3.8:27b | 0.5 | 75.00 | 68.89 | 72.67 | +6.11 [+3.17, +9.05] |
| qwen3.8:27b | 0.33 | 71.78 | 63.67 | 64.67 | +8.11 [+5.09, +11.23] |
| qwen3.8:27b | 0.75 | 79.33 | 75.11 | 79.89 | +4.22 [+1.77, +6.78] |
| qwen3.8:27b | 0.25 | 66.00 | 58.22 | 61.22 | +7.78 [+4.48, +11.09] |
| qwen3.5:9b | 0.5 | 68.11 | 60.78 | 62.22 | +7.33 [+4.34, +10.35] |
| qwen3.5:9b | 0.33 | 63.00 | 56.11 | 56.67 | +6.89 [+3.70, +10.11] |
| qwen3.5:9b | 0.75 | 70.56 | 65.44 | 70.22 | +5.11 [+2.60, +7.72] |
| qwen3.5:9b | 0.25 | 58.56 | 52.89 | 52.00 | +5.67 [+2.36, +9.08] |

Intervals are paired passage-clustered, exploratory and unadjusted for multiple comparisons.
At 0.50 and 0.33, BM25 intervals exclude zero for all four answer models, including the 666-question subset outside current selection sources. That subset still has historical exposure. Superiority over LLMLingua-2 is less uniform: several corresponding intervals include zero.

## Efficiency and failure limits

| Model | Original generation, s | Candidate compression + generation at 0.50, s |
|---|---:|---:|
| qwen3.5:4b | 0.137 | 0.541 |
| qwen3.6:35b | 0.224 | 0.619 |
| qwen3.8:27b | 0.479 | 0.848 |
| qwen3.5:9b | 0.151 | 0.552 |

At target 0.5, mean actual context kept is 44.8% and full prompt kept is 68.8%.

At target 0.33, mean actual context kept is 28.3% and full prompt kept is 58.7%.

Component sums above are observed timings, not a controlled deployment latency benchmark. The ranker overhead exceeds measured answer-generation savings here; do not claim end-to-end speedup. Invalid outputs remain failures in denominators; raw output-cap errors are preserved.

## Stress checks and manual review

Budget compliance does not establish meaning preservation. Report original Roman text and derived romanizations separately. Literal negation/number deletion is a surface diagnostic, not a semantic error rate.

original_roman_hindi_heuristic: 2178 texts; at 0.33, 27 empty, 60 nonempty punctuation-only, 1406 prefix-clipped; 1059/1321 tracked literal occurrences dropped.

derived_romanization_annotator1: 7822 texts; at 0.33, 0 empty, 0 nonempty punctuation-only, 7049 prefix-clipped; 2636/3660 tracked literal occurrences dropped.

Inspected QA wins bb-8, bb-11 and bb-21: bb-11 retains the daily nest-change evidence; bb-8 answers correctly although the selected text omits the tide condition, showing that accuracy alone cannot prove evidence preservation. Stress examples in verified_review.json drop a date/number or negation, and one emits only punctuation without the clipping flag.

## Paper decision

Promising development result, not a confirmed superiority or losslessness claim. Keep the selector opt-in. Next priorities: repair lossy span/fallback behaviour and test a cheaper distilled scorer; then evaluate a frozen method on fresh source-disjoint human-validated Hinglish QA with an independent model family. Establish novelty against current query-aware retrieval/compression work before drafting a contribution claim.

Evidence: verified_review.json, report.json, stress_report.json and their fingerprinted raw files.
