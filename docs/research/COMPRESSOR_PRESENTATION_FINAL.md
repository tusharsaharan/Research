# Presentation guide: final AI-only Hinglish compressor study

Prepared 16 November 2026 from the frozen reports. This guide supersedes the
older PRESTO pilot presentation brief for this compressor presentation.

## Central message

We built and evaluated a question-aware Hinglish context-compression pipeline.
A large teacher ranker improved observed compressed-input accuracy over BM25
across four Qwen answer-model sizes. It still lost accuracy relative to full
context and added compute overhead. Two smaller students did not establish a
quality/latency advantage. Independent-family evaluation and failure analysis
exposed the limits of the approach.

This is a defensible engineering and exploratory research contribution.
It is not proof of a novel state-of-the-art, lossless, faster compressor.

## Proposed title

Evaluating Evidence-Preserving Context Compression for Roman Hinglish

Subtitle: Teacher Ranking, Student Distillation, and Quality–Efficiency Tradeoffs

## Slide 1 — Problem and research question

- Long contexts consume input tokens; removing text can remove needed facts.
- Roman Hinglish includes spelling variation, code-mixing, negation and relational dependencies.
- Question: can we reduce context while retaining downstream answer quality,
  and can a cheaper student replace an expensive teacher?

Say: "We measured the tradeoff rather than assuming fewer tokens meant a better system."

## Slide 2 — System implemented

Show: passage + question → source spans → relevance ranking → token-budgeted
original-text packing → answer model → evaluation.

- Teacher: Qwen3.6-35B ranks numbered source span IDs.
- Students: a six-weight lexical ranker and an XLM-R-based neural ranker.
- Compressor sees passage/question only; choices/gold go only to evaluation/answering.
- Output text is selected from source wording rather than generated evidence.
- Original wording alone does not guarantee preservation of complete meaning.

## Slide 3 — Data and experiment design

| Component | Size / scope |
|---|---|
| Historical full-pool QA | 900 questions / 488 source passages |
| Historical answer records | 75,600; includes exact-prompt reuse |
| Student training | 717 questions / 391 exact source groups |
| Student development | 183 questions / 97 different exact source groups |
| Independent answer family | Mistral-7B-Instruct-v0.3, all 183 development questions |
| AI translation review | 500 rows, no human review |
| Stress study | 10,000 texts / 80,000 outputs, without QA gold |

All existing Belebele examples have historical exposure. Source-group separation
between training/development does not make the development split a fresh test.
Four Qwen sizes are one model family. The newer Mistral run adds a second family,
not four extra independent families. Counts of records are not counts of unique
questions or newly generated responses.

## Slide 4 — Primary historical result: teacher versus compressors

Use the 50% retained-context target for the full 900-question pool.

| Answer model | Full context | Strict BM25 | LLMLingua-2 large | Teacher |
|---|---:|---:|---:|---:|
| Qwen 4B | 69.11% | 58.67% | 60.44% | 63.44% |
| Qwen 35B | 79.56% | 65.78% | 71.22% | 71.78% |
| Qwen 27B | 83.11% | 68.89% | 72.67% | 75.00% |
| Qwen 9B | 74.22% | 60.78% | 62.22% | 68.11% |

Say: "Observed teacher gains over BM25 were approximately 4.8–7.3 percentage
points. The teacher remained below uncompressed accuracy in all four models."

These are exploratory same-family results under Qwen2.5 reference-token caps.
Do not label them native-budget evaluations for every Qwen size or fresh-test
proof. Use percentage points for accuracy differences, not relative percent.

## Slide 5 — Actual token savings

- Original study at target .50: about 44.8% context kept, 55.2% context removed.
- First answer model: about 68.8% full prompt kept, 31.2% full-prompt reduction.
- Question, choices and instructions are outside the context-only budget.
- Output tokens and compressor inference also contribute to total cost.

Use two stacked bars, one for context and one for full prompt. Do not label
55.2% context reduction as 55.2% money saved, latency reduced or total tokens saved.

## Slide 6 — Independent-family results and students

Main slide: all 183 Mistral questions, native tokenizer, .50 budget.

| Method | Accuracy |
|---|---:|
| Full context | 48.09% |
| Teacher atomic | 47.54% |
| BM25 atomic | 41.53% |
| LLMLingua-2 strict | 42.08% |
| XProvence strict | 42.08% |
| Lexical student | 40.98% |
| Neural student | 37.16% |

Say: "The teacher's point estimate remains promising, but neither student
demonstrates a baseline improvement. The independent model has modest baseline
competence, so this is evidence from one additional family, not universal validation."

Keep .33 results, no-context and shuffled controls in the appendix. Do not
select just the most flattering budget or omit the failed neural model.

## Slide 7 — Statistical uncertainty

Use `native_student_differences.png` from the saved figures.

- Comparisons are paired on the same questions, with whole-passage clustering.
- Teacher atomic vs BM25 at .50: +6.01 points; 95% interval [0.00, 11.96];
  Holm-adjusted p=.9621 in the 24-comparison native family.
- Neural student vs BM25 at .50: -4.37 points; interval [-10.06, 1.12];
  Holm-adjusted p=1.0000.
- None of the 24 native comparisons passes adjusted p<.05; minimum is about .1384.
- Bootstrap intervals displayed are exploratory and unadjusted; p-values carry
  the stated Holm adjustment. Do not imply simultaneous adjusted intervals.

Say: "A higher observed percentage is not automatically a statistically
established improvement. This experiment did not establish independent-family
superiority under our disclosed multiple-comparison policy."

