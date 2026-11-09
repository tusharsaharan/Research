# Detailed execution plan for the Hinglish compressor research

**Created:** 9 November 2026
**Source reviewed:** `to-do.md`, current `README.md`, `docs/progress/ROADMAP.md`, last six lines of `docs/progress/AGENT_LOG.md`, the paper-alignment note, preregistration, current campaign results, and relevant code/test/artifact paths.

## Status verdict

The TODO is a useful proposed research program, but it is **not yet a reliable complete status ledger**.

- The broad missing-evidence claims are consistent with current project records: a fresh source-disjoint human-validated test, a genuinely independent answer family, native-token evaluation, XProvence, a cheap ranker with an efficiency advantage, and a sealed evaluation are not evidenced as complete.
- The full 900-question / 488-passage Belebele pool is historically exposed. Moving items between splits cannot make a fresh test. The 666-item subset outside the latest selection sources also remains exposed.
- The 75,600-answer development run and 80,000-output unlabeled stress run are complete and verified; these are development evidence, not confirmatory evidence.
- The 7 November evidence release is complete and verified. A future campaign still needs its own traceable evidence archive.
- Annotation, source splitting, power simulation, distillation, native-token controls, Gemma calibration, XProvence comparison, latency profile, and sealed test report are not evidenced as complete.
- The proposed annotation sheet exists, but project README says its saved human-verification fields are blank. Generated translations and automatic validation are not a substitute for human review.
- The TODO says phonetic normalization, lexicon tests, and repair work are absent. Those code/test files already exist. Their existence does not establish that stress failures are repaired: saved stress evidence still includes dropped literals, prefix clipping, empty outputs, and punctuation-only outputs.
- The original proposal to build a sealed test from human-verified existing Belebele items is invalid for confirmation. New source families are needed.
- The exact model tags, tokenizer, license, downloaded artifact digest, latency threshold, annotation allocation, practically meaningful effect, and sealed-set size need explicit owner/researcher decisions before evaluation.
- The old roadmap includes unchecked router/demo tasks. The router study is a separate track and must not be treated as evidence for compressor quality or silently pulled into this compressor plan.

**Result:** there is no evidence that the TODO's central research gates have been completed, and there are additional required gates/decisions missing from its task list. However, the TODO is not the only open work list in the repository. This plan scopes the unfinished work needed for a defensible Hinglish compressor study; it does not certify that every stale router/demo checkbox has been reconciled.

## How to read this plan

Each numbered work package records current status, files, human decisions/inputs, an ordered procedure, and a completion gate. A step is complete only when its named artifact or check exists and can be reproduced. A file existing is not evidence that its scientific task is complete. Human annotation, source acquisition, sealed-data custody, model/license choices, and protocol decisions cannot be completed by an agent without the required human work.

## Dependency order

1. Establish the authoritative status ledger.
2. Define annotation and acquire fresh source-family data.
3. Group sources, seal the test, and calculate power.
4. Repair/audit the compressor and test development-only retrieval and student methods.
5. Implement native-token accounting, controls, and the frozen analysis.
6. Restore GPU access; calibrate independent family and baselines.
7. Train/select the student and establish quality/efficiency on development data.
8. Pass the pre-run gate, run the sealed evaluation once, archive and reproduce it.
9. Write paper/thesis claims only from the verified final evidence.

Work on source acquisition, annotation protocol, code audit, and implementation can proceed in parallel only if no one accesses sealed labels or changes a frozen choice based on test outcomes. The ordered freeze gates remain binding.

## Progress update — 9 November 2026

CPU/offline preparation completed in this continuation:

- Added `docs/annotation/ANNOTATION_GUIDE.md` with label definitions, blinded-review workflow, adjudication handling, agreement interpretation, and an explicit warning that the existing Belebele sample remains historically exposed.
- Added `backend/scripts/bench/annotation_agreement.py`. It creates a dual-review template and, after humans fill it, reports per-field missing/invalid counts, label marginals, exact agreement, confusion counts, and Cohen's kappa. It does not infer labels, adjudicate, or filter.
- Generated `docs/annotation/belebele_cm_review_template.csv`, preserving the original 500 rows and adding independent reviewer/adjudication columns. Its labels are intentionally blank.
- Generated `docs/annotation/belebele_cm_review_assignments.csv`, with one blank primary/overlap assignment row per item; the owner must assign actual people and overlap IDs before annotation.
- Added `backend/scripts/bench/build_source_splits.py`, a configurable source-family splitter that requires explicit exposure booleans and a human-audited family key; exposed groups are forced to development, gold is separated from sealed inputs, and every split/manifest is hashable. It has not been run because no new, reviewed source dataset or owner-approved split proportions/seed exist.

Human-dependent gates remain open: assign qualified bilingual reviewers and overlap rows; approve how `partly` and naturalness affect eligibility; acquire/license genuinely fresh sources and have humans establish source-family IDs; choose split proportions and custodian; choose practical effect size, alpha/power, primary comparator, and sample-size ceiling. Existing 500-row annotation can be completed for development-data quality but cannot be used as a fresh test. No GPU work was started. No tests were run.


## Work package 00: Resolve the authoritative work list and status ledger

**Current status:** PARTLY COMPLETE: the 7 Nov README and roadmap provide current priorities, but the untracked TODO contains proposed tasks and the roadmap also retains older router/demo checkboxes.

**Files and evidence:** to-do.md; README.md; docs/progress/ROADMAP.md; docs/progress/AGENT_LOG.md; docs/research/COMPRESSOR_PAPER_ALIGNMENT.md

**Human input required:** Confirm whether this plan is the canonical compressor backlog and whether to-do.md should later be edited to reflect status. Do not overwrite it in this plan-writing pass.

### Ordered execution steps

