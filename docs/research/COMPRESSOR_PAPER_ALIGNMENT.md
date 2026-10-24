# Hinglish compressor: evidence and paper plan

2026-10-24. This is a retrospective audit and prospective development plan, **not a preregistration of results already seen**. The project priority is now compression that preserves downstream answer quality on Roman-script Hinglish at measured token budgets. Router certification is a separate study.

**Verdict: the implementation has improved, but a Hinglish superiority claim is not supported yet.** Budget control, document handling and reproducible GPU evaluation are useful foundations. The strongest recent quality gain is English HotpotQA. Hinglish sentence extraction still loses to BM25, while the earlier measured hybrid is a more promising candidate whose small apparent gain is uncertain.

Evidence: [reproducible audit](../../backend/data/bench/hinglish_research_audit/report.json), [item exposure registry](../../backend/data/bench/hinglish_research_audit/exposure.jsonl), and [audit script](../../backend/scripts/bench/hinglish_research_audit.py). Run `python backend/scripts/bench/hinglish_research_audit.py` from the repository root. The report fingerprints its script, grader, raw inputs/answers/variants, manifests and source reports. No inference or paid API calls are needed. All measured numbers below come from that report; proposed experiments are explicitly future work.

## What the current results actually show

Only Belebele supplies paired English/Hinglish evaluation in the recent pilots. HotpotQA, SQuAD and MeetingBank are English-only here. Historical PRESTO work is a different task and script setting; it cannot stand in for Roman-script Hinglish QA.

Each row below uses 120 Hinglish questions with Qwen2.5-3B. Target means the **fraction of context tokens retained**, counted with the serving tokenizer; questions, options and system text remain outside that context budget. v5 and v7 use different items, so their raw accuracies must not be interpreted as a version-to-version improvement curve.

| Pilot / method | Target kept | Accuracy | Actual context kept | Full input kept | Budget misses |
|---|---:|---:|---:|---:|---:|
| v5 original | 1.00 | 58.33% | 1.000 | 1.000 | — |
| v5 measured hybrid (`bhybrid_v2`) | 0.50 | 57.50% | 0.487 | 0.699 | 1/120 |
| v5 BM25 | 0.50 | 59.17% | 0.453 | 0.675 | 14/120 |
| v5 LLMLingua-2 large | 0.50 | 50.83% | 0.478 | 0.691 | 23/120 |
| v5 measured hybrid | 0.33 | 53.33% | 0.328 | 0.604 | 3/120 |
| v5 BM25 | 0.33 | 52.50% | 0.345 | 0.607 | 42/120 |
| v5 LLMLingua-2 large | 0.33 | 49.17% | 0.309 | 0.590 | 22/120 |
| v7 original | 1.00 | 60.83% | 1.000 | 1.000 | — |
| v7 extraction / bridge | 0.50 | 51.67% | 0.418 | 0.652 | 0/120 |
| v7 BM25 | 0.50 | 58.33% | 0.440 | 0.663 | 10/120 |
| v7 extraction / bridge | 0.33 | 43.33% | 0.283 | 0.571 | 3/120 |
| v7 BM25 | 0.33 | 50.83% | 0.336 | 0.597 | 40/120 |

Bridge and extraction produce the same outputs on these untitled Hinglish passages; they are not two independent successes. The measured hybrid's v5 advantage at 0.33 is only 0.83 percentage points. Its passage-clustered paired 95% bootstrap interval against BM25 spans −7.44 to +9.09 points. There is no convincing win.

BM25's budget overruns make the raw comparisons unsuitable for a fixed-budget claim. Restricting to examples where **both** methods meet the cap does not establish population superiority either: it changes the evaluated sample. It is a diagnostic only. On that subset, v7 extraction minus BM25 is −5.45 points at 0.50 (110 pairs; interval −11.82 to 0.00) and −5.06 at 0.33 (79 pairs; −12.20 to +1.32). These are exploratory intervals from adaptively inspected data, without multiple-comparison correction.

The v7 0.33 candidate retains 57.1% of the **full input**, not 33%. Token savings also exclude generated answer tokens and compressor compute. A paper must report context retention, full-input retention, output tokens and end-to-end latency separately.

English v7 bridge F1 is 0.5197 versus BM25 0.4190 on HotpotQA at 0.33; the saved no-more-context-token comparison has 56 pairs and delta +0.1591. This supports testing title-link retrieval for multi-hop contexts. Generalization is mixed: SQuAD F1 is 0.6850 versus 0.6915 at 0.33; MeetingBank is 0.5988 versus 0.6435 at 0.50. These English results cannot establish a Hinglish contribution, and open-answer F1 needs factual-error inspection because answer verbosity affects overlap scores.

