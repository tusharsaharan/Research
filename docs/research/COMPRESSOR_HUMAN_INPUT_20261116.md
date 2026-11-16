# Human input for the compressor study

No manual input is needed to run the current GPU comparisons or use the
corrected AI-review spreadsheet. The agent has completed the AI labels. They
are useful development annotations; claiming human validation requires a
person to read and judge the source material themselves.

## Open the completed spreadsheet

[Corrected 500-row workbook](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/belebele_ai_review_corrected.xlsx)

[Current AI-label CSV](C:/Research/docs/annotation/belebele_cm_ai_reviewed.csv)
contains the same current judgments in a small, row-matched text file.

- `Overview`: counts and scope.
- `Review`: final AI labels, supported answers, changed fields, and notes.
- `Sources`: original English/Hinglish text and original answer key.
- `Previous AI`: the earlier AI labels, preserved for comparison.

Do not treat a spreadsheet row number as the permanent identifier. Use the
`ID` in column A, especially after sorting or filtering.

## If you want to personally validate the existing sheet

This step is needed only for a claim that humans checked these translations.
It cannot turn the old questions into a fresh test.

Open [the human-review template](C:/Research/docs/annotation/belebele_cm_review_template.csv).
Make a copy named `docs/annotation/belebele_cm_review_completed.csv`. Keep the
template intact. The following columns are the ones you would edit:

| Column | Enter | Meaning |
|---|---|---|
| `reviewer_a_same_meaning` | `yes`, `partly`, or `no` | Does the Hinglish preserve the passage, question, and choices? |
| `reviewer_a_answerable_same_gold` | `yes` or `no` | Is the original gold still the uniquely supported Hinglish answer? |
| `reviewer_a_natural_hinglish` | `1`, `2`, or `3` | 1: confusing/unusable; 2: understandable but awkward; 3: natural and clear. |
| `reviewer_a_notes` | Your reason | Explain damage, ambiguity, uncertainty, or an incorrect source answer. |

Read both versions and all options. A passage can be broadly similar while a
changed question, option, number, or negation changes the answer. Do not copy
AI labels automatically. Since the AI suggestions have already been shown,
describe your checking as AI-assisted human review rather than blind review.

The [annotation guide](C:/Research/docs/annotation/ANNOTATION_GUIDE.md) defines
the rules in more detail. The [assignment file](C:/Research/docs/annotation/belebele_cm_review_assignments.csv)
identifies the delayed repeat subset. As the sole reviewer, you may measure
your own repeat consistency; this is not agreement between independent people.
Use `reviewer_b_*` only for that later repeat, after saving your first pass.

The current AI pass flags these original answer keys for checking. A flag can
mean ambiguity; it is not proof that the original answer is wrong.

| ID | Initial workbook row | Original gold | Current AI-supported English answer |
|---|---:|---|---|
| bb-421 | 6 | D | ambiguous |
| bb-85 | 16 | A | ambiguous |
| bb-117 | 24 | A | ambiguous |
| bb-320 | 56 | A | ambiguous |
| bb-83 | 141 | B | C |
| bb-883 | 150 | C | ambiguous |
| bb-647 | 272 | C | ambiguous |
| bb-644 | 301 | C | ambiguous |
| bb-846 | 335 | C | A |
| bb-439 | 365 | C | B |
| bb-655 | 431 | C | ambiguous |

Record any personal decisions in `adjudicated_*` and `adjudication_notes`
after saving the individual passes. Keep the original gold and source fields
unchanged. A future corrected dataset should be a new, versioned artifact.
The frozen GPU experiments keep all original rows and gold labels.

## What is genuinely needed for a fresh research test

The current 900 questions were used in earlier experiments. Repartitioning or
reviewing them does not remove that exposure. The remaining human contribution
is a new licensed source pool and bilingual validation of its meaning and gold.

Provide a new UTF-8 JSONL file at
`C:/Research/backend/data/source_pool/compressor_fresh_candidates.jsonl`.
Each line should describe one real question and contain these fields:

| Field | What you supply |
|---|---|
| `id` | A unique ID for the question. |
| `source_family_id` | The same ID for all questions/translations/paraphrases from one source article or related family. |
| `historically_exposed` | JSON `true` if previously used for development/evaluation; otherwise a supported `false`. |
| `source_passage` | The original source passage used to check lineage and duplicates. |
| `context` | The Roman-script Hinglish passage given to the compressor. |
| `question` | The Hinglish question. |
| `options` | Four Hinglish choices in A/B/C/D order. |
| `gold` | The personally checked correct letter. |
| `source_url` | The actual source page or documented original source. |
| `license` | The license and any permission/attribution requirements. |
| `reviewer_id` | Your reviewer name or stable pseudonym. |
| `review_notes` | Meaning/answer checks and any translation or ambiguity concerns. |

Do not invent fresh status, source URLs, licenses, or reviewer identity. Group
related sources together, including mirrored or paraphrased versions. Newly
generated or translated material must be identified as derived/synthetic and
kept distinct from original Roman Hinglish. Do not put gold into compressor
prompts. The answering model may see choices; the question-only compressor may
see only context/question.

Before any new answer-model evaluation, the agent can validate this schema,
audit duplicates, freeze source hashes and exclusions, and use
`backend/scripts/bench/build_source_splits.py` to separate source families.
Sealed gold needs a custodian-controlled location outside ordinary development
access. As the only reviewer, you can hold the gold; disclose that single-person
arrangement and keep it out of any model/method selection.

The saved planning simulation suggests a large independent passage pool may be
needed for a small accuracy improvement: its smallest tested 80%-power counts
are 1,200 and 2,000 passages under two historical comparison assumptions.
Those are planning scenarios, not a guaranteed universal sample requirement.
A smaller available pool should be reported as a pilot with its uncertainty.

## What you do not need to edit

You do not need to change Python code, model weights, GPU settings, benchmark
reports, or the separate router certification. No paid API is required for the
current continuation. Tell the agent when a real new source file or your human
review copy is ready; those are the only files requiring your own judgments.