### 00.01 Create a dated inventory of each TODO deliverable and matching repo evidence.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.02 Label each item complete, partial, pending, blocked, superseded, or needs a decision.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.03 Separate completed code scaffolding from completed scientific evidence.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.04 Mark all 900 Belebele items and 488 passages historically exposed.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.05 Record that the 666-item subgroup remains historically exposed.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.06 Record that model-family diversity is absent from the full-scale QA run.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.07 Record the checked-in blank verification sheet and any independent annotations not present.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.08 Record completed 75,600 QA and 80,000 stress-output campaign evidence.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.09 Record completed 7 November evidence release and checksum receipt.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.10 Identify the most recent SSH timeout and state live GPU availability as unknown.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.11 Identify code/tests that already implement some proposed A.4 and A.5 behavior.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.12 Identify the difference between compressor work and the separate router study.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.13 Cross-check every purported completed result against a saved artifact.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 00.14 Publish a concise status table before treating any proposed run as authorized.

**Purpose.** This action exists to make the resolve the authoritative work list and status ledger work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 00

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 01: Define human annotation protocol and complete source-language review

**Current status:** PENDING: saved annotation fields are reported blank; do not treat existing checks or generated Hinglish as human validation.

**Files and evidence:** docs/annotation/belebele_cm_verify_500.csv; docs/annotation/belebele_cm_verify_500_completed.csv; backend/scripts/bench/annotation_agreement.py; backend/data/bench/annotation_report.json; docs/research/DATA_CARD.md

**Human input required:** Human annotators must supply row assignments, bilingual competence confirmation, annotation judgments, overlap assignments, adjudicator identity, and any corrections. The project owner must approve eligibility rules and whether the existing 500-row sheet is adequate.

### Ordered execution steps

### 01.01 Inspect CSV header, row count, unique IDs, and all current values without changing the source sheet.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.02 Define each label with operational examples and an explicit not-applicable value.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.03 Write a short annotator guide covering meaning, answerability, naturalness, gold alignment, and notes.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.04 Separate bilingual correctness judgments from stylistic preference judgments.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.05 Specify independent review and blindness to model outputs and method identity.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.06 Assign unique row ranges to named annotators and prevent accidental duplicate ownership.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.07 Select the overlap rows before annotation and record the deterministic selection seed.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.08 Reserve a second annotator for overlap rows and an adjudicator for disagreements.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.09 Copy the input sheet to a versioned output file and retain original row IDs.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.10 Have annotators review English/Hinglish passage, question, options, and gold alignment together.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.11 Record partial meaning equivalence separately from fully equivalent and non-equivalent cases.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.12 Record answerability and whether the same gold remains correct in both variants.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.13 Record naturalness on the agreed ordinal scale and add a short rationale when low.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.14 Run schema checks for missing, invalid, duplicate, or out-of-range annotations.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.15 Calculate agreement on the overlap set and preserve per-label confusion tables.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.16 Report kappa choice, prevalence caveats, confidence intervals, missingness, and adjudication separately.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.17 Apply only preregistered inclusion rules and retain exclusion counts with reasons.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.18 Write a provenance-aware data card distinguishing adapted, translated, synthetic, and human-reviewed text.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.19 Compare known suspicious items such as bb-387 against the source and document the resolution.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 01.20 Freeze the final annotation file hash and attach it to the later split manifest.

**Purpose.** This action exists to make the define human annotation protocol and complete source-language review work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 01

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 02: Acquire genuinely fresh data and build source-family leakage groups

**Current status:** PENDING: historical Belebele is ineligible as a fresh confirmatory set; a new source-disjoint, human-validated pool is required.

**Files and evidence:** backend/scripts/bench/build_source_splits.py; backend/data/bench/splits_manifest.json; backend/data/bench/test_sealed_inputs.jsonl; docs/research/DATA_CARD.md; docs/research/PREREG.md

**Human input required:** Owner chooses target population/task, data source and licensing path, annotation budget, inclusion scope, acceptable source families, and who controls the sealed labels. Annotators verify each new Hinglish variant. Any external source acquisition or paid service needs separate authorization.

### Ordered execution steps

### 02.01 List candidate datasets and determine whether they contain Roman-script Hinglish and answerable source-grounded questions.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.02 Check the original source license, derivative translation terms, redistribution limits, and attribution.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.03 Choose at least one source pool that has not appeared in prior local or external evaluations.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.04 Track source document, passage, question, variant, translator, and annotation provenance with stable IDs.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.05 Define normalized exact passage hashes and a conservative near-duplicate/source-family grouping policy.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.06 Group all language variants, paraphrases, questions, and related passages under the same source-family key.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.07 Quarantine every historical Belebele source and all known derivatives from confirmatory evaluation.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.08 Keep original, human-derived, machine-generated, and synthetic records in separate manifest strata.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.09 Design train, development, and sealed-test groups by source family before inspecting test labels.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.10 Use group-level deterministic allocation and save the seed, algorithm version, and split counts.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.11 Verify zero source-family overlap across train, development, and sealed test.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.12 Verify zero overlap with all exposure-registry IDs and historical source fingerprints.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.13 Write only IDs and non-label metadata into the sealed input package until the freeze gate.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.14 Keep sealed labels and answer keys under a controlled path with explicit access logging.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.15 Build a manifest containing hashes, licenses, source lineage, split assignment, and exclusion reasons.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.16 Have a second reviewer audit random groups and near-duplicate decisions before locking.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.17 Record the exact count of eligible independent groups, not only the number of questions.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.18 Report any shortfall against the eventual power target before deciding whether to collect more data.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.19 Mark a dataset as confirmatory only if novelty, human validation, and grouping gates all pass.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 02.20 Archive rejected and development-only data separately so future researchers can reproduce selection.

