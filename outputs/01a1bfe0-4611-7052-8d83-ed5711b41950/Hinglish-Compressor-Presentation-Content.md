# Hinglish Compressor: Presentation Content and Speaker Notes

**Prepared:** 16 November 2026  
**Format:** Markdown only; no PowerPoint or PDF is created by this delivery.  
**Scope:** the compressor study. The separate router study is not evidence for compressor performance.

## How to use this file

Sections labelled "Slide" contain suggested slide text and speaker notes.
There are 15 suggested main slides, followed by complete result tables and Q&A
for backup. The number of slides is a suggestion, not a requirement.
Keep the qualifications next to the numbers they affect. Use the full tables
in backup slides rather than squeezing every row onto the main slides.

All measured numbers below come from saved project artifacts. Explanations
that were not isolated experimentally are identified as hypotheses.

## The central, defensible statement

We implemented and evaluated question-aware context compression for Roman
Hinglish. Large-model evidence ranking produced higher observed compressed-input
accuracy than the configured baselines in Qwen development experiments. It
still lost accuracy relative to full context and introduced overhead. Two
tested student rankers did not establish the intended quality/efficiency gain.
The independent-family experiment did not establish superiority after the
disclosed multiple-comparison adjustment.

The AI-only implementation and fixed experimental study are complete. The
original goal of demonstrating a better, faster compressor was not achieved.

---

## Slide 1 — Evaluating Context Compression for Roman Hinglish

**On-slide text**

Teacher ranking, student distillation, and measured quality–efficiency tradeoffs

Exploratory AI-only development study · November 2026

**Speaker notes**

"We studied whether selecting question-relevant evidence can reduce Roman
Hinglish input length without losing too much answer quality, and whether a
smaller student can replace a large teacher. We report both observed gains and
the parts that did not meet our objective."

Do not add "state of the art", "lossless", "guaranteed" or "faster" to the title.

## Slide 2 — Research objective and actual outcome

**On-slide text**

| Objective | Observed outcome |
| --- | --- |
| Reduce context tokens | Achieved in the tested compression conditions |
| Improve compressed-input QA over baselines | Higher teacher point estimates; broad superiority not established |
| Retain full-context accuracy | Not consistently achieved |
| Replace the teacher with a cheaper student | Not established by either tested student |
| Demonstrate end-to-end speedup | Not established |
| Produce reproducible implementation and results | Completed within the AI-only exploratory scope |

**Speaker notes**

"Completing the experiment and achieving the performance objective are
different. We completed the first; the combined quality and speed target
remains unmet."

## Slide 3 — Compression pipeline

**On-slide text**

Passage + question → source spans → relevance ranking → token-budgeted packing
→ answer model → accuracy, token and timing analysis

- Teacher ranks source span IDs rather than generating replacement evidence.
- Selected text retains original wording.
- The compressor receives no answer choices or gold answers.
- The answering model receives the question and choices; gold is used for grading.

**Speaker notes**

"Extraction avoids inventing evidence, but it does not guarantee complete
meaning. Removing a negation, a number or one half of a relation can still
change the meaning of the remaining text."

## Slide 4 — Data and experimental scope

**On-slide text**

| Component | Size and interpretation |
| --- | --- |
| Historical full-pool QA | 900 questions / 488 source passages |
| Historical saved answer records | 75,600, including exact-prompt reuse |
| Student training | 717 questions / 391 exact source groups |
| Student development | 183 questions / 97 other exact source groups |
| Independent answer family | Mistral 7B on all 183 development questions |
| AI annotation review | 500 rows; no human review |
| Unlabelled stress study | 10,000 texts / 80,000 outputs; not QA accuracy |

**Visible qualification**

All existing Belebele examples have historical exposure. Source-group separation
between train and development does not make development a fresh test.

**Speaker notes**

"Four Qwen sizes are one model family. Mistral adds one independent family.
Record counts include multiple conditions and response reuse: we did not have
75,600 independent questions or make that many fresh calls in this continuation.
The groups are exact source-passage groups, not fully audited paraphrase families."

## Slide 5 — Methods and comparison boundaries

**On-slide text**

- Large teacher: Qwen3.6-35B source-span ranking.
- Lexical student: a learned ranker using six relevance/text features.
- Neural student: XLM-R encoder with its last block and ranking head trained.
- Baselines: BM25, LLMLingua-2 large and XProvence.
- Controls: full context, no context and shuffled context.

**Important configuration disclosure**

In the native experiment, the configured LLMLingua-2 call compresses the passage
without receiving the question. Our rankers and XProvence receive the question.
LLMLingua-2 and XProvence outputs then undergo explicit word-boundary clipping
if they exceed the Mistral native-token cap. XProvence uses threshold .3 with
no forced first sentence. These are the pipelines we evaluated, not a
reproduction of either paper's published benchmark setup.

**Speaker notes**

"We compare these configured systems under a context-token cap. Their
information inputs, inference costs and achieved retained lengths differ.
The results do not isolate a uniquely Hinglish algorithmic advantage."

## Slide 6 — Historical teacher results on 900 questions

**On-slide table: accuracy at the 50% context-budget target**

| Answer model | Full context | Strict BM25 | LLMLingua-2 large | Teacher |
| --- | --- | --- | --- | --- |
| Qwen 4B | 69.11% | 58.67% | 60.44% | 63.44% |
| Qwen 35B | 79.56% | 65.78% | 71.22% | 71.78% |
| Qwen 27B | 83.11% | 68.89% | 72.67% | 75.00% |
| Qwen 9B | 74.22% | 60.78% | 62.22% | 68.11% |

**Speaker notes**

"The teacher produced higher observed accuracy than BM25 in all four Qwen
sizes, by approximately 4.8–7.3 percentage points. It also had higher point
estimates than our LLMLingua-2 configuration. Full context remained more accurate."

**Visible qualification:** exposed development; one answer-model family;
Qwen2.5 reference-token budgets. Do not describe this as having surpassed
LLMLingua-2 generally or the Microsoft research paper.

**Evidence:** [verified_review.json](C:/Research/backend/data/bench/restored_audit_20261116/verified_review.json).