v8 is **prepared only**, without completed GPU results. Its structural policy is not validated. The gateway default should not be promoted on the strength of this audit.

## Evidence problems to resolve before a paper claim

**Passage overlap and previous test exposure.** The 900 Belebele items contain 488 unique English passages after whitespace normalization. The old item-hash split places 186 passages in both dev and test; 186 test questions share a dev passage. This violates passage-level independence, even though question IDs differ. v7 has no item-ID overlap with v5, but 18 of its 120 items share v5 passages. Prepared v8 has no item-ID overlap with v7, but 2 of its 47 items share v7 passages. Exact hashing is only a lower bound on source overlap: near duplicates and related source documents need grouping too.

Historical evaluations already cover all 900 items and expose test-oracle summaries. Repartitioning them now cannot create a never-inspected confirmatory test. Keep them as development/retrospective evidence; obtain new sealed source families for a final test, or present an explicitly exploratory paper with the corresponding limitation. The exposure registry records the existing item-level history and passage hashes; it is not a claim that every row was manually inspected.

**Formatting and protocol changes.** Historical uncompressed 3B accuracy is 49.33% Hinglish / 64.78% English, but the grader finds 54 / 123 unparseable replies. Manual checks of `bb-566`, `bb-602`, `bb-289` found a concrete failure: a final `B####` or `C####` rather than `#### B` or `#### C`. A narrow retrospective parser sensitivity recovers 34 / 104 such replies, including 17 / 76 correct answers, raising original-only accuracy to 51.22% / 73.22%. This is **not** a uniform regrade of compressed methods; do not compare adjusted originals with unchanged method scores. Preserve the raw outputs, apply any parser revision to every method, and report both grading policies if historical results are used.

Current pilots request only the option letter; historical runs used a reasoning/final-marker protocol. Do not pool those scores or attribute changes between protocols to the compressor. The current v5 Hinglish methods have no invalid MCQ replies, so the earlier parser problem does not explain away the current quality losses.

**Data quality and language scope.** `belebele_cm.py` pairs an adapted code-mixed dataset with English Belebele by row order, matching source link and gold option. That is insufficient to establish semantic equivalence of every passage, question and distractor. The saved item fields lack linked human-verification provenance. Recover any existing annotation records, then audit bilingual answerability, option alignment, naturalness, spelling and code-switch characteristics. Keep natural code-mixed and synthetic/adapted evidence separate. English original accuracy is 90.83% in v5 and 87.50% in v7, versus Hinglish 58.33% and 60.83%; downstream model competence and translation quality must be measured alongside compression loss.

**Old budget and baseline comparisons.** Historical hybrid selection used average CL100K retention with tolerance, whereas recent pilots use per-item serving-token budgets. Historical Hinglish selection did not establish dominance over the large LLMLingua-2 baseline: its selected 0.50 candidate scored 39.15% versus 43.23% for the large model; at 0.33 it selected BM25. Keep these historical results separate from the current protocol. Old defective LongLLML implementations also cannot substitute for a validated baseline.

## Concrete failures and targeted improvements

The audit saves complete passages, variants, answers and token counts for the failure cases. These examples identify mechanisms to test, not evidence that a proposed fix already works.

| Example | Observed failure | Next ablation |
|---|---|---|
| `bb-226` | The question asks which aspect of events time compares. Extraction omits the sentence about comparing **duration**, selecting the general opening instead. Candidate 42/52 tokens; BM25 50/52; both feasible. | Improve sentence relevance across `compare/comparison` and `length/duration`; inspect ranking and budget packing separately. |
| `bb-747` | Extraction drops **garmiyon** and the summer/winter contrast, retaining winter activities; it answers snowfall instead of Indian summers. Candidate 23/23 tokens; BM25 71/23, over budget. | Preserve the answer-bearing time expression and its clause/contrast; compare against a feasible baseline before attributing the score gap. |
| `bb-579` | The compressed text retains the boy, mail counts and post-office apology but damages the agent/action relationship; the answer changes from boy to postman. Candidate 39/39 tokens; BM25 69/39, over budget. | Protect agent–action–object and negation scope, rather than only checking that names, numbers and a negation word survive. |

**First candidate: improve retrieval without rewriting the output.** Use the measured hybrid as the Hinglish starting point, retaining extraction as a baseline. Test character/subword matching and a small human-checked Roman-Hindi variant lexicon in the *ranking representation*; emit the original text unchanged. Compare this with a bilingual sentence scorer. If using MCQ options for retrieval, include all options symmetrically for every comparable method; never the gold answer. Spelling normalization alone will not solve semantic pairs such as length/duration.