**Purpose.** This action exists to make the acquire genuinely fresh data and build source-family leakage groups work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 02

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 03: Run passage-clustered power and sample-size planning

**Current status:** PENDING: no power-analysis artifact is present; the proposed +3 percentage-point effect is a decision, not an established fact.

**Files and evidence:** backend/scripts/bench/power_simulation.py; backend/data/bench/power_analysis_report.json; docs/research/PREREG.md

**Human input required:** The owner must choose the smallest practically meaningful effect, primary comparator, acceptable type-I error, target power, eligible population, and feasible annotation ceiling. Researchers must approve whether the development discordance distribution is a reasonable planning proxy.

### Ordered execution steps

### 03.01 Freeze the outcome definition and comparison that determine the primary power calculation.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.02 Choose a practically meaningful difference before using the simulation to select sample size.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.03 State alpha, target power, confidence-interval method, and any multiplicity adjustment.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.04 Estimate paired disagreement structure only from eligible development data.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.05 Preserve passage-family cluster sizes rather than pretending every question is independent.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.06 Model within-passage correlation and uncertainty in the planning effect size.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.07 Simulate paired outcomes under null and alternative across candidate cluster counts.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.08 Include realistic unequal cluster sizes, invalid answers, empty outputs, and exclusions.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.09 Use a fixed random generator and seed and record software versions.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.10 Run enough replicates to make Monte Carlo error negligible for the decision.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.11 Report power by independent passage count and total question count separately.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.12 Show sensitivity curves for plausible effect sizes and intracluster correlations.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.13 Report the smallest sample size meeting the chosen criterion, not only a single headline.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.14 Check that available fresh source families can meet the target without leakage.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.15 Write assumptions and the selected target into the dated preregistration change log.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.16 Do not inspect confirmatory outcomes to revise the sample-size target.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.17 Retain a report for underpowered outcomes and label any later increase as protocol change.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.18 Have an independent reviewer inspect the simulation code and interpretation.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.19 Do not call 10,000 simulation draws a substitute for enough independent passages.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 03.20 Stop before test inference if fresh data cannot satisfy the frozen design.

**Purpose.** This action exists to make the run passage-clustered power and sample-size planning work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 03

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 04: Audit and repair relational span boundaries and fallback behavior

**Current status:** PARTLY COMPLETE: repair code and regression-test files exist, but the saved stress evidence still contains dropped literals, clipping, empties, and punctuation-only outputs.

**Files and evidence:** backend/src/gateway/modules/m2_compressor/hinglish_evidence.py; backend/src/gateway/modules/m2_compressor/qwen_evidence.py; backend/tests/test_hinglish_evidence_repair.py; backend/tests/test_budgeted_compressor.py; backend/data/bench/hinglish_scaleup_full_20261029/stress_report.json

**Human input required:** A bilingual reviewer should label the stress examples for meaning-changing loss and boundary correctness. The owner must decide which failure rate is unacceptable and whether oversized evidence should yield empty output or an explicitly marked alternative.

### Ordered execution steps

### 04.01 Map each documented stress failure to the exact compressor, span, budget, and output path.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.02 Keep existing method names and historical outputs reproducible; add repaired variants under new IDs.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.03 Audit boundary behavior around causal, contrastive, concessive, temporal, and conditional connectives.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.04 Audit agent-action-object relations, pronoun antecedents, quotations, abbreviations, and punctuation.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.05 Treat negation and quantities as relational evidence, not merely token-presence checks.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.06 Verify original source offsets reconstruct exact substrings with no normalization leakage.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.07 Replace raw token-prefix fallback only where the new protocol explicitly defines behavior.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.08 Keep whole-span packing within measured caps using the actual rendering-aware tokenizer.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.09 Record infeasible items, empty outputs, clipped outputs, and budget misses distinctly.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.10 Add targeted regression cases for each observed failure mechanism.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.11 Use the existing repair tests as coverage evidence, not as proof all 10,000 examples are repaired.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.12 Run the frozen stress set once after code changes and retain every raw output.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.13 Check at least three real outputs manually, including negation, numeric, and relational cases.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.14 Report literal-loss rates as diagnostics and do not call them semantic accuracy.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.15 Compare candidate and matched packing control on identical segmentation and tokenization.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.16 Preserve the original method and report candidate/control paired differences.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.17 Measure performance on all stress strata, keeping original Roman and derived text separate.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.18 Reject any patch that improves one handpicked example while regressing the frozen aggregate.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.19 Update code hash, test hash, tokenizer hash, and method description in the manifest.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 04.20 Keep final acceptance conditional on independent human judgments and no silent failure mode.

**Purpose.** This action exists to make the audit and repair relational span boundaries and fallback behavior work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 04

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 05: Separate retrieval normalization from output text and test retrieval ablations

**Current status:** PARTLY COMPLETE: phonetic normalization module and tests exist; the proposed generic lexicon task is not simply missing, but evidence-ranking integration and effectiveness need audit.

**Files and evidence:** backend/src/gateway/modules/m2_compressor/phonetic.py; backend/tests/test_phonetic.py; backend/tests/test_lexicon.py; backend/src/gateway/modules/m2_compressor/hinglish_evidence.py; docs/research/PREREG.md

**Human input required:** A bilingual reviewer must vet transliteration equivalence groups and homographs. The owner chooses whether variant lexicon development is in scope after the existing module is audited. Do not ask the lexicon to collapse semantically distinct words.

### Ordered execution steps

