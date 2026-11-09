# Human review guide for the Hinglish QA pairs

**Status:** protocol draft for human review. No annotation labels are supplied by this guide.

## Important scope limit

The existing `belebele_cm_verify_500.csv` contains 500 adapted English/Hinglish pairs and has historically been evaluated. Reviewing it now can improve development-data quality documentation, but **cannot make it a fresh confirmatory test set**. Keep it labelled exposed/development-only. A later fresh evaluation needs newly sourced source families, their own annotations, and a sealed custodian.

## Before annotation begins

1. The study owner is the sole human reviewer for this round. Use the `study_owner` assignment in `docs/annotation/belebele_cm_review_assignments.csv`; do not enter personal contact details.
2. First review every row in `docs/annotation/belebele_cm_review_template.csv`, filling only `reviewer_a_*` fields. Keep the separate AI suggestion file, model answers, compressor outputs, and benchmark scores closed until this pass is saved and hashed. If the reviewer has already viewed the AI suggestions, disclose that the first pass was not blind to AI recommendations; do not describe the labels as independent of AI assistance.
3. Repeat the fixed 50-row subset in `reviewer_b_*` fields at least seven days later, without viewing the first-pass labels or AI suggestions during the repeat pass. This measures intra-rater stability only; it is not independent review.
4. Preserve `belebele_cm_verify_500.csv` unchanged. The existing working copy was generated with `python backend/scripts/bench/annotation_agreement.py --template docs/annotation/belebele_cm_verify_500.csv --output docs/annotation/belebele_cm_review_template.csv`.
5. The assignment sheet records the deterministic repeat subset and seed. Do not change the subset after inspecting labels.
6. The study owner must approve any eligibility or exclusion rule before filtering rows. The guide does not set a naturalness threshold or decide whether `partly` is acceptable.

## What each label means

Review the English and Hinglish passage, question, options, and gold label together. Use only the values below. If the record cannot be judged, leave the label blank and explain why in the corresponding notes field; do not guess.

### `same_meaning`

- `yes`: the Hinglish passage and question preserve the meaning needed for this item; the options retain the same meanings and distinctions.
- `partly`: some content is altered, omitted, ambiguous, or awkward enough to affect interpretation, while a substantial part remains aligned. Explain the issue in notes.
- `no`: a material meaning change, missing fact, reversed relation, or mismatched question/options is present.

Consider names, dates, numbers, negation, agent/action relations, causal/temporal relations, and scope. Do not mark `yes` merely because the expected answer seems guessable.

### `answerable_same_gold`

- `yes`: using the Hinglish passage and question, the same option identified by `gold` is supported as correct, with no other option made equally defensible by translation damage.
- `no`: the item is unanswerable from the Hinglish version, the gold is no longer supported, or translation damage changes which option is correct.

This label is an annotation of item alignment, not an assessment of whether a language model answered correctly.

### `natural_hinglish`

- `1`: hard to understand or not plausible Roman-script Hinglish for the intended audience; substantial unnatural phrasing or confusing code-mixing.
- `2`: understandable but noticeably awkward, inconsistent, or unnatural in places.
- `3`: clear and plausible Roman-script Hinglish for the intended audience.

Use the intended audience specified by the study owner. Do not penalize a valid spelling variant only because you personally prefer another spelling. Note regional or audience-specific ambiguity.

### Notes

Describe the smallest concrete discrepancy that explains a `partly`/`no`, `answerable_same_gold=no`, low naturalness, or uncertainty judgment. Quote only the short relevant phrase. For an uncertain item, state exactly what needs adjudication.

## Independent review and adjudication

1. Fill `reviewer_a_*` during the first pass and only the assigned `reviewer_b_*` cells during the delayed repeat. The latter is a second measurement by the same person.
2. Save and hash the first-pass file before the repeat pass. Keep both versions and do not overwrite either.
3. Compute agreement on the 50 repeated rows. Report exact agreement and Cohen's kappa as **intra-rater** statistics, never inter-annotator agreement. The script does not decide which labels are correct.
4. After both passes are frozen, compare them and use `adjudicated_*` only to record the final owner decision where a label changed; explain the decision in `adjudication_notes`.
5. Report assigned/completed counts, missing labels, repeat count, exact agreement, intra-rater kappa, and changes after adjudication. Retain confusion counts; kappa may be unstable with rare labels.
6. Any inclusion/exclusion threshold is applied only after the owner approves it and is recorded with row ID and reason. Keep excluded rows in the flow counts.

## Required human work in the current 500-row sheet

The source sheet has the fields `same_meaning (yes/partly/no)`, `answerable_same_gold (yes/no)`, `natural_hinglish (1-3)`, and `notes`; those source fields remain blank. The separate AI file is explicitly provisional and must not be copied into human-review columns. The sole human reviewer fills the two passes as described above. The results remain exposed development data.

The owner must still decide the eligible naturalness rule and whether any `partly` meaning judgments are retained, excluded, or adjudicated. Record those decisions in the dated protocol before filtering or calculating final benchmark scores. A single reviewer cannot provide inter-annotator agreement or independent human validation.

## Reproducible agreement report

After the merged review sheet is complete, run:

```powershell
python backend/scripts/bench/annotation_agreement.py `
  --input docs/annotation/belebele_cm_review_completed.csv `
  --output backend/data/bench/annotation_report.json
```

This report is descriptive. For the single-reviewer workflow, the paired fields are repeated measurements and every kappa must be described as intra-rater. It includes field-level counts, missingness, paired confusion tables, exact agreement, and Cohen's kappa on complete valid pairs. It does not filter rows, infer missing labels, adjudicate disagreements, or establish that the data are independent.