Failure to establish significance does not prove all methods are identical.
Do not say the effect is universally absent or that p is the probability that
the method works. Historical results remain exploratory; do not treat their
unadjusted intervals as a stronger confirmatory claim.

## Slide 8 — Efficiency finding

Native .50 local component means:

| Method | Seconds per query |
|---|---:|
| Full context | .3586 |
| BM25 | .3928 |
| Lexical student | .4018 |
| Neural student | .4150 |
| Teacher | .8856 |

Teacher time includes historical ranker cost. Reused exact outputs and setup
accounting mean these are component estimates, not interleaved production
throughput benchmarks. Use `native_tradeoff.png` and state the limitation.

Say: "The context got shorter, but compression overhead and answer behavior
prevented a demonstrated end-to-end speedup."

## Slide 9 — What failure analysis taught us

- Removing punctuation-only outputs can create empty evidence instead.
- In the original-Roman stress stratum at .33, one atomic candidate changed
  punctuation-only outputs from 60 to zero, but empty outputs from 27 to
  1,464 out of 2,178 texts. It was not promoted as a repaired method.
- Stress data has no QA gold; these counts measure failure modes, not accuracy.
- Saved bb-428: student evidence omits the clouds/confusion relation and gives
  the weather-office option; BM25 retains the clouds/confusion link and selects A.
- Saved bb-246: both compared outputs omit the small-river inflow fact, yet one
  answer is correct. Correct QA answers alone do not certify evidence preservation.

Use one full saved example from the report, with the question, both selections,
gold, and actual model replies. If shortening text for layout, mark omissions.

## Slide 10 — AI review and reproducibility

- Reviewed all 500 source pairs; revised 286 earlier AI judgments.
- Meaning labels: 268 yes / 88 partly / 144 no.
- Same-gold answerability: 406 yes / 94 no.
- These are AI judgments accepted as working labels, not human-validated truth.
- Original gold and frozen QA rows were not rewritten to improve results.
- Verified all 3,294 native served prompts and found zero native cap violations.
- Retained capped/invalid answers in denominators; preserved failures and raw data.
- Saved checkpoint, prompts, hashes, source scripts, replay receipts and archive.

Reproducibility is an engineering contribution, not proof that every label is
correct or that a method is superior. Keep detailed test counts in the appendix.

## Slide 11 — Contributions and limitations

Contributions: an executable Hinglish evidence-selection pipeline; measured
teacher-versus-baseline comparisons; two student implementations/checkpoints;
native independent-family controls; cost/token accounting; concrete failure
analysis; a reproducible AI-only study package.

Limitations: exposed development data; AI-only labels and possible source-gold
issues; exact groups rather than fully audited source families; one modest
independent model; two fixed student configurations; no established speedup;
no fresh sealed confirmation or supported state-of-the-art claim.

Do not combine the separate router certification results with this study to
claim compressor safety or quality.

## Slide 12 — Final conclusion

Suggested closing statement:

"We implemented and evaluated a question-aware Roman-Hinglish compression
pipeline. Large-model evidence ranking improved observed compressed-input QA
over lexical baselines in the Qwen development experiments, but retained an
accuracy gap to full context and introduced overhead. The tested distilled
students did not establish quality or latency gains. Our independent-family
and failure analyses show that reliable evidence preservation, rather than
token removal alone, remains the central challenge."

Future research is a separate scope: relation-aware evidence units, better
ranking supervision/encoding and stronger validation. No human review is being
assigned as part of this completed AI-only delivery.

## Questions to prepare for

**Did you meet the original objective?** We completed implementation and
evaluation. We did not establish the intended combined quality/efficiency gain.

**Did the project fail?** The student-performance hypothesis was not supported
in these experiments. The system, measurement pipeline and documented negative
findings are real outputs; they do not justify claiming a successful faster method.

**What is novel?** We do not claim compression, evidence ranking or distillation
as new inventions. Our defensible contribution is the specific implementation,
Hinglish-focused evaluation and documented findings. Algorithmic novelty needs
separate literature support and stronger evidence.

**Why not just use full context?** Full context had better measured accuracy
and lower measured component time here. Compression may matter under input
limits, but this study does not establish our method as the preferred deployment.

**Why did the student not work?** A plausible explanation is that imitating an
ordinal ranking is an imperfect proxy for retaining answer-critical evidence,
and the tested encoders/features/training setup were insufficient. This is an
interpretation, not a separately proven causal explanation or a universal claim
that distillation cannot work.

**Why are the two models' accuracies different?** The full-pool Qwen table and
183-question Mistral table use different answer checkpoints and evaluation
slices. Their absolute accuracies are not a version-to-version improvement curve.

**Is it publishable?** This is a defensible exploratory engineering study.
Publication, novelty and superiority are not established by these results alone;
acceptance cannot be promised.

## Exact artifacts

- Final report: `docs/research/COMPRESSOR_AI_ONLY_FINAL.md`.
- Historical raw-derived audit: `backend/data/bench/restored_audit_20261116/verified_review.json`.
- Native combined results/intervals: `backend/data/bench/neural_student_20261116/results/combined/report.json`.
- Figures: `backend/data/bench/compressor_figures_20261116/native_tradeoff.png`
  and `native_student_differences.png`.
- Final archive: `outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip`.

All presentation numbers above are drawn from those saved artifacts. Preserve
their exposed-development scope and do not present repeated/reused records as
additional independent examples.