## Slide 7 — Context savings and full-prompt savings

**On-slide text**

Historical primary condition, first Qwen answer model, approximately:

- Context kept: 44.8%; context reduction: 55.2%.
- Full prompt kept: 68.8%; full-prompt reduction: 31.2%.
- The question, options and instructions remain outside the context-only cap.

**Speaker notes**

"These are different denominators. Removing about 55% of the passage tokens
does not mean saving 55% of the complete input, total inference, money or time.
Output tokens and the compression model also have a cost."

The historical percentages are rounded summaries from the saved audit. A target
is an upper token budget, not a promise that every output retains exactly 50%.

## Slide 8 — What was trained

**On-slide text**

- Supervision: saved teacher span order, without QA choices/gold as training inputs.
- Lexical student: six weights, trained on 27,476 directed ranking comparisons.
- Neural student: existing XLM-R large encoder; last block plus linear head updated.
- Training and development have no exact source-group overlap.
- Each student used one fixed training configuration, without development-score early stopping.

| Neural training detail | Recorded result |
| --- | --- |
| Encoder parameters | 558,943,232 |
| Trainable block/head parameters | 12,597,249 |
| Epochs / updates | 2 / 1,718 |
| Training duration | 80.55 seconds |
| Development top-1 teacher agreement | 39.34% |
| Development NDCG@3 | 0.7934 |

**Speaker notes**

"We did not train a foundation model from scratch or fine-tune every encoder
parameter. Ranking agreement is a teacher-imitation measure; it is not answer
accuracy and does not establish evidence preservation. The neural candidate
was introduced after the lexical student's Qwen result, making this exploratory
development adaptation. The final fixed checkpoint was saved and reloaded."

**Evidence:** [training_report.json](C:/Research/backend/data/bench/neural_student_20261116/results/training_report.json).

## Slide 9 — Independent-family results

**On-slide table: Mistral 7B, 183 questions, 50% native context cap**

| Method | Accuracy |
| --- | --- |
| Full context | 48.09% |
| Teacher atomic | 47.54% |
| BM25 atomic | 41.53% |
| LLMLingua-2 strict | 42.08% |
| XProvence strict | 42.08% |
| Lexical student | 40.98% |
| Neural student | 37.16% |

**Speaker notes**

"The teacher's point estimate is higher than the compressed baselines, but
neither student demonstrates the desired advantage. The full-context Mistral
baseline is only 48.09%, so this is one additional model with modest competence,
not broad validation across strong independent models. Gemma was unavailable
because of the proxy download failure; Mistral was selected before its outputs."

The Qwen full-pool and Mistral tables use different models and slices. Their
absolute accuracies are not a before/after progress curve. Both budgets and
all controls are included in the backup tables below.

**Evidence:** [report.json](C:/Research/backend/data/bench/neural_student_20261116/results/combined/report.json).

## Slide 10 — Statistical uncertainty

**On-slide text**

- Comparisons use the same questions, with whole-passage clustering.
- Reported 95% bootstrap intervals are exploratory and unadjusted.
- Holm p-values adjust across the 24 disclosed native comparisons.

| Comparison | Difference, percentage points | 95% interval | Adjusted p |
| --- | --- | --- | --- |
| teacher_atomic@0.5 vs BM25 | +6.01 | [0.00, 11.96] | 0.9621 |
| student_neural@0.5 vs BM25 | -4.37 | [-10.06, 1.12] | 1.0000 |

No native comparison passes adjusted p < .05; the smallest adjusted
p-value is 0.1384.

**Speaker notes**

"A higher observed percentage is not automatically a reliable improvement.
This experiment did not establish independent-family superiority after the
disclosed correction. Failure to establish a difference also does not prove
that all methods are equivalent. The correction covers these 24 comparisons,
not all historical choices and experiments in the project."

Do not present the displayed confidence intervals as simultaneously adjusted
intervals, or interpret a p-value as the probability that our method works.

## Slide 11 — Timing and practical relevance

**On-slide table: native .50 local component means**

| Method | Compression + generation seconds/query |
| --- | --- |
| Full context | 0.3586 |
| BM25 atomic | 0.3928 |
| Lexical student | 0.4018 |
| Neural student | 0.4150 |
| Teacher atomic | 0.8856 |

Original native prompts average **266.60 input tokens**.
This is a short-QA study, not a long-document speed benchmark.

**Speaker notes**

"The measured accounts do not demonstrate a speedup. They include exact-output
reuse, and teacher costs combine historical ranking measurements with current
generation. Setup is separate. This is not an interleaved production latency
or throughput benchmark. Short inputs offer limited prefill savings; ranking
overhead and changed answer lengths may offset those savings. We did not
experimentally isolate the cause or test much longer inputs."

The neural .50 condition averages 12.88 output tokens versus 11.15 for original.
Fewer input tokens do not necessarily mean proportionately less generation work.

## Slide 12 — Failure analysis

**On-slide text**

- Selecting original words does not ensure that their necessary relationships survive.
- Negations, numbers and connected clauses can be removed or separated.
- A model may answer correctly using prior knowledge despite missing evidence.
- Removing punctuation-only outputs can create empty outputs instead.

**Saved example to discuss: bb-428**

The passage connects black clouds with confusion about an apparent eruption.
The lexical student omits the clouds/confusion link and selects the weather-office
option. BM25 retains the clouds/confusion sentence and selects the gold option A.
Full source, choices and actual replies are included in Appendix E.

**Speaker notes**

"This illustrates a failure mechanism; one example is not a population estimate.
In another saved example, bb-246, both compared selections omit the small-river
inflow fact, yet one answer is correct. QA accuracy alone therefore cannot
certify that the required evidence survived."

## Slide 13 — AI review and verification

**On-slide text**

| Measure | Recorded count |
| --- | --- |
| Reviewed rows | 500 |
| Rows revised relative to earlier AI labels | 286 |
| Meaning: yes / partly / no | 268 / 88 / 144 |
| Same-gold answerable: yes / no | 406 / 94 |
| Native served prompts replay-verified | 3294 |
| Native context-cap violations | 0 |

