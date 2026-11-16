# Compressor continuation: 16 November 2026

The GPU connection, evidence restoration, stress replay, compact-student
development, power planning, 500-row AI review, Qwen comparison, native Mistral
comparison, and one fixed neural-distillation candidate are complete. Both
students underperform the strong baselines in the tested development setting.
Fresh human-validated confirmation is not available. No serving default changed.

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
This attempt completed in about 912 seconds. Mistral's 48.09% original-context
accuracy versus 27.32% without context establishes modest competence, not a
strong frontier-model calibration. The Gemma substitution limits the scope.

The lexical student's negative Qwen result motivated one separately declared
neural candidate: cached XLM-R large, final transformer block plus linear head,
two fixed RankNet epochs on the same training split. No hyperparameter search,
development-based checkpoint choice, or repeated search for a win is allowed.
The first neural launch failed before training because its metrics dependency
was missing. After installing scikit-learn and checking imports, the unchanged
protocol completed 1,718 training steps in about 80.5 seconds and 366 added QA
records. Of 558,943,232 encoder parameters, 12,597,249 block/head parameters were
trained. The final checkpoint was saved in safetensors and reloaded strictly
before evaluation. No training pair was truncated at the frozen 192-token cap.
Teacher top-1 agreement is 39.34%, NDCG@3 .7934, and mean rank-scoring time
about 8.35 ms on this GPU. These teacher-imitation metrics are not QA accuracy.

### Complete native-family comparison

All 183 questions / 97 source passages remain in every cell. The combined
report has 3,294 records across 18 methods. Its 24 paired candidate/baseline
comparisons use whole-passage bootstrap intervals and Holm adjustment across
all 24; this does not correct every historical exploration in the project.

| Method | Accuracy at .50 | Accuracy at .33 |
|---|---:|---:|
| Original context | 48.09% | 48.09% |
| No context | 27.32% | 27.32% |
| Teacher prefix | 47.54% | 48.09% |
| Teacher atomic | 47.54% | 47.54% |
| Lexical student | 40.98% | 42.08% |
| Neural student | 37.16% | 38.80% |
| BM25 atomic | 41.53% | 40.98% |
| LLMLingua-2 strict | 42.08% | 36.61% |
| XProvence strict | 42.08% | 42.08% |
| Shuffled context | 38.80% | 32.79% |

Original/no-context are common controls, repeated in the table for readability,
not independently rerun at each budget. At .50, neural minus BM25 is -4.37
percentage points (95% passage-bootstrap interval -10.06 to +1.12; Holm p=1).
The lexical student differs by -0.55 points (-3.80 to +2.72; Holm p=1).
Neither demonstrates a quality gain. Teacher .50 is +6.01 points over BM25
(0.00 to +11.96), but Holm p=.962 in the expanded family; no adjusted independent-
family superiority is established. Consult the saved combined JSON for exact
values and all comparisons, including non-primary cells.

The independent replay verifies every one of the 3,294 rendered prompt hashes,
recorded context counts, serving input lengths, and native budget caps: zero
native-cap violations. Twelve output-capped records and two other unparseable
answers remain incorrect in their original denominators. Exact prompt reuse
accounts for 1,076 combined records; it is not 1,076 independent extra runs.

At .50, the neural candidate retains 45.95% of context tokens and 65.50% of the
full prompt. Mean output is 12.88 tokens, versus original 11.15. Shorter context
therefore does not imply the same fraction of total inference cost saved.
Its measured compression-plus-generation component mean is about .415 s,
versus .359 s for original and .393 s for BM25. No speedup is established.
Teacher .50 costs about .886 s including historical ranking cost. These are
local component accounts, with exact-reply reuse and historical teacher timing,
not an interleaved deployment-throughput benchmark. Model setup is separate.

Three native disagreements were inspected: bb-246 drops the small-river inflow
fact in both compared outputs, yet BM25's answer is correct; bb-309 separates
the theatre name from its distance/location relation; bb-428's lexical student
drops the cloud/confusion connection. Correct answers can rely on guesses or
prior knowledge. These cases do not certify preservation from QA accuracy.

