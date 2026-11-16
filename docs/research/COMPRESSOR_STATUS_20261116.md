# Compressor continuation: 16 November 2026

The GPU connection, evidence restoration, stress replay, compact-student
development, power planning, 500-row AI review, and Qwen student comparison
are complete. Native Mistral and one fixed neural-distillation candidate are
in progress. Fresh human-validated confirmation is not available.

Current review files: [corrected workbook](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/belebele_ai_review_corrected.xlsx),
[current AI CSV](C:/Research/docs/annotation/belebele_cm_ai_reviewed.csv), and
[exact human-input guide](C:/Research/docs/research/COMPRESSOR_HUMAN_INPUT_20261116.md).

## Saved measurements

The verified 7 November archive was restored byte-for-byte into
`backend/data/bench/restored_evidence_20261116/`. The new audit reproduces 75,600
QA answers across 900 questions and 488 source passages, plus 80,000 separate
stress outputs. It also reproduces 64 stored output-cap/error records for the
35B answer model. See `restored_audit_20261116/verified_review.json`.

### Complete-span fallback has a major failure tradeoff

The full 10,000-input replay produces 80,000 raw candidate outputs. At the 33%
budget, the teacher-based complete-span candidate changes the original Roman
stratum from 27 empty and 60 punctuation-only outputs to 1,464 empty and zero
punctuation-only outputs, among 2,178 texts. In the derived-romanization stratum,
7,049 of 7,822 outputs become empty. Literal losses also increase. Complete-span
packing therefore cannot be promoted as a repaired quality method. Retain this
negative result and the original algorithm; hard budgets can make complete
evidence infeasible. Surface cleanliness is not semantic preservation.

Evidence: `backend/data/bench/atomic_replay_20261116/report.json` and its
fingerprinted `variants.jsonl`. Three saved examples show a dropped `45`, a
retained `nahi`, and a dropped `nahi`; their full source/output text is retained.

### First compact student is not a demonstrated quality gain

The teacher-order dataset uses 717 questions from 391 passages for training and
183 questions from 97 disjoint passages for development. Both splits are
historically exposed; neither is a fresh test. The student is a fixed six-weight
pairwise logistic ranker trained on 27,476 directed comparisons, without a
hyperparameter search. On development, top-1 teacher agreement is 43.72%, versus
45.90% for BM25. NDCG@3 is 0.7960 versus 0.7904. This is rank imitation,
not downstream answer accuracy. Local mean scoring time was about 0.46 ms for
the student and 0.16 ms for BM25; hardware and deployment differ from GPU serving.

The subsequent 183-question Qwen4B comparison also rejects a student-quality
win: at .50 the student answers 53.01% correctly, versus matched BM25 55.19%,
teacher 66.67%, and original context 71.04%. The student-minus-BM25 difference
is -2.19 percentage points (paired passage bootstrap 95% interval -6.91 to
+2.21; Holm-adjusted p=.698 across six declared Qwen comparisons). At .33,
student 51.91% and BM25 53.01%. No request failures or invalid replies occurred.
All original gold and all questions remain in the denominators.

The run contains 2,196 records: 1,586 exact replies reused from the verified
historical archive, 31 reused within this run, and 579 new calls. A separate
tokenizer replay verifies zero reference-cap misses. These are Qwen2.5
reference-text budgets, not newly established native Qwen3.5 serving caps.
Historical timing is not a fresh latency measurement.

Three inspected teacher-win examples are saved by the reproducibility audit:
bb-76 retains the minimum-strokes criterion; bb-93 retains removal from the
expressed variation pool. In bb-105, the teacher answers correctly even though
its selected text omits the explicit daily-life-break sentence. This cautions
against treating answer accuracy as evidence that every needed fact survived.

Evidence: `backend/data/training/compressor_distill_20261116/manifest.json` and
`backend/data/bench/compact_student_20261116/{student,report}.json`.
QA evidence: `backend/data/bench/qwen_student_20261116/analysis/` with raw
inputs, variants, and answers in its sibling `data/` directory.

### Sample-size planning

The frozen 10,000-replicate simulation uses paired question outcomes and whole
passage clusters from the exposed Qwen4B development run at 0.50. Under the
declared +3 percentage-point alternative and conservative per-comparison alpha
0.025, the smallest tested sizes reaching 80% power are 1,200 passages for BM25
and 2,000 for LLMLingua-2. The discrete grid is coarse; this does not claim an
exact minimum. Null rejection stays near the nominal 2.5%. A fresh source pool
and independent-family planning are still needed.

Evidence: `backend/data/bench/power_analysis_20261116.json`.

## GPU work

SSH to the user-provided college address worked with the existing `user`
account. The workstation reports RTX 5000 Ada, 32 GB VRAM, a working CUDA
environment, and four installed Qwen models. No credentials are stored in the
repository or research artifacts.

The first annotation launch failed before row 1 because another process held
the shared GPU lock. It released the lock itself; no process was killed. The
owner subsequently authorized compressor priority. Cleanup now unloads a model
only after acquiring the lock.

The second annotation run processed all 500 rows in about 938 seconds, with
497 valid structured replies and three invalid ones. Thirty source-based
Codex AI adjudications resolve those three and other contradictory/disputed
judgments. Final labels change 286 rows, with zero unresolved AI fields.
Same meaning: 268 yes / 88 partly / 144 no. Same-gold answerability: 406 yes /
94 no. Naturalness: 13 at 1 / 255 at 2 / 232 at 3. Eleven source-gold flags
include ambiguity; they are not automatically corrected or excluded from QA.
Raw GPU replies, the original labels, and all adjudications are preserved.
These are AI-assisted development annotations, not human validation.

Gemma4-26B could not be downloaded because the proxy returned HTTP 503. Before
any independent-family answers, cached Mistral7B was substituted and frozen.
The pinned XProvence download completed after one bounded continuation of a
timed-out partial asset download. Official spaCy dependencies were installed.
The first Mistral attempt failed during tokenizer setup, before any QA output;
the corrected attempt passes synthetic compressor API checks and runs all
2,928 native-token answer cells. It compares original/no-context, teacher
prefix/atomic, lexical student, matched BM25, shuffled controls, LLMLingua-2
large, and XProvence at .50/.33. No thresholds were tuned against answers.

The lexical student's negative Qwen result motivated one separately declared
neural candidate: cached XLM-R large, final transformer block plus linear head,
two fixed RankNet epochs on the same training split. No hyperparameter search,
development-based checkpoint choice, or repeated search for a win is allowed.
Its two native Mistral cells will join immutable baseline outputs in a separate
exploratory combined report, with all 24 candidate/baseline comparisons.

## Remaining gates

- Retrieve/verify the native Mistral and neural-student outputs and archive the
  full continuation. Keep setup failures and negative candidates.
- Treat measured component timings as local development accounting; a serving
  throughput/latency guarantee needs a deployment-specific benchmark.
- Establish appropriate source licenses and source-family grouping for a new
  Hinglish pool; obtain human validation and enough independent passages.
- Freeze the final method and run one sealed evaluation. This work cannot
  manufacture those prerequisites from already exposed Belebele data.

The separate router paper and certification split remain unchanged.