**Speaker notes**

"The owner accepted AI-only working annotations. Revising 286 labels is not
proof that 286 mistakes were corrected. We do not claim human validation,
inter-annotator agreement or guaranteed label correctness. Original gold and
frozen QA rows were preserved, rather than filtered to improve accuracy."

There were 497 valid initial GPU reviews; three invalid initial reviews and
other disputed judgments were handled in 30 source-based AI adjudications.
The count of 30 includes the three invalid cases; do not add them as 33.

**Evidence:** [report.json](C:/Research/backend/data/bench/gpu_annotation_review_20261116/merged/report.json).

## Slide 14 — Completed work and limits

**On-slide text**

Completed: compression/ranking implementations, two trained students, configured
baseline comparisons, AI review, native token checks, raw-output preservation,
replay analysis, figures, checkpoint and internal evidence package.

Limits: exposed development data; AI-only labels; possible source-gold issues;
exact rather than fully audited source families; one modest independent model;
short prompts; limited student configurations; no established speedup or
independent-family superiority.

**Speaker notes**

"The reproducible implementation is a real engineering deliverable. Passing
checks establishes the things those checks test, not research novelty,
production readiness, or semantic correctness. We did not change serving
defaults based on these student results."

## Slide 15 — Conclusions

**On-slide text**

1. Teacher ranking produced promising compressed-input development point estimates.
2. The tested students did not establish the desired quality/efficiency advantage.
3. Actual token savings, answer quality and total compute must be reported separately.
4. Evidence relationships remain a central failure mode in the inspected cases.
5. The experimental study is complete; the original performance objective is unmet.

**Suggested closing statement**

"We implemented and evaluated a question-aware Roman-Hinglish compression
pipeline. Large-model ranking improved observed compressed-input accuracy in
our Qwen development experiments, while retaining an accuracy gap to full
context and adding overhead. The tested students did not reproduce the intended
quality/efficiency advantage. Independent-family and failure analyses limit
the claims we can make. The outcome is a reproducible exploratory study with
documented tradeoffs, rather than a proven faster or superior compressor."

---

## Appendix A — Complete native result table

All methods use 183 development questions. The 50% and 33% labels are context
caps. Original/no-context are common controls. Actual context retention differs
between methods; an equal cap does not mean equal achieved retained length.
Native accuracy uses the original frozen gold labels.

| Condition | Accuracy | Context kept | Full prompt kept | Output tokens mean | Component seconds/query | Invalid | Errors | Empty contexts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 48.09% | 100.00% | 100.00% | 11.15 | 0.3586 | 0 | 0 | 0 |
| no_context | 27.32% | 0.00% | 36.53% | 19.20 | 0.5972 | 4 | 3 | 183 |
| teacher_prefix@0.5 | 47.54% | 45.54% | 65.23% | 13.86 | 0.8856 | 1 | 1 | 0 |
| teacher_prefix@0.33 | 48.09% | 28.84% | 54.57% | 13.34 | 0.8682 | 1 | 1 | 0 |
| teacher_atomic@0.5 | 47.54% | 45.54% | 65.23% | 13.86 | 0.8856 | 1 | 1 | 0 |
| teacher_atomic@0.33 | 47.54% | 28.42% | 54.31% | 14.01 | 0.8885 | 1 | 1 | 5 |
| student_atomic@0.5 | 40.98% | 46.05% | 65.56% | 12.67 | 0.4018 | 0 | 0 | 0 |
| student_atomic@0.33 | 42.08% | 28.34% | 54.26% | 14.74 | 0.4642 | 1 | 1 | 5 |
| bm25_atomic@0.5 | 41.53% | 45.65% | 65.30% | 12.39 | 0.3928 | 0 | 0 | 0 |
| bm25_atomic@0.33 | 40.98% | 28.06% | 54.08% | 14.39 | 0.4531 | 1 | 1 | 5 |
| shuffled@0.5 | 38.80% | 45.29% | 65.07% | 11.99 | 0.3807 | 0 | 0 | 0 |
| shuffled@0.33 | 32.79% | 28.34% | 54.26% | 13.87 | 0.4370 | 1 | 1 | 5 |
| llml2_strict@0.5 | 42.08% | 47.05% | 66.20% | 13.43 | 0.4382 | 0 | 0 | 0 |
| llml2_strict@0.33 | 36.61% | 30.21% | 55.44% | 15.11 | 0.4773 | 1 | 1 | 0 |
| xprovence_strict@0.5 | 42.08% | 39.10% | 61.13% | 13.05 | 0.4225 | 0 | 0 | 4 |
| xprovence_strict@0.33 | 42.08% | 28.88% | 54.60% | 12.94 | 0.4185 | 0 | 0 | 4 |
| student_neural@0.5 | 37.16% | 45.95% | 65.50% | 12.88 | 0.4150 | 0 | 0 | 0 |
| student_neural@0.33 | 38.80% | 28.40% | 54.30% | 14.22 | 0.4552 | 2 | 1 | 5 |

Across the combined native cells, 12 capped records and two other invalid
records remain incorrect. These are counts across method cells, not necessarily
14 distinct questions or independent generations. No-context emptiness is an
intentional control, not a compressor failure.

## Appendix B — All 24 native comparisons

Differences are candidate minus baseline accuracy, in percentage points.
Intervals are exploratory paired passage-bootstrap 95% intervals; the p-values
use Holm adjustment across the 24 rows.