### 05.01 Inventory current normalization call sites and distinguish CRF cleanup from evidence-ranking features.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.02 Record the existing abbreviation map, protected tokens, homograph guards, and test coverage.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.03 Define a development-only spelling-variant set with source passage provenance.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.04 Have a bilingual reviewer label whether each proposed spelling pair is interchangeable in context.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.05 Add a ranking representation that can normalize variants without rewriting source output.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.06 Preserve protected markers, numbers, names, punctuation, and original offsets through scoring.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.07 Compare exact lexical scoring against normalized scoring on the same development examples.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.08 Include character/subword matching as a separate ablation instead of bundling every feature.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.09 Measure retrieval recall of answer-bearing spans using labels available only on development data.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.10 Track false matches from homographs, code-switches, short tokens, and named entities.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.11 Verify every emitted output is a byte-faithful source substring or a documented join thereof.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.12 Use deterministic scores and ties and record implementation version.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.13 Do not provide options or gold labels to the question-only compressor.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.14 Compare results with and without normalization under identical token caps and answer prompts.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.15 Retain negative outcomes and describe them as a failed development hypothesis when appropriate.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.16 Have a second bilingual reviewer audit a sample of errors and false positives.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.17 Freeze only a candidate that improves the predeclared retrieval metric without source rewriting.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.18 Ensure all choices are made on development data, never on sealed results.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.19 Update the method card to explain normalization scope and known language-variation limits.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 05.20 Do not duplicate existing lexicon tests under new filenames without new behavior.

**Purpose.** This action exists to make the separate retrieval normalization from output text and test retrieval ablations work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 05

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 06: Build a leakage-safe distillation dataset from development evidence

**Current status:** PENDING: no distillation dataset builder or saved train/dev files were found; prior 35B teacher outputs exist only as evidence and require a task-specific audit.

**Files and evidence:** backend/scripts/bench/build_distill_data.py; backend/data/bench/hinglish_scaleup_full_20261029/; backend/data/training/compressor_distill_train.jsonl; backend/data/training/compressor_distill_dev.jsonl; backend/data/bench/distill_manifest.json

**Human input required:** The owner approves teacher-supervision target, allowable training sources, data-license treatment, excluded records, and compute budget. Human labels may be used only under the frozen development/training policy; sealed test passages and labels are prohibited.

### Ordered execution steps

### 06.01 Enumerate raw campaign files and manifests without dumping full JSONL into logs.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.02 Verify hashes, question-to-passage links, model digest, ranker prompt, and answer correctness fields.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.03 Map teacher-ranked span IDs back to exact source offsets and detect invalid or duplicate ranks.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.04 Define whether the student learns teacher order, downstream answer-bearing evidence, or a declared combination.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.05 Keep teacher ranking targets separate from answer correctness targets in the schema.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.06 Exclude sealed and confirmatory source families before creating any dataset row.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.07 Quarantine historically exposed examples as development-only and label their exposure.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.08 Group all rows by source family before any train/dev allocation.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.09 Create a deterministic passage-grouped train/dev split and save seed and group counts.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.10 Prevent near-duplicate passages and all language variants from crossing train/dev.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.11 Preserve teacher failures and missing ranks with explicit statuses instead of dropping them.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.12 Record how downstream correctness is computed and freeze the parser/grading policy.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.13 Ensure no answer, option, gold, or teacher explanation enters the runtime compressor features.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.14 Write compact examples with passage ID, question, span IDs, text, teacher score, and provenance.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.15 Add schema validation for empty text, duplicate IDs, malformed scores, and invalid source offsets.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.16 Write manifest hashes and a summary of group, item, positive, negative, and missing-label counts.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.17 Inspect at least three examples by hand for correct alignment and no gold leakage.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.18 Compare sample weighting choices and class imbalance without selecting on sealed data.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.19 Train/dev outputs must remain reproducible from committed script and raw evidence hashes.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 06.20 Do not imply distillation quality from a dataset successfully building.

**Purpose.** This action exists to make the build a leakage-safe distillation dataset from development evidence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 06

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 07: Implement native-token accounting and matched negative controls

**Current status:** PENDING: existing campaign used Qwen2.5 reference-token caps and fixed-text transfer; no independent-family native-budget/control report was found.

**Files and evidence:** backend/src/gateway/tokenizer.py; backend/src/gateway/modules/m2_compressor/budgeted.py; backend/scripts/bench/controls.py; backend/data/bench/

**Human input required:** Model owner approves exact model snapshots and prompts. License/legal owner verifies tokenizer and model terms. The study owner freezes whether cap applies to context or full prompt and which figures are primary.

### Ordered execution steps

### 07.01 Inventory the token counters currently supported and their fingerprints.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.02 Define the exact native tokenizer and prompt renderer for every answer model.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.03 Pin tokenizer revision, chat template, special-token handling, and truncation policy.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.04 Count context, full rendered prompt, generated answer, and compressor overhead separately.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.05 Validate that the serving path and offline evaluator count the same byte-identical prompt.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.06 Test boundary cases around system text, options, separators, and special tokens.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.07 Use actual tokenizer counts to pack each method separately at the matched context cap.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.08 Report the resulting full-prompt retention even when fixed context fractions differ.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.09 Keep reference-token transfer results under their own clearly labelled protocol.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.10 Implement no-context prompts with the same question, options, and formatting policy.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.11 Implement shuffled-context controls with fixed seeds and exact matched retained token counts.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.12 Ensure shuffling preserves the multiset of source spans and does not introduce answer labels.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.13 Run controls for both answer families with the same decoding settings as their comparators.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.14 Record prompt tokens, output tokens, latency, empty output, parse failure, and inference cost.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.15 Add tests for tokenizer parity and exact measured cap enforcement.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.16 Compare original, compressed, no-context, and shuffled conditions in the same denominator.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.17 Describe how shuffling affects discourse coherence and avoid overclaiming causal isolation.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.18 Store control order seeds, raw prompts, raw answers, and model usage in immutable manifests.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.19 Report model-specific costs using dated provider/runtime pricing assumptions.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 07.20 Block any native-token claim if only reference-token counts are available.

