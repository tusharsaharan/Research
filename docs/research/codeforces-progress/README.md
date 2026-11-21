# Qwen 35B programming benchmark — progress for supervisor review

**Snapshot: 21 November 2026.** Qwen answered all **700** selected Codeforces problems. The official C++17 queue processed **431**, producing **331 judged submissions** and **100 skips**. Of the judged submissions, **169 were Accepted** and **162 were rejected**. The remaining **269 queue items** have yet to be processed. All 331 recorded submissions came from the dataset’s native train split.

## Objective and setup

Measure how often `qwen3.6:35b` produces a working program for a competitive programming problem, using the official judge as the primary source of verdicts and saved-test checks as supporting evidence. This is an exploratory code-generation benchmark, separate from the Hinglish compressor and router studies.

- **Dataset:** `open-r1/codeforces`, revision `fbe3f6e903ee854eec2e69e9d96d0306cde59baf`. The selected set preserves the native split, **500 train and 200 test**. The split labels identify the source partitions. Qwen received no fine-tuning in this experiment.
- **Selection:** first eligible rows in source order, excluding duplicate IDs, aliases, identical normalized statements and two already-explored problems (`852/A`, `852/B`). All 700 IDs have a unique contest/index mapping in the dataset. Some mapped pages have restricted languages or unavailable submission forms.
- **Generation:** one independent prompt per problem on the RTX 5000 Ada workstation. The prompt included the statement, formats, constraints and public examples, and requested a complete C++17 solution. Editorials, official tests, and checkers stayed out of the prompts. Temperature 0, seed 42, thinking disabled, context 32,768 and generation cap 8,192 tokens.
- **Provenance:** the original train and test response files were copied to this PC and their SHA-256 hashes matched the workstation copies. The verdict sync audit matched 330 of the 331 official C++ submissions' recorded hashes to the extracted Qwen source. The first submission lacked a journal hash, but the separately saved preparation record matches the extracted code. Eight fresh Kotlin answers were generated using the same model digest and tracked separately.

## Results

| Evaluation | Accepted / passed | Rejected / failed | Unverified or skipped |
|---|---:|---:|---:|
| Official C++17, 431 items processed | 169 Accepted | 162 rejected | 100 skipped |
| Official Kotlin 1.9.21, contest 1958 | 2 Accepted | 6 rejected | 0 |
| Workstation checks, all 700 original responses | 81 passed available tests | 123 failures or resource stops | 496 unverified |

The official C++ acceptance rate is **51.1% among the 331 submissions judged so far**. Coverage is incomplete and all of these submissions are in the native train split. There is no official score for the full set or the test split yet. The Kotlin results reflect fresh generation in another language and should be reported on their own.

The workstation run used isolated compilation and executed saved tests when the output format supported reliable comparison. It did not execute unvalidated generated checkers. The dataset has saved tests for **695/700** problems, **124** test sets marked complete, and **110** generated checkers. Passes apply to the available checks. A resource stop is specific to the local evaluation limits.

| Workstation outcome | Train | Test | Total |
|---|---:|---:|---:|
| Passed available tests | 64 | 17 | 81 |
| Failed a saved test | 29 | 17 | 46 |
| Compilation error | 48 | 24 | 72 |
| Runtime error | 3 | 1 | 4 |
| Resource limit | 1 | 0 | 1 |
| Unverified | 355 | 141 | 496 |

## Current blocker and follow-up

Codeforces reported its **250-submissions-per-day limit** while processing **1197E**, and the account history showed no receipt for that attempt. The user subsequently reported the submission account was disabled. The official run is stopped with the existing receipts intact. Further official judging depends on an approved submission route and account access.

The 100 C++ skips are logged individually. **49** responses lacked an extractable C++ `main`, **25** problems did not offer the selected compiler, **19** submission routes redirected away from the form, and **7** records had a nonstandard interface. Eight of the 25 compiler cases have separate Kotlin results. The remaining **17** need alternate-language follow-up. After the access issue is resolved, reconcile 1197E by submission ID before resuming, then review the skips for eligible judging routes.

## Related work

- **GSM8K:** collected all **8,792** raw responses using the same Qwen model family, 7,473 train and 1,319 test. Both splits were copied and verified. Accuracy was not scored before moving to Codeforces.
- **Comparison answers:** **535** assistant/subagent attempts exist, 417 train and 118 test. Another 150 are pending and 15 Q# tasks were marked unsupported for C++. This collection is partly sample-assisted, has mixed authorship, and has no comparable official score.

## Screenshots and underlying evidence

The screenshots below show locally rendered summaries of saved evidence. The receipt panel also includes submission IDs and the original judge verdicts, which can be checked on Codeforces.

1. [Official judging, skips, and checkpoint](screenshots/01-official-progress.png)
2. [Workstation outcomes and checking coverage](screenshots/02-workstation-results.png)
3. [Representative official receipts and model provenance](screenshots/03-receipts-and-provenance.png)
4. [GSM8K collection and comparison coverage](screenshots/04-related-work.png)

The following artifacts are in the project’s local benchmark data directory:

- [Dataset manifest](../../../backend/data/bench/codeforces700_20261116/manifest.json) and [model generation manifest](../../../backend/data/bench/codeforces700_20261116/qwen_answers_v1/manifest.json)
- [Official verdict sync](../../../backend/data/bench/codeforces700_20261116/official_codeforces_v1/api_verdict_sync.json), [submission journal](../../../backend/data/bench/codeforces700_20261116/official_codeforces_v1/submission_journal.jsonl), and [skip review](../../../backend/data/bench/codeforces700_20261116/official_codeforces_v1/skip_review_after_sync.json)
- [Kotlin journal](../../../backend/data/bench/codeforces700_20261116/alternate_languages_v1/submission_journal.jsonl), [workstation state](../../../backend/data/bench/codeforces700_20261116/qwen_judging_v1/state.json), and [checker inventory](../../../backend/data/bench/codeforces700_20261116/checking_inventory.json)
- [GSM8K completion state](../../../backend/data/bench/gsm8k_20261116/state.json) and [comparison answer status](../../../backend/data/bench/codeforces700_20261116/assistant_answers_v1/collection_status.json)