| Candidate | Baseline | Difference (pp) | 95% interval (pp) | Holm p |
| --- | --- | --- | --- | --- |
| student_atomic@0.5 | bm25_atomic@0.5 | -0.55 | [-3.80, 2.72] | 1.0000 |
| student_atomic@0.5 | llml2_strict@0.5 | -1.09 | [-7.78, 5.95] | 1.0000 |
| student_atomic@0.5 | xprovence_strict@0.5 | -1.09 | [-7.87, 5.62] | 1.0000 |
| teacher_atomic@0.5 | bm25_atomic@0.5 | +6.01 | [0.00, 11.96] | 0.9621 |
| teacher_atomic@0.5 | llml2_strict@0.5 | +5.46 | [-1.08, 12.09] | 1.0000 |
| teacher_atomic@0.5 | xprovence_strict@0.5 | +5.46 | [-1.10, 12.23] | 1.0000 |
| teacher_prefix@0.5 | bm25_atomic@0.5 | +6.01 | [0.00, 11.96] | 0.9621 |
| teacher_prefix@0.5 | llml2_strict@0.5 | +5.46 | [-1.08, 12.09] | 1.0000 |
| teacher_prefix@0.5 | xprovence_strict@0.5 | +5.46 | [-1.10, 12.23] | 1.0000 |
| student_neural@0.5 | bm25_atomic@0.5 | -4.37 | [-10.06, 1.12] | 1.0000 |
| student_neural@0.5 | llml2_strict@0.5 | -4.92 | [-10.81, 1.08] | 1.0000 |
| student_neural@0.5 | xprovence_strict@0.5 | -4.92 | [-11.11, 1.61] | 1.0000 |
| student_atomic@0.33 | bm25_atomic@0.33 | +1.09 | [-2.12, 4.30] | 1.0000 |
| student_atomic@0.33 | llml2_strict@0.33 | +5.46 | [-2.16, 12.99] | 1.0000 |
| student_atomic@0.33 | xprovence_strict@0.33 | +0.00 | [-6.78, 6.74] | 1.0000 |
| teacher_atomic@0.33 | bm25_atomic@0.33 | +6.56 | [0.54, 12.64] | 0.8173 |
| teacher_atomic@0.33 | llml2_strict@0.33 | +10.93 | [2.79, 18.72] | 0.1837 |
| teacher_atomic@0.33 | xprovence_strict@0.33 | +5.46 | [-2.22, 13.56] | 1.0000 |
| teacher_prefix@0.33 | bm25_atomic@0.33 | +7.10 | [1.08, 13.26] | 0.6051 |
| teacher_prefix@0.33 | llml2_strict@0.33 | +11.48 | [3.31, 19.34] | 0.1384 |
| teacher_prefix@0.33 | xprovence_strict@0.33 | +6.01 | [-1.65, 13.97] | 1.0000 |
| student_neural@0.33 | bm25_atomic@0.33 | -2.19 | [-7.53, 2.79] | 1.0000 |
| student_neural@0.33 | llml2_strict@0.33 | +2.19 | [-5.38, 9.66] | 1.0000 |
| student_neural@0.33 | xprovence_strict@0.33 | -3.28 | [-10.00, 3.72] | 1.0000 |

## Appendix C — Qwen 4B student-development follow-up

This is the 183-question development slice, not the 900-question table.
It uses Qwen2.5 reference-token text budgets, not verified native Qwen3.5 caps.
There are 2,196 saved records: 1,586 historical-archive reuses, 31 within-run
reuses and 579 new calls. These are not 2,196 independent new examples.

| Condition | Accuracy | Invalid | Recorded errors |
| --- | --- | --- | --- |
| qwen3.5:4b / original | 71.04% | 0 | 0 |
| qwen3.5:4b / no_context | 37.16% | 0 | 0 |
| qwen3.5:4b / teacher_prefix@0.5 | 66.67% | 0 | 0 |
| qwen3.5:4b / teacher_prefix@0.33 | 60.11% | 0 | 0 |
| qwen3.5:4b / teacher_atomic@0.5 | 66.67% | 0 | 0 |
| qwen3.5:4b / teacher_atomic@0.33 | 59.56% | 0 | 0 |
| qwen3.5:4b / student_atomic@0.5 | 53.01% | 0 | 0 |
| qwen3.5:4b / student_atomic@0.33 | 51.91% | 0 | 0 |
| qwen3.5:4b / bm25_atomic@0.5 | 55.19% | 0 | 0 |
| qwen3.5:4b / bm25_atomic@0.33 | 53.01% | 0 | 0 |
| qwen3.5:4b / shuffled@0.5 | 49.73% | 0 | 0 |
| qwen3.5:4b / shuffled@0.33 | 46.99% | 0 | 0 |

All six declared Qwen follow-up comparisons are shown below; the adjustment is separate from the native family.

| Candidate | Baseline | Difference (pp) | 95% interval (pp) | Holm p |
| --- | --- | --- | --- | --- |
| student_atomic@0.5 | bm25_atomic@0.5 | -2.19 | [-6.91, 2.21] | 0.6976 |
| teacher_atomic@0.5 | bm25_atomic@0.5 | +11.48 | [4.44, 18.33] | 0.0099 |
| teacher_prefix@0.5 | bm25_atomic@0.5 | +11.48 | [4.44, 18.33] | 0.0099 |
| student_atomic@0.33 | bm25_atomic@0.33 | -1.09 | [-5.56, 3.33] | 0.6976 |
| teacher_atomic@0.33 | bm25_atomic@0.33 | +6.56 | [1.11, 11.73] | 0.0525 |
| teacher_prefix@0.33 | bm25_atomic@0.33 | +7.10 | [1.65, 12.37] | 0.0463 |

The historical same-family evidence and these development contrasts do not
become fresh confirmation because a within-family comparison has a small
p-value. Conversely, absence of adjusted significance in the native family
does not justify saying that no numerical difference exists anywhere.

## Appendix D — All historical full-pool conditions

Each cell has 900 questions. These are saved development results under reference
token accounting, including exact-prompt reuse. The following table preserves
all four answer models and all 21 conditions, rather than selecting a favourable
budget. Compression and generation columns are recorded component means; they
are not an all-inclusive production benchmark. Checkpoint and configuration
details remain in the archived manifests.

Method-key legend: `bqwen35b_span` is the teacher ranker;
`llml2L_strict` is the large LLMLingua-2 configuration;
`bspan_bm25` is the saved same-packing lexical control;
`bm25_strict` is the strict BM25 baseline; and `bhybrid_char_clause` is the
historical character/clause hybrid condition. The number after `@` is the
target retained-context fraction, not the percentage removed.