**Purpose.** This action exists to make the implement native-token accounting and matched negative controls work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 07

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 08: Freeze protocol, hypotheses, and analysis before development-to-test transition

**Current status:** PENDING: PREREG.md contains an older router registration and dated compressor change log; a new dated compressor protocol must be added before new evaluation.

**Files and evidence:** docs/research/PREREG.md; backend/scripts/bench/eval_final_paper.py; backend/data/bench/

**Human input required:** Research lead approves primary hypothesis, margin, budget, baselines, answer families, sample size, failure handling, multiplicity family, practical-efficiency threshold, and stopping rule. These choices cannot be inferred from the exploratory results.

### Ordered execution steps

### 08.01 Separate the compressor protocol from the R1 router preregistration and label scope clearly.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.02 Write the date and reason for each protocol amendment before any new answer generation.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.03 Define one primary candidate selected solely on development data.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.04 Define primary budget and secondary stress budgets and specify which comparisons are confirmatory.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.05 Freeze answer-model family, exact snapshot, prompt, parser, tokenizer, sampling, and output cap.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.06 Freeze compressor input fields and ensure no choices or gold reach question-only rankers.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.07 Freeze source data hashes, source-family split manifest, annotation policy, and exposure rules.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.08 Define all metrics, denominators, invalid-output policy, infeasible-output policy, and missingness reporting.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.09 Define paired passage-clustered interval method, resampling seed, replicate count, and cluster unit.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.10 Define multiplicity correction across prespecified baselines, models, and secondary budgets.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.11 Define meaningful superiority or noninferiority margins before viewing sealed outcomes.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.12 Define total system efficiency claims using compressor plus generation latency and actual costs.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.13 Freeze negative controls and ablations, including their matching rules.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.14 Define parser sensitivity reporting without selecting the most favorable parser after results.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.15 Specify minimum valid source-family count and what to do if the target power is unmet.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.16 Write a machine-readable config that mirrors the preregistered values.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.17 Implement evaluator validation for duplicate, missing, malformed, and unexpected result rows.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.18 Generate tables only from immutable raw records and committed analysis code.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.19 Have a reviewer compare config, preregistration, and runner flags before freeze.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 08.20 Tag and hash the frozen code/config bundle before accessing sealed labels.

**Purpose.** This action exists to make the freeze protocol, hypotheses, and analysis before development-to-test transition work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 08

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 09: Restore GPU access and coordinate shared hardware

**Current status:** BLOCKED/PENDING: SSH timed out on 7 Nov; no proof of current remote GPU availability or free capacity.

**Files and evidence:** /home/user/hinglish-research/gpu-campaign.lock; remote GPU setup log; backend/data/bench/gpu_setup_20261029/

**Human input required:** Human owner restores college VPN/SSH, confirms host/account access, coordinates with lab users, and supplies any environment-specific credentials through approved secret storage. No credentials should be written into Git or the plan.

### Ordered execution steps

### 09.01 Read the existing GPU setup evidence and identify the last verified machine configuration.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.02 Confirm SSH and VPN access through the documented host alias without exposing secrets.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.03 Inspect the shared campaign lock and current owner, timestamp, and expiry.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.04 Contact the current lock owner through the user's normal process if the lease is active.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.05 Acquire the lock only after confirming no conflicting run is active.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.06 Record who owns the lock, the campaign name, and expected release time.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.07 Inspect GPU model, driver, memory, utilization, and competing processes.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.08 Check Python, CUDA, PyTorch, Ollama, and relevant package versions.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.09 Verify model-cache availability and disk headroom before any downloads.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.10 Set explicit job wall-time, per-request timeout, memory target, and no-retry policy.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.11 Write logs, atomic state, and a unique run directory before launching work.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.12 Ensure failure recovery will not trigger duplicate calls or repeated GPU jobs.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.13 Release the lock after work and record actual start/end times.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.14 Keep remote logs and setup metadata in a reproducible evidence path.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.15 Do not start expensive inference if GPU lock ownership is unclear.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.16 Do not interpret a prior setup snapshot as evidence of today's free capacity.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.17 Escalate network/provider issues through the existing approved path.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.18 Record whether the blocker is VPN, SSH, contention, driver, memory, or model availability.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.19 Update the project status with the exact failed or completed preflight stage.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 09.20 Proceed only after the hardware gate is recorded complete.

**Purpose.** This action exists to make the restore gpu access and coordinate shared hardware work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 09

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 10: Calibrate an independent answer-model family and validate baseline competence

**Current status:** PENDING: Gemma 4 is a proposed independent family; no completed local calibration or evaluation evidence was found.

**Files and evidence:** docs/research/HINGLISH_LITERATURE_2026-10-29.md; backend/data/bench/gemma4_calibration_report.json; backend/data/bench/

**Human input required:** Owner confirms Gemma snapshot, license constraints, model runtime, acceptable download/storage, and whether model family counts as sufficiently independent for the intended claim. Bilingual reviewers approve the prompt and parse audit sample.

### Ordered execution steps

