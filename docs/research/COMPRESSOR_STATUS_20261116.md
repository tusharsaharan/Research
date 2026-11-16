# Compressor continuation: 16 November 2026

The GPU connection is restored. Local evidence restoration, stress replay,
compact-student development, and power planning are complete. Fresh-data
confirmation and the GPU annotation review are incomplete.

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

Evidence: `backend/data/training/compressor_distill_20261116/manifest.json` and
`backend/data/bench/compact_student_20261116/{student,report}.json`.

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
`/home/user/hinglish-research/gpu-campaign.lock`. The holder runs
`/home/user/hinglish-research/gsm8k_20261116/run.py` under a 73-hour cap. Preserve
that job unless the owner explicitly authorizes changing its priority. Fix the
annotation cleanup so a failed lock acquisition cannot unload someone else's
model. No annotation result exists from the failed launch.

An official Gemma4-26B download was started separately with a 45-minute limit;
it does not load the model onto the GPU. Its success and final installed digest
must be checked before inference. Existing pinned XProvence source metadata
exists remotely, but weights and baseline execution remain pending.

## Remaining gates

- Complete GPU-assisted review of all 500 rows, export raw replies and a revised
  AI-labelled workbook, and inspect disagreements. Preserve human columns.
- Run the frozen source-grouped student-development answer comparisons.
- Add and verify native target-model tokenization, XProvence and LLMLingua-2
  comparisons, and controlled compression-plus-generation cost/latency.
- Establish appropriate source licenses and source-family grouping for a new
  Hinglish pool; obtain human validation and enough independent passages.
- Freeze the final method and run one sealed evaluation. This work cannot
  manufacture those prerequisites from already exposed Belebele data.

The separate router paper and certification split remain unchanged.