| Answer model | Condition | Accuracy | Invalid | Reference-cap misses | Mean context kept | Mean full prompt kept | Compression seconds | Generation seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen 4B | original | 69.11% | 1 | 0 | 100.00% | 100.00% | 0.0003 | 0.1366 |
| Qwen 4B | bm25_strict@0.5 | 58.67% | 0 | 0 | 42.87% | 66.83% | 0.0006 | 0.1183 |
| Qwen 4B | bm25_strict@0.33 | 52.56% | 0 | 0 | 28.41% | 58.27% | 0.0007 | 0.1210 |
| Qwen 4B | bm25_strict@0.75 | 60.44% | 0 | 0 | 64.94% | 79.82% | 0.0006 | 0.1199 |
| Qwen 4B | bm25_strict@0.25 | 49.89% | 0 | 0 | 22.42% | 54.78% | 0.0007 | 0.1317 |
| Qwen 4B | llml2L_strict@0.5 | 60.44% | 1 | 0 | 47.24% | 69.46% | 0.1307 | 0.1315 |
| Qwen 4B | llml2L_strict@0.33 | 50.67% | 1 | 0 | 30.16% | 59.58% | 0.0028 | 0.1313 |
| Qwen 4B | llml2L_strict@0.75 | 66.00% | 1 | 0 | 72.19% | 83.94% | 0.0029 | 0.1327 |
| Qwen 4B | llml2L_strict@0.25 | 49.56% | 2 | 0 | 22.48% | 55.09% | 0.0027 | 0.1312 |
| Qwen 4B | bhybrid_char_clause@0.5 | 57.33% | 0 | 0 | 44.73% | 68.83% | 0.0013 | 0.1243 |
| Qwen 4B | bhybrid_char_clause@0.33 | 53.33% | 0 | 0 | 28.32% | 58.79% | 0.0011 | 0.1262 |
| Qwen 4B | bhybrid_char_clause@0.75 | 62.33% | 1 | 0 | 68.25% | 83.16% | 0.0015 | 0.1230 |
| Qwen 4B | bhybrid_char_clause@0.25 | 48.56% | 0 | 0 | 20.86% | 54.24% | 0.0010 | 0.1313 |
| Qwen 4B | bqwen35b_span@0.5 | 63.44% | 0 | 0 | 44.78% | 68.82% | 0.4145 | 0.1265 |
| Qwen 4B | bqwen35b_span@0.33 | 59.33% | 0 | 0 | 28.28% | 58.74% | 0.4145 | 0.1275 |
| Qwen 4B | bqwen35b_span@0.75 | 66.56% | 0 | 0 | 68.18% | 83.10% | 0.4145 | 0.1219 |
| Qwen 4B | bqwen35b_span@0.25 | 54.67% | 0 | 0 | 21.12% | 54.36% | 0.4145 | 0.1311 |
| Qwen 4B | bspan_bm25@0.5 | 56.89% | 0 | 0 | 44.83% | 68.88% | 0.0012 | 0.1253 |
| Qwen 4B | bspan_bm25@0.33 | 52.33% | 0 | 0 | 28.33% | 58.79% | 0.0010 | 0.1274 |
| Qwen 4B | bspan_bm25@0.75 | 61.89% | 1 | 0 | 67.97% | 83.00% | 0.0014 | 0.1216 |
| Qwen 4B | bspan_bm25@0.25 | 48.56% | 0 | 0 | 20.89% | 54.24% | 0.0010 | 0.1314 |
| Qwen 35B | original | 79.56% | 1 | 0 | 100.00% | 100.00% | 0.0003 | 0.2237 |
| Qwen 35B | bm25_strict@0.5 | 65.78% | 3 | 0 | 42.87% | 66.83% | 0.0006 | 0.1931 |
| Qwen 35B | bm25_strict@0.33 | 58.00% | 13 | 0 | 28.41% | 58.27% | 0.0007 | 0.2010 |
| Qwen 35B | bm25_strict@0.75 | 71.44% | 3 | 0 | 64.94% | 79.82% | 0.0006 | 0.1994 |
| Qwen 35B | bm25_strict@0.25 | 54.11% | 8 | 0 | 22.42% | 54.78% | 0.0007 | 0.2084 |
| Qwen 35B | llml2L_strict@0.5 | 71.22% | 0 | 0 | 47.24% | 69.46% | 0.1307 | 0.2056 |
| Qwen 35B | llml2L_strict@0.33 | 62.44% | 1 | 0 | 30.16% | 59.58% | 0.0028 | 0.2029 |
| Qwen 35B | llml2L_strict@0.75 | 76.56% | 1 | 0 | 72.19% | 83.94% | 0.0029 | 0.2124 |
| Qwen 35B | llml2L_strict@0.25 | 60.22% | 0 | 0 | 22.48% | 55.09% | 0.0027 | 0.2025 |
| Qwen 35B | bhybrid_char_clause@0.5 | 65.44% | 2 | 0 | 44.73% | 68.83% | 0.0013 | 0.2018 |
| Qwen 35B | bhybrid_char_clause@0.33 | 60.56% | 9 | 0 | 28.32% | 58.79% | 0.0011 | 0.2054 |
| Qwen 35B | bhybrid_char_clause@0.75 | 71.67% | 3 | 0 | 68.25% | 83.16% | 0.0015 | 0.2027 |
| Qwen 35B | bhybrid_char_clause@0.25 | 57.22% | 10 | 0 | 20.86% | 54.24% | 0.0010 | 0.2078 |
| Qwen 35B | bqwen35b_span@0.5 | 71.78% | 2 | 0 | 44.78% | 68.82% | 0.4145 | 0.2040 |
| Qwen 35B | bqwen35b_span@0.33 | 65.78% | 5 | 0 | 28.28% | 58.74% | 0.4145 | 0.2034 |
| Qwen 35B | bqwen35b_span@0.75 | 76.33% | 2 | 0 | 68.18% | 83.10% | 0.4145 | 0.2004 |
| Qwen 35B | bqwen35b_span@0.25 | 63.00% | 10 | 0 | 21.12% | 54.36% | 0.4145 | 0.2092 |
| Qwen 35B | bspan_bm25@0.5 | 64.78% | 3 | 0 | 44.83% | 68.88% | 0.0012 | 0.2038 |
| Qwen 35B | bspan_bm25@0.33 | 60.00% | 9 | 0 | 28.33% | 58.79% | 0.0010 | 0.2065 |
| Qwen 35B | bspan_bm25@0.75 | 70.33% | 1 | 0 | 67.97% | 83.00% | 0.0014 | 0.1995 |
| Qwen 35B | bspan_bm25@0.25 | 55.78% | 12 | 0 | 20.89% | 54.24% | 0.0010 | 0.2089 |
| Qwen 27B | original | 83.11% | 0 | 0 | 100.00% | 100.00% | 0.0003 | 0.4792 |
| Qwen 27B | bm25_strict@0.5 | 68.89% | 0 | 0 | 42.87% | 66.83% | 0.0006 | 0.4106 |
| Qwen 27B | bm25_strict@0.33 | 63.67% | 0 | 0 | 28.41% | 58.27% | 0.0007 | 0.4089 |
| Qwen 27B | bm25_strict@0.75 | 75.11% | 0 | 0 | 64.94% | 79.82% | 0.0006 | 0.4254 |
| Qwen 27B | bm25_strict@0.25 | 58.22% | 0 | 0 | 22.42% | 54.78% | 0.0007 | 0.4313 |
| Qwen 27B | llml2L_strict@0.5 | 72.67% | 0 | 0 | 47.24% | 69.46% | 0.1307 | 0.4444 |
| Qwen 27B | llml2L_strict@0.33 | 64.67% | 0 | 0 | 30.16% | 59.58% | 0.0028 | 0.4346 |
| Qwen 27B | llml2L_strict@0.75 | 79.89% | 0 | 0 | 72.19% | 83.94% | 0.0029 | 0.4591 |
| Qwen 27B | llml2L_strict@0.25 | 61.22% | 0 | 0 | 22.48% | 55.09% | 0.0027 | 0.4310 |
| Qwen 27B | bhybrid_char_clause@0.5 | 68.33% | 0 | 0 | 44.73% | 68.83% | 0.0013 | 0.4272 |
| Qwen 27B | bhybrid_char_clause@0.33 | 64.44% | 0 | 0 | 28.32% | 58.79% | 0.0011 | 0.4226 |
| Qwen 27B | bhybrid_char_clause@0.75 | 75.11% | 0 | 0 | 68.25% | 83.16% | 0.0015 | 0.4325 |
| Qwen 27B | bhybrid_char_clause@0.25 | 59.89% | 0 | 0 | 20.86% | 54.24% | 0.0010 | 0.4284 |
| Qwen 27B | bqwen35b_span@0.5 | 75.00% | 0 | 0 | 44.78% | 68.82% | 0.4145 | 0.4332 |
| Qwen 27B | bqwen35b_span@0.33 | 71.78% | 0 | 0 | 28.28% | 58.74% | 0.4145 | 0.4260 |
| Qwen 27B | bqwen35b_span@0.75 | 79.33% | 0 | 0 | 68.18% | 83.10% | 0.4145 | 0.4316 |
| Qwen 27B | bqwen35b_span@0.25 | 66.00% | 0 | 0 | 21.12% | 54.36% | 0.4145 | 0.4299 |
| Qwen 27B | bspan_bm25@0.5 | 68.78% | 0 | 0 | 44.83% | 68.88% | 0.0012 | 0.4298 |
| Qwen 27B | bspan_bm25@0.33 | 63.56% | 0 | 0 | 28.33% | 58.79% | 0.0010 | 0.4258 |
| Qwen 27B | bspan_bm25@0.75 | 75.33% | 0 | 0 | 67.97% | 83.00% | 0.0014 | 0.4285 |
| Qwen 27B | bspan_bm25@0.25 | 58.67% | 0 | 0 | 20.89% | 54.24% | 0.0010 | 0.4292 |
| Qwen 9B | original | 74.22% | 0 | 0 | 100.00% | 100.00% | 0.0003 | 0.1513 |
| Qwen 9B | bm25_strict@0.5 | 60.78% | 0 | 0 | 42.87% | 66.83% | 0.0006 | 0.1295 |
| Qwen 9B | bm25_strict@0.33 | 56.11% | 0 | 0 | 28.41% | 58.27% | 0.0007 | 0.1313 |
| Qwen 9B | bm25_strict@0.75 | 65.44% | 0 | 0 | 64.94% | 79.82% | 0.0006 | 0.1323 |
| Qwen 9B | bm25_strict@0.25 | 52.89% | 0 | 0 | 22.42% | 54.78% | 0.0007 | 0.1421 |
| Qwen 9B | llml2L_strict@0.5 | 62.22% | 0 | 0 | 47.24% | 69.46% | 0.1307 | 0.1424 |
| Qwen 9B | llml2L_strict@0.33 | 56.67% | 0 | 0 | 30.16% | 59.58% | 0.0028 | 0.1414 |
| Qwen 9B | llml2L_strict@0.75 | 70.22% | 0 | 0 | 72.19% | 83.94% | 0.0029 | 0.1452 |
| Qwen 9B | llml2L_strict@0.25 | 52.00% | 0 | 0 | 22.48% | 55.09% | 0.0027 | 0.1419 |
| Qwen 9B | bhybrid_char_clause@0.5 | 60.00% | 0 | 0 | 44.73% | 68.83% | 0.0013 | 0.1355 |
| Qwen 9B | bhybrid_char_clause@0.33 | 55.33% | 0 | 0 | 28.32% | 58.79% | 0.0011 | 0.1367 |
| Qwen 9B | bhybrid_char_clause@0.75 | 67.56% | 0 | 0 | 68.25% | 83.16% | 0.0015 | 0.1349 |
| Qwen 9B | bhybrid_char_clause@0.25 | 52.00% | 0 | 0 | 20.86% | 54.24% | 0.0010 | 0.1411 |
| Qwen 9B | bqwen35b_span@0.5 | 68.11% | 0 | 0 | 44.78% | 68.82% | 0.4145 | 0.1376 |
| Qwen 9B | bqwen35b_span@0.33 | 63.00% | 0 | 0 | 28.28% | 58.74% | 0.4145 | 0.1383 |
| Qwen 9B | bqwen35b_span@0.75 | 70.56% | 0 | 0 | 68.18% | 83.10% | 0.4145 | 0.1342 |
| Qwen 9B | bqwen35b_span@0.25 | 58.56% | 0 | 0 | 21.12% | 54.36% | 0.4145 | 0.1413 |
| Qwen 9B | bspan_bm25@0.5 | 60.44% | 0 | 0 | 44.83% | 68.88% | 0.0012 | 0.1363 |
| Qwen 9B | bspan_bm25@0.33 | 56.22% | 0 | 0 | 28.33% | 58.79% | 0.0010 | 0.1380 |
| Qwen 9B | bspan_bm25@0.75 | 67.89% | 0 | 0 | 67.97% | 83.00% | 0.0014 | 0.1332 |
| Qwen 9B | bspan_bm25@0.25 | 51.78% | 0 | 0 | 20.89% | 54.24% | 0.0010 | 0.1414 |