### 10.01 Recheck the model card, current exact artifact revision, license, and supported runtime.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.02 Freeze the full model digest rather than relying on a mutable tag or abbreviated hash.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.03 Record prompt template, thinking/reasoning setting, temperature, seed, and output ceiling.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.04 Estimate disk and VRAM needs including context cache and competing processes.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.05 Acquire model only after the shared GPU and compute gates are satisfied.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.06 Run a bounded load-only smoke test and capture actual GPU residency.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.07 Run an uncompressed development calibration set selected before inspecting outputs.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.08 Measure exact rendered-prompt native token counts and context-limit behavior.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.09 Audit answer parse rate and grading validity separately from accuracy.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.10 Check raw output examples for formatting, language comprehension, and truncation.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.11 Report baseline accuracy and invalid-output rate by task and language.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.12 Do not tune prompts on sealed examples or hide poor uncompressed competence.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.13 Compare answer-model performance with human-verified answerability strata.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.14 Estimate the model's own cost and generation latency on the same hardware.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.15 Pin runtime/library versions and preserve the exact calibration prompts and replies.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.16 Stop if the model cannot fit or has unusable parsing under the frozen protocol.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.17 Do not substitute another model tag after calibration without a documented amendment.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.18 Document model-family independence as a reasoned limitation, not absolute independence.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.19 Store a signed or hashed calibration manifest beside raw outputs.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 10.20 Advance only if the uncompressed calibration gate passes the predeclared criterion.

**Purpose.** This action exists to make the calibrate an independent answer-model family and validate baseline competence work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 10

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 11: Benchmark independent-family compressors and controls on development data

**Current status:** PENDING: XProvence and Gemma are documented candidates, not completed measurements.

**Files and evidence:** backend/data/bench/baselines_dev_report.json; backend/data/bench/; backend/scripts/bench/controls.py; docs/research/HINGLISH_LITERATURE_2026-10-29.md

**Human input required:** Owner approves model license use, exact XProvence version, custom-code review, development sample, cost ceiling, and any label-based QA judgments. Annotators validate a small set of method outputs for evidence fidelity.

### Ordered execution steps

### 11.01 Freeze the development IDs, source-family set, prompts, and native token caps.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.02 Pin XProvence model revision, package versions, custom loading code, and license.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.03 Review external code and model card before executing remote or custom code.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.04 Verify XProvence output extraction and wrapper behavior on a tiny development smoke set.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.05 Compare strict BM25, LLMLingua-2 large, XProvence, same-packing BM25, and original.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.06 Add no-context and shuffled-context conditions under matched prompt budgets.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.07 Keep all methods on identical passages, questions, answer snapshots, and denominators.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.08 Repack each method with the answer model's native tokenizer.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.09 Record budget misses, empty outputs, invalid answers, and full prompt token counts.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.10 Track compressor latency separately from generation and model setup.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.11 Capture raw text, selected span IDs, prompts, replies, and per-row usage.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.12 Use passage-grouped development data only for candidate selection and calibration.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.13 Do not pick XProvence v1 or v2 based on whichever looks best after unrestricted testing.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.14 Audit license restrictions before distributing weights, outputs, or adapted components.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.15 Inspect at least three representative answer differences and source spans.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.16 Report paired exploratory intervals with all model and budget cells disclosed.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.17 Keep results clearly marked development and avoid confirmatory language.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.18 Check whether no-context accuracy reveals parametric answer leakage or easy questions.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.19 Check whether shuffled controls retain question-relevant words while disrupting relation.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 11.20 Freeze chosen baseline settings before the sealed study.

**Purpose.** This action exists to make the benchmark independent-family compressors and controls on development data work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 11

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 12: Train and validate the lightweight student evidence scorer

**Current status:** PENDING: no student dataset, checkpoint, or training report was found.

**Files and evidence:** backend/scripts/bench/build_distill_data.py; backend/data/training/; backend/data/models/hinglish_evidence_student.pt; backend/data/bench/distill_training_report.json

**Human input required:** Owner chooses model architecture, trainable parameter budget, permitted training artifacts, hardware ceiling, checkpoint retention policy, and minimum latency target. Human source-span judgments may be needed to validate teacher labels.

### Ordered execution steps

### 12.01 Build and verify the source-grouped train/dev data before allocating accelerator time.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.02 Select a compact candidate architecture using development-only evidence and memory estimates.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.03 Freeze maximum parameters, input length, tokenizer, optimization schedule, and stopping rule.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.04 Set a fixed compute cap and stop condition before training begins.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.05 Use only grouped training examples for updates and grouped development examples for selection.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.06 Exclude every sealed test family and its near duplicates from the training pipeline.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.07 Train with an explicitly chosen ranking loss and document tie handling.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.08 Compare teacher-order imitation against any answer-bearing span objective as separate arms.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.09 Track training loss, dev NDCG, pairwise accuracy, and rank correlation.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.10 Measure inference latency on the target hardware including model load amortization policy.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.11 Compare the student with BM25, same-packing control, and 35B teacher on development only.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.12 Evaluate packing feasibility and output fidelity at every planned budget.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.13 Inspect false positives and omitted evidence without cherry-picking.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.14 Save checkpoint hash, training config, seeds, package versions, and data hashes.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.15 Record failed runs and avoid repeated hyperparameter search until a score improves.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.16 Keep student selection separate from sealed answer results.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.17 Report model size, CPU/GPU memory, initialization cost, and per-query cost.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.18 Reject student if efficiency advantage is absent under the declared end-to-end metric.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.19 Retain a baseline fallback for failed or infeasible student outputs and count fallback use.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 12.20 Document that teacher-family output imitation is not itself evidence of generalization.

**Purpose.** This action exists to make the train and validate the lightweight student evidence scorer work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 12

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 13: Measure controlled latency, cost, and quality-efficiency tradeoffs

**Current status:** PENDING: available timings show the 35B ranker overhead exceeds generation savings; a lightweight speedup is unproven.

**Files and evidence:** backend/scripts/bench/profile_latency.py; backend/data/bench/latency_profile_report.json; docs/research/

**Human input required:** Owner defines acceptable speedup or cost-reduction threshold, target hardware, warm/cold service assumptions, concurrency, and whether power use matters. Infrastructure operator confirms no unrelated load distorts the measurement.

### Ordered execution steps