Evidence: `backend/data/bench/mistral_native_20261116/results/` retains the
original 18-comparison report; `backend/data/bench/neural_student_20261116/results/`
contains the checkpoint, losses, training report, raw added cells and separate
`combined/` report with 24 comparisons and `token_replay_audit.json`.
Figures are in `backend/data/bench/compressor_figures_20261116/`.

### Task ledger after execution

| Original task | Current result |
|---|---|
| A.1 annotation | Protocol and all AI labels complete; human validation and human repeat statistics not supplied. |
| A.2 source-disjoint data | Splitter and exposed-only quarantine exist; new licensed, human-audited source families absent. |
| A.3 power | Completed conditional passage-cluster planning; no universal guaranteed sample size. |
| A.4 repair | Full candidate replay completed; atomic fallback has unacceptable empty/literal-loss tradeoffs and is not promoted. |
| A.5 normalization | Existing retrieval-only normalization/lexicon preserved; emitted source text is not rewritten. |
| A.6 distillation data | Completed source-grouped ordinal teacher dataset without options/gold/QA labels. |
| A.7 token accounting/controls | Native Mistral caps and served templates verified; Qwen remains explicitly reference-text transfer. |
| A.8 protocol/statistics | Frozen development protocols, raw failures, clustered uncertainty and disclosed multiplicity implemented. |
| A.9 writing | Dated results, limitations, figures and reproducible methods recorded; final superiority/paper claims unsupported. |
| B.1 GPU | Access, environment, residency, lock coordination and bounded job completion verified. |
| B.2 independent family | Cached Mistral completed; Gemma proxy failure preserved. |
| B.3 baselines | BM25, LLMLingua-2, XProvence and controls completed on the independent family. |
| B.4 neural student | One fixed two-epoch candidate trained and evaluated; both students miss the quality target. |
| B.5 timing/efficiency | Native token, output and component timing accounts plus figures completed; no speedup demonstrated. |
| B.6 sealed evaluation | Not run: no suitable fresh human-validated sealed pool or frozen successful method. |
| B.7 evidence | Raw artifacts and code preserved locally; internal checksummed continuation snapshot prepared. No public release or push. |

### Reproduce the saved analyses without new inference

From `C:/Research`, with the recorded Python dependencies:

```powershell
$env:PYTHONPATH='backend/src'
python backend/scripts/bench/eval_final_paper.py --data backend/data/bench/qwen_student_20261116/data --output backend/data/bench/qwen_student_20261116/reanalysis
python backend/scripts/bench/review_mistral_native.py --data backend/data/bench/neural_student_20261116/results/combined --inputs backend/data/bench/qwen_student_20261116/data/inputs.jsonl --output backend/data/bench/neural_student_20261116/reanalysis
python backend/scripts/bench/plot_compressor_development.py --report backend/data/bench/neural_student_20261116/results/combined/report.json --output backend/data/bench/compressor_figures_20261116
```

The combined analysis uses all 24 disclosed comparisons. The original native
report remains separate. `audit_native_tokens.py` additionally replays context
and rendered-template counts using the pinned cached Mistral tokenizer; the
GPU-host replay receipt is already saved. No GPU generation is needed for
these analyses. Further inference needs a new dated protocol/output directory;
do not delete state files to bypass duplicate-run guards.

The internal archive is
`outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_evidence_20261116.zip`,
with an adjacent `.manifest.json` containing every included file hash and the
archive digest. It includes the new raw data, trained patch, source scripts,
protocol, review and figures. The restored historical archive is referenced
by its receipt and original SHA-256
`7ebce5a3ae1dfc8abb3f9643475731a87168b8adc9506e12435465885ac42d91`;
it is not relabelled as a new campaign. Full model weights are not bundled.
This is an internal research snapshot; upstream data/model licenses and
attribution still govern any future redistribution. No public release occurred.

## Remaining gates

- Develop a method that meets a prespecified quality/efficiency target on
  development data; the tested student candidates do not. Keep these negatives.
- Treat measured component timings as local development accounting; a serving
  throughput/latency guarantee needs a deployment-specific benchmark.
- Establish appropriate source licenses and source-family grouping for a new
  Hinglish pool; obtain human validation and enough independent passages.
- Freeze the final method and run one sealed evaluation. This work cannot
  manufacture those prerequisites from already exposed Belebele data.

The separate router paper and certification split remain unchanged.