## Appendix E — Saved real failure examples

The cases below are illustrations already saved by the native analysis script.
They are not a representative random sample or additional accuracy evidence.
The text below is taken from the saved records, not newly invented examples.

### bb-246

**Original Hinglish context**

Amazon river earth ki second longest aur sabse badi river hai. Isme second largest river se bhi 8 guna zyada paani hai. Amazon earth ki sabse wide river bhi hai, jo kabhi-kabhi six miles jitni wide ho jati hai. Hamare planet ki rivers se oceans mein jaane wale paani ka 20% part Amazon se aata hai. Main Amazon river 6,387 km (3,980 miles) long hai. Isme hazaron chhoti rivers milti hain.

**Question**

Passage ke according, Amazon river ke liye paani kahan se aata hai?

- A: Chhoti rivers
- B: Sabse lambi river
- C: Ocean
- D: Doosri sabse badi river

**Frozen source gold:** A

**Lexical-student selection**

Amazon river earth ki second longest aur sabse badi river hai.
Amazon earth ki sabse wide river bhi hai,
Hamare planet ki rivers se oceans mein jaane wale paani ka 20% part Amazon se aata hai.

**BM25 selection**

Isme second largest river se bhi 8 guna zyada paani hai.
Amazon earth ki sabse wide river bhi hai,
Hamare planet ki rivers se oceans mein jaane wale paani ka 20% part Amazon se aata hai.

