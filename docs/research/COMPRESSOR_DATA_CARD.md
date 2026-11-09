# Compressor study data card: exposed Belebele annotation slice

**Prepared:** 2026-11-09
**Status:** development-only inventory; not a validated benchmark card.

## Dataset covered by this card

This card covers the 500 rows in `docs/annotation/belebele_cm_verify_500.csv`.
Each row contains an English passage, question, choices, and gold option, plus a
Hinglish passage, question, and choices. The source sheet includes blank fields
for same-meaning, same-gold answerability, naturalness, and notes.

The wider historical Belebele campaign evaluated 900 questions grouped under
488 English source passages. The 500-row sheet is a subset, not the full
historical campaign. The 500-row preparation run grouped 500 rows into 372
exact normalized English-passage hashes. These are exact-text groups only;
near-duplicate or shared-source relations still need human review.

## Exposure and permitted use

All 500 rows are marked historically exposed. The preparation manifest sends
all rows to development, with zero train rows and zero sealed rows. No row in
this sheet can serve as fresh confirmatory evidence, regardless of whether its
label is later reviewed.

The original source, translation, and adaptation licenses and redistribution
conditions have not been fully audited in this work. Confirm permission and
attribution from the upstream source before redistributing derived data or
outputs. The current sheet does not record translator identity, translation
date, or a complete source lineage for each adapted passage.

## AI pre-review labels

`docs/annotation/belebele_cm_ai_suggestions.csv` contains 500 row-matched AI
suggestions by Codex, created on 2026-11-09. The file is separate from the
original source sheet and contains no blank rows. Its 307 `yes`, 150 `partly`,
and 43 `no` same-meaning judgments, plus 444 `yes` and 56 `no`
answerability judgments, are provisional model outputs. They are not human
annotations, adjudications, or evidence of inter-annotator reliability.

The suggestions should not be copied into the human-review fields. The
single-reviewer workflow records a first pass and a delayed repeated 50-row
subset; this can measure intra-rater stability only. If the reviewer has
already seen the AI suggestions, report the first pass as non-blind to AI
recommendations.

## Known limitations

- Historical exposure includes prior local evaluation and possible external
  exposure; a clean external-evaluation history is not established.
- Translation provenance and upstream license review are incomplete.
- Exact passage hashes do not find paraphrases, shared source documents, or
  cross-item families.
- The AI judgments can be wrong and have not been independently verified.
- Naturalness is audience- and region-dependent; the intended target audience
  and acceptance threshold remain owner decisions.
- This slice is not guaranteed to represent Hinglish usage beyond this adapted
  benchmark.

## Current counts and files

- Source sheet: `docs/annotation/belebele_cm_verify_500.csv` (500 rows).
- AI suggestions: `docs/annotation/belebele_cm_ai_suggestions.csv` (500 rows,
  0 missing suggestions).
- Human review copy: `docs/annotation/belebele_cm_review_template.csv` (labels
  remain blank).
- Single-reviewer assignment: `docs/annotation/belebele_cm_review_assignments.csv`
  (500 primary assignments; 50 delayed repeats).
- Exposure-only split: `backend/data/bench/belebele_exposed_dev_only/` (500
  development rows; no train or sealed examples).

## Use restrictions for claims

Use the sheet for development diagnostics, annotation-protocol rehearsal, and
exposed-data failure analysis. Do not report AI counts as human-validated
translation quality, use this set to choose a confirmatory-test result, or
call the exposure-only manifest a fresh source-disjoint test. A confirmatory
study needs a new licensed source pool, audited source families, human-checked
labels, a frozen sample-size plan, and an untouched sealed test.