**Second candidate: preserve relational clauses under the real cap.** Whole-sentence packing already exists, but oversized top sentences fall back to token thinning. Test clause segmentation and atomic evidence spans at that fallback, including time, contrast, quantifiers and agent/action relations. Do not assume automatic parsing of Roman Hinglish is reliable: audit span boundaries on development examples. Keep hard protection for literal/code content, and expose infeasible budgets explicitly. A budget violation or full-context fallback must remain in the quality/cost report, not disappear from the denominator.

**Third candidate, only if needed: train a small relevance/preservation model.** Use source-disjoint training examples with evidence-span and downstream-answer supervision; estimate label cost first. Compare against the training-free candidates. Teacher explanations or gold answers must never become test-time compressor input. More GPU hours on the same development questions will not resolve independence or novelty.

`tokopt` spelling rewriting remains withdrawn: prior checks found meaning-changing merges. Do not restore “lossless” claims. Word preservation, embedding similarity and negation-word presence are diagnostics, not a semantic guarantee.

## Paper protocol and ordered work

The proposed research question is: **Can query-aware compression with code-mixed relevance and relational-span preservation improve Hinglish answer quality at fixed serving-token budgets, beyond strong generic compression, without erasing its efficiency advantage?** This is a hypothesis, not an established novelty claim.

1. **Repair evaluation first.** Uniformly audit historical grading if those results will be cited. Build source-family grouping across all questions and language variants, retain the exposure registry, and reserve new source-disjoint test data before further selection. Link bilingual verification records. Freeze the answer prompt, parser, tokenizer revision, generation settings, exact-prompt reuse rules and context-limit exclusions.
2. **Run a small paired development experiment.** Compare measured hybrid, retrieval-only normalization, clause-preserving fallback, and their combination on exactly the same examples with a strict-budget BM25 control. These ablations separate retrieval gains from preservation gains. Use 0.50 as the proposed primary retained budget and 0.33 as the compression stress test; freeze that choice before new confirmatory labels. Keep English pairs to test whether improvements are specifically larger on Hinglish. Record all attempted variants.
3. **Strengthen baselines before scaling.** Include uncompressed input, simple truncation/sentence extraction, BM25, both LLMLingua-2 sizes, and a validated query-aware comparator. [LLMLingua-2](https://arxiv.org/html/2403.12968v2), [LongLLMLingua](https://aclanthology.org/2024.acl-long.91/) and [RECOMP](https://arxiv.org/abs/2310.04408) are essential references: multilingual compression, query-aware selection and learned extraction are not by themselves novel. Implementations must pass small evidence-retention and token-budget checks before expensive evaluation. Report native behavior and any shared budget-enforcement wrapper as distinct configurations, with tuning confined to development data. A broader, current novelty review is still required before submission.
4. **Freeze, then evaluate once.** Select one main candidate and baseline configuration on development data. Determine test size by passage-clustered power simulation using development discordances and a predeclared practically useful margin; more nominal questions sharing passages do not provide equivalent evidence. Use a second answer-model family in addition to Qwen; 3B/7B within one family is a size check. Reuse permitted free GPU capacity with exact source/input hashes and quota accounting.
5. **Report the tradeoff, not a single winning cell.** Primary outcome: paired Hinglish answer accuracy at the fixed cap; report passage-clustered intervals and a predeclared multiple-comparison policy. Secondary: paired English interaction, compression loss relative to each language's original, budget compliance, actual full-input/output tokens, compressor + generation latency, and blinded human meaning-preservation judgments. If claiming “no meaningful loss,” preregister a noninferiority margin and test it; a nonsignificant difference is insufficient. Label post-filtered no-more-token subsets as diagnostics.

For a broader dataset claim, add a human-validated Hinglish version of a second task such as multi-hop QA, keeping all translated/source variants in the same split. Do not relabel existing English Hotpot/SQuAD/MeetingBank runs as Hinglish. [Human evaluation of synthetic Hinglish](https://aclanthology.org/2021.inlg-1.34/) supports taking annotation disagreement and language quality seriously; it does not validate our adaptation automatically.

The desired paper contribution is a verified code-mixed failure mechanism, a method addressing it, and source-disjoint quality/efficiency evidence with ablations. If the final method fails to beat the strongest valid fixed-budget baseline, report that outcome and consider a benchmark/error-analysis contribution instead. Venue, deadline and acceptance remain open; neither an English-only win nor an implementation-heavy demo establishes a publishable Hinglish method result.