### 13.01 Freeze the candidate methods and comparison set using development-only rules.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.02 Define whether reported timing includes model load, tokenizer setup, GPU transfer, and queue wait.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.03 Measure uncompressed generation, compressor-only, compressed generation, and combined path.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.04 Run controlled warmups separately from recorded measurements.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.05 Randomize or interleave method order to reduce thermal and load drift.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.06 Use identical inputs, prompts, output caps, decoding, and hardware conditions.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.07 Report median, spread, tail latency, and per-example paired latency differences.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.08 Record GPU utilization, VRAM, CPU use, and concurrent workload.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.09 Measure actual input/output token counts and calculate dated cost components.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.10 Report context and full-prompt retention separately from generated-token savings.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.11 Include 0.75, 0.50, 0.33, and 0.25 only if they were frozen in development scope.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.12 Plot quality against full-system latency and cost rather than compressor latency alone.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.13 Compare student and 35B teacher on identical text and answer-model conditions.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.14 Include setup and amortization sensitivity for one-shot versus reused deployments.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.15 Keep failures and slow requests in the timing denominator or report them explicitly.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.16 Confirm the student beats the prespecified efficiency target with uncertainty.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.17 Do not claim speedup from adding component means measured in different conditions.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.18 Save hardware provenance, raw timing events, and analysis code.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.19 Inspect outlier examples and identify whether timeouts/caps are systematic.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 13.20 Do not change serving defaults based on development latency alone.

**Purpose.** This action exists to make the measure controlled latency, cost, and quality-efficiency tradeoffs work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 13

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 14: Run one sealed confirmatory evaluation after all freeze gates pass

**Current status:** PENDING AND BLOCKED ON FRESH DATA, HUMAN VALIDATION, POWER, PROTOCOL FREEZE, MODEL CALIBRATION, AND INFRASTRUCTURE.

**Files and evidence:** backend/data/bench/test_sealed_inputs.jsonl; docs/research/PREREG.md; backend/scripts/bench/eval_final_paper.py; backend/data/bench/final_confirmatory_evaluation_report.json

**Human input required:** Study owner signs the freeze checklist. Sealed-set custodian confirms hashes and access log. Human annotators complete eligibility labels before sealing. Owner explicitly authorizes compute/cost if outside the already approved free/local budget.

### Ordered execution steps

### 14.01 Check that the sealed data were source-disjoint, human-validated, and never used for development.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.02 Verify the preregistration, code commit, environment, prompts, models, tokenizers, and manifests are frozen.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.03 Verify a sample-size target and primary hypotheses were set without sealed outcome access.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.04 Verify every baseline and control passed its development sanity checks.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.05 Verify model licenses and required privacy restrictions permit the run.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.06 Verify exact native-token packing and denominator rules are implemented for each answer family.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.07 Verify the shared GPU lock and bounded run budget are active.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.08 Hash sealed inputs, labels, code, config, and model artifacts before inference.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.09 Run the frozen evaluator exactly once with explicit state, logging, and no automatic retries.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.10 Resume only from saved per-record state after infrastructure failures, without changing any result policy.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.11 Preserve malformed, truncated, empty, failed, and invalid answers in the frozen denominator.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.12 Record all unexpected deviations and stop if they change the protocol.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.13 Keep labels inaccessible to method-selection code until all raw predictions are complete.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.14 Compute paired passage-clustered intervals and multiplicity corrections using frozen code.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.15 Report primary results before secondary subgroup and exploratory analyses.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.16 Compare candidate with original, BM25, LLMLingua-2, XProvence, and matched controls as frozen.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.17 Report answer quality, budget misses, context/full prompt/output tokens, latency, and cost.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.18 Break out human-validated quality strata and all exclusion counts.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.19 Have a second analyst independently reproduce summary tables from raw records.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 14.20 Classify claims as supported, not supported, inconclusive, or invalidated by protocol deviations.

**Purpose.** This action exists to make the run one sealed confirmatory evaluation after all freeze gates pass work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 14

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Work package 15: Archive evidence, reproduce analyses, and prepare the paper/thesis account

**Current status:** PARTLY COMPLETE: 7 Nov evidence archive is verified for prior runs; the new campaign archive and paper/thesis interpretation remain future work.

**Files and evidence:** backend/scripts/bench/archive_evidence.py; backend/data/bench/evidence_release_20261107.json; docs/progress/AGENT_LOG.md; thesis_latex/Chapters/; paper_router/main.tex; docs/research/

**Human input required:** Owner chooses thesis scope, submission audience, author contributions, venue/deadline, and whether limited or negative results justify a paper. Human coauthors review annotation interpretation, licensing, and all claims before release.

### Ordered execution steps

### 15.01 Reuse the verified 7 Nov release receipt for existing campaign evidence rather than repeating it.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.02 Create a new campaign-specific archive containing raw outputs, configs, scripts, logs, and manifests.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.03 Compute SHA-256 hashes and verify archive contents against a manifest.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.04 Ensure credentials, private keys, user data, and prohibited model assets are excluded.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.05 Check source dataset license and attribution requirements for every included artifact.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.06 Reproduce all reported tables and figures from archived raw evidence with committed scripts.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.07 Verify the result report states failures, invalid outputs, empty outputs, and exclusions.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.08 Report both positive and negative findings and avoid an unsupported superiority narrative.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.09 Update the literature review with primary-source claims and a documented search scope.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.10 State the contribution as a tested hypothesis, not a guaranteed novelty claim.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.11 Keep router certification evidence separate from compressor-quality claims.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.12 Write methods with exact data, grouping, human annotation, prompts, models, and budget details.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.13 Write results with cluster counts, paired intervals, multiplicity, and power limitations.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.14 Write efficiency with compressor plus generation time and separate token categories.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.15 Write limitations covering exposure, model-family independence, language scope, and cost.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.16 Prepare figure/table sources so every number traces to a saved artifact and script.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.17 Ask a second researcher to verify a sample of numbers against their source rows.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.18 Update README and roadmap only after the scientific status is confirmed.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.19 Append no more than six concise handoff lines with status, evidence paths, and next step.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### 15.20 Do not push or publish anything unless separately requested.