**Actual lexical-student reply:** C) Ocean

**Actual BM25 reply:** A) Chhoti rivers

### bb-309

**Original Hinglish context**

Current Senator aur Argentina ki First Lady Cristina Fernández de Kirchner ne kal shaam Buenos Aires se 50 km (31 miles) door La Plata city mein apni presidential candidacy announce ki. Mrs. Kirchner ne Argentina Theater se presidential race mein join karne ka announcement kiya, usi jagah se unhone Buenos Aires province ke delegation member ke roop mein Senate ke liye apna 2005 ka campaign start kiya tha.

**Question**

Christina Fernandez De Kirchner ne apne running ke intention ki announcement kahan ki thi?

- A: La Plata se 31 miles door ek theater mein
- B: La Plata mein Buenos Aires theater mein
- C: Buenos Aires se 31 miles door Argentina Theatre mein
- D: Buenos Aires mein La Plata Theatre mein

**Frozen source gold:** C

**Lexical-student selection**

Current Senator aur Argentina ki First Lady Cristina Fernández de Kirchner ne kal shaam Buenos Aires se 50 km (31 miles) door La Plata city mein apni presidential candidacy announce ki.

**BM25 selection**

Mrs. Kirchner ne Argentina Theater se presidential race mein join karne ka announcement kiya,

**Actual lexical-student reply:** A) La Plata se 31 miles door ek theater mein

**Actual BM25 reply:** C) Buenos Aires se 31 miles door Argentina Theatre mein

### bb-428

**Original Hinglish context**

US Geological Survey ke international earthquake maps ne dikhaya ki pichle ek hafte mein Iceland mein koi earthquake nahi aaya. Icelandic Meteorological Office ne bhi report kiya hai ki pichle 48 hours mein Hekla area mein koi earthquake activity nahi hui hai. Tez earthquake activity ki wajah se 10 March ko volcano ke summit caldera ke north-east ki taraf situation change hui thi. Mountain ki foothills mein kisi bhi volcanic activity se unrelated kaale badal dekhe gaye. In clouds ki wajah se confusion ho gaya ki shayad sach mein explosion hua hai.

**Question**

Paragraph ke according, earthquake activity ke baare mein confusion ki situation kya ho sakti hai?

- A: Kaale clouds ki presence
- B: Icelandic weather office se report
- C: International earthquake map
- D: Activity Iceland ke baaki areas mein report ki gayi hai

**Frozen source gold:** A

**Lexical-student selection**

Icelandic Meteorological Office ne bhi report kiya hai ki pichle 48 hours mein Hekla area mein koi earthquake activity nahi hui hai.
Tez earthquake activity ki wajah se 10 March ko volcano ke summit caldera ke north-east ki taraf situation change hui thi.

**BM25 selection**

Tez earthquake activity ki wajah se 10 March ko volcano ke summit caldera ke north-east ki taraf situation change hui thi.
In clouds ki wajah se confusion ho gaya ki shayad sach mein explosion hua hai.

**Actual lexical-student reply:** B) Icelandic weather office se report

**Actual BM25 reply:** A) Kaale clouds ki presence

### Stress-repair tradeoff

The unlabelled 10,000-text stress study separates 2,178 original Roman texts
from 7,822 derived romanizations. On the original-Roman stratum at the .33
budget, a complete-span teacher candidate changed punctuation-only outputs
from 60 to zero, but empty outputs from 27 to 1,464. On the derived stratum,
7,049 outputs became empty. These findings concern this repair policy and
these data. They are not QA accuracy, proof that all atomic selection fails,
or evidence that removing punctuation-only outputs guarantees better semantics.