**Purpose.** This action exists to make the archive evidence, reproduce analyses, and prepare the paper/thesis account work auditable and prevent the result from being inferred from an unchecked box.

**Procedure.** Make the change only on the designated development or preparation path; preserve raw inputs, record the responsible person and date, and keep a machine-readable trace from the decision to its output.

**Record.** Save the exact file, hash, count, decision, or failure named in this work package. If a prerequisite is absent, mark the step blocked and state the missing input rather than fabricating a result.

**Completion check.** A reviewer should be able to repeat the action from the recorded inputs and reach the same status without accessing sealed outcomes or relying on undocumented knowledge.

### Completion gate for package 15

Do not mark this package complete until its required human inputs are recorded, every ordered step is either evidenced or explicitly waived with a dated rationale, and the listed artifacts have been reviewed. A failed gate remains a result and must be carried forward; it is not permission to change hypotheses or retry until a preferred result appears.


## Human input register by file

| File or location | Input the researcher/owner must provide |
|---|---|
| `docs/annotation/belebele_cm_verify_500.csv` and completed copy | Row assignments, bilingual judgments, overlap labels, adjudication, and annotation provenance. |
| `docs/research/DATA_CARD.md` | Confirm language/data categories, source licenses, collection provenance, intended scope, and exclusions. |
| `backend/data/bench/splits_manifest.json` | Approve source-family policy, fresh-source identity, split proportions, and sealed-data custodian. |
| `backend/data/bench/power_analysis_report.json` | Select practically meaningful effect, alpha, target power, cluster assumptions, and feasible sample ceiling. |
| `docs/research/PREREG.md` | Approve primary hypothesis, budgets, model snapshots, baseline set, failure policy, multiplicity, and stopping rule before inference. |
| `docs/research/HINGLISH_LITERATURE_2026-10-29.md` or successor | Approve search scope and contribution framing; verify licensing and primary literature before novelty claims. |
| `/home/user/hinglish-research/gpu-campaign.lock` and remote setup | Restore access, coordinate ownership with lab users, and confirm current GPU availability. |
| Model manifests under `backend/data/bench/` | Approve exact Gemma/Qwen/XProvence snapshots, tokenizer, license use, storage, and compute. |
| `backend/data/bench/final_confirmatory_evaluation_report.json` | Study owner signs freeze gate and sealed custodian confirms no prior exposure. |
| Thesis and paper files | Owner selects scope, authorship, deadline/venue, and whether evidence supports submission. |

## Explicit corrections to the TODO

1. **Do not form a sealed test from the existing 900 Belebele items.** They have historical exposure and must stay development/retrospective, even when an item was not selected in one campaign.
2. **Do not describe generated/adapted Hinglish as human-validated.** Blank saved review fields mean human validation remains outstanding unless records are recovered and linked.
3. **Do not claim A.4/A.5 are wholly absent.** Repair tests, phonetic utilities, and lexical tests exist; verify behavior and gaps, then make only specific changes tied to failures.
4. **Do not treat passing tests or 10,000 unlabeled stress records as QA accuracy or semantic-preservation proof.** Obtain human judgments and preserve invalid/empty cases in the relevant denominator.
5. **Do not assume Gemma availability, exact digest, native tokenizer parity, or GPU fit from package size/model card.** Verify them in a bounded smoke run under the lock.
6. **Do not assert that the proposed student will beat latency.** Existing 35B timings are slower end-to-end than original generation; the student must demonstrate the prespecified efficiency target.
7. **Do not start the sealed run before new data, annotation, power, baseline validation, protocol freeze, and infrastructure gates pass.**
8. **Do not make publication or novelty promises.** The outcome may be negative, inconclusive, underpowered, or better framed as benchmark/error analysis.
9. **Do not bundle the router study into compressor evidence.** Preserve its scorer_train/pilot/cert split and separate certification constraints.
10. **Do not repeat the 7 Nov archive task for old data.** Reuse its receipt; archive new evidence separately.

## End-state checklist

- [ ] Fresh, source-family-disjoint Hinglish evaluation data acquired under an approved license.
- [ ] Human annotation completed, agreement and adjudication reported, and source links recorded.
- [ ] Exposure registry and near-duplicate/source-family grouping audited.
- [ ] Sealed set is held by a custodian and absent from training/development artifacts.
- [ ] Power plan identifies a realistic independent-passage target before final evaluation.
- [ ] Compression failure mechanisms are explicitly tested and reported.
- [ ] Retrieval normalization is distinct from source output and gold/options are not leaked.
- [ ] Student train/dev data are group-safe and exclude sealed material.
- [ ] Native tokenizers, prompts, full input counts, output counts, and controls are validated.
- [ ] Preregistration amendment, code, configuration, and model/data hashes are frozen.
- [ ] GPU access and shared lock are verified at run time.
- [ ] Independent answer-family competence and XProvence baseline are measured on development data.
- [ ] Candidate selection occurs on development data only.
- [ ] End-to-end quality, latency, token retention, failures, and cost are reported.
- [ ] Sealed evaluation is executed once under the frozen policy.
- [ ] Raw outputs and derived tables are checksummed and independently reproduced.
- [ ] Paper/thesis text is limited to claims supported by these artifacts.

## Handoff rule

When work begins, update `docs/progress/AGENT_LOG.md` with at most six short lines: date/commit, verified result, running job/status/log, evidence path, and next step. Keep status labels explicit. Do not turn this detailed execution document into a substitute for raw evidence or the preregistration.