The candidate was not promoted as a successful repair.

## Appendix F — Questions and honest answers

**Did we beat LLMLingua-2 or Microsoft?**

No general superiority claim is established. Our configured teacher had higher
point estimates in these development runs. The native independent-family
comparison did not establish superiority after the disclosed adjustment.
Information inputs, achieved retained lengths and compute costs also differ.
We did not reproduce and surpass the paper's published benchmark results.

**What is the actual contribution?**

An implemented Hinglish-focused evidence-selection study, teacher/student
comparisons, independent-family/native-token checks, measured cost and failure
analysis, and preserved reproducible artifacts. We do not claim that extraction,
distillation or context compression was invented in this project.

**Did the original objective succeed?**

The implementation and fixed AI-only study were completed. The combined goal
of a better, faster compressor was not established. Administrative closure is
not scientific success or production certification.

**Why did the students underperform?**

Possible explanations include insufficient representations/training and the
mismatch between imitating span order and preserving answer-critical evidence.
We did not isolate causes experimentally; do not present any explanation as proven.
These are two fixed configurations, not evidence that distillation cannot work.

**Why was shorter input not faster?**

Measured component accounts include ranking overhead, and output behavior
changes after compression. The native inputs are short. These are plausible
contributors, not an isolated causal result. Long-document and deployment
throughput performance remain untested.

**Are the 500 labels definitely correct?**

No. They are accepted AI working judgments. There was no human review or
independent human agreement measurement. Owner acceptance does not guarantee
correctness. Eleven original source-gold judgments were flagged, including
ambiguity; those flags were not used to rewrite or filter the frozen QA scores.

**Did native-token verification prove semantic safety?**

No. It checks token counts, caps and exact rendered prompts. Meaning and answer
evidence can still be lost while every token-count check passes.

**Should the tested student replace the current compressor?**

The results do not justify that change. No serving default was changed.
Performance on other workloads would require its own evaluation.

**Can we present this now?**

Yes, as an exploratory implementation and empirical study with mixed/negative
findings. Do not present it as an established superior algorithm, a validated
production system or a guaranteed publication. Assessment depends on the rubric.

**What comes next scientifically?**

Potential separate work includes relation-aware selection, better supervision,
broader independent-model evaluation and long-context timing studies. These
are proposals, not completed results. A future confirmatory claim would need
suitable new validation and a frozen evaluation. No human-review task is being
assigned in this AI-only delivery.

## Appendix G — Claim wording

| Use this wording | Avoid this wording |
| --- | --- |
| Higher observed development accuracy for the configured teacher | We beat Microsoft or LLMLingua-2 generally |
| AI-reviewed working annotations; 286 judgments revised | 500 human-validated examples or 286 proven errors fixed |
| Approximately 55.2% context reduction in the reported condition | 55.2% money saved or 55.2% faster |
| Four Qwen sizes and one additional Mistral family | Five independent model families |
| Exact source-group-separated development; historically exposed | Fresh unseen test set |
| No native comparison passes the disclosed adjusted threshold | The methods are proven equivalent |
| One teacher-prefix cell matches aggregate original accuracy | Lossless compression or identical correct answers |
| Current implementation and AI-only study finalized | Original performance goal or production readiness achieved |

## Appendix H — Figure files and evidence

The existing figures may be used in the later PowerPoint. They are explanatory
views of the saved results, not additional experiments. Keep their scope and
timing/uncertainty qualifications visible.

- [native_tradeoff.png](C:/Research/backend/data/bench/compressor_figures_20261116/native_tradeoff.png)

- [native_student_differences.png](C:/Research/backend/data/bench/compressor_figures_20261116/native_student_differences.png)

### Evidence files and checksums

| Evidence | SHA-256 |
| --- | --- |
| [historical](C:/Research/backend/data/bench/restored_audit_20261116/verified_review.json) | eb41ee250adc1dd11d63d8d2d401271d15754f01f9c3259880e31b129671ea9e |
| [qwen](C:/Research/backend/data/bench/qwen_student_20261116/analysis/report.json) | 815482eee5d0732cc76b8268bdc0f0d33595ad9806af29d8c4232e10402e97e3 |
| [native](C:/Research/backend/data/bench/neural_student_20261116/results/combined/report.json) | 0546b68d4a8c3450764eba337a6a009fded89920a2c582dac527f802f465bedb |
| [training](C:/Research/backend/data/bench/neural_student_20261116/results/training_report.json) | 385557ed2fa3fd644d1d318bb9b09f8342009d387ea487b0e03e11454783618f |
| [annotation](C:/Research/backend/data/bench/gpu_annotation_review_20261116/merged/report.json) | c418fef007fc1dfc92bbbb414ba4cbe127e72266b08d460312b2cd27a2ca1127 |
| [native_audit](C:/Research/backend/data/bench/neural_student_20261116/results/combined/token_replay_audit.json) | 6fe5447f6f84f6d94732f8bd4999e54da2df87bda6f7f9d62f0e9865cf00759d |
| [archive](C:/Research/docs/research/COMPRESSOR_AI_ONLY_ARCHIVE.json) | d1a5c2423949c1a4fffd9455d0d646460a9694e8e2738db0b50c6413fa7ecc75 |

The previously finalized internal archive contains 298 files and is 53,024,257 bytes. This new Markdown content file is a separate presentation deliverable; it is not claimed to be inside that older archive.

The machine-readable closeout and complete reproducibility record are available at:

- [AI-only closeout](C:/Research/docs/research/COMPRESSOR_AI_ONLY_FINAL.json)
- [Methods and execution record](C:/Research/docs/research/COMPRESSOR_STATUS_20261116.md)
- [Current AI-label CSV](C:/Research/docs/annotation/belebele_cm_ai_reviewed.csv)
- [Final internal evidence archive](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip)

Upstream source/data/model licenses remain applicable. The study archive is
internal and was not publicly uploaded. The router certification study remains
separate. There is no completed fresh sealed confirmation represented here.
