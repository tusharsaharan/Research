# Hinglish compression research

Primary goal: a defensible research paper on Roman-script Hinglish context
compression. A language-conditional model router and web gateway form a separate
supporting track. Research results, prototype behavior and historical pilots are
not interchangeable.

## Current evidence — 7 November 2026

The strongest completed compressor is an **opt-in Qwen3.6-35B evidence ranker**:
question + numbered source spans -> ranked span IDs -> original-text packing.
The ranker never receives the answer options or gold answer. Implementation:
[`qwen_evidence.py`](backend/src/gateway/modules/m2_compressor/qwen_evidence.py).

The completed development campaign contains **900 questions / 488 source
passages**, 21 conditions and four Qwen answer models: **75,600 answer records**
(including exact-prompt reuse). At the primary 0.50 retained-context target:

| Answer model | Original accuracy | Strict BM25 | LLMLingua-2 large | 35B span ranker |
|---|---:|---:|---:|---:|
| Qwen3.5 4B | 69.11% | 58.67% | 60.44% | 63.44% |
| Qwen3.6 35B | 79.56% | 65.78% | 71.22% | 71.78% |
| Qwen3.8 27B | 83.11% | 68.89% | 72.67% | 75.00% |
| Qwen3.5 9B | 74.22% | 60.78% | 62.22% | 68.11% |

Source: [`verified_review.json`](backend/data/bench/hinglish_scaleup_full_20261029/verified_review.json),
regenerated and checked against raw hashes, scores and token counts on 7 November.
The [full results](backend/data/bench/hinglish_scaleup_full_20261029/RESULTS.md)
retain all budgets, uncertainty and failures. These are **exploratory results**:

- Every QA item has historical evaluation exposure. The 666 questions outside
  the latest selection sources are not a fresh test set.
- All four answer models are Qwen-family; the ranker is from that family too.
- Caps use the Qwen2.5 reference tokenizer. Other models receive fixed-text
  transfer, not their own matched native-token budgets.
- At target 0.50, actual context retention averages 44.8%; full-prompt retention
  is 68.8% for the first answer model. Context savings are not total-system savings.
- The ranker beats strict BM25 and the same-packing lexical control, but its
  advantage over LLMLingua-2 large is less consistent. Paired passage-bootstrap
  intervals are exploratory and unadjusted for multiple comparisons.
- Ranker overhead exceeds measured generation savings. Quality remains below
  uncompressed input; there is no established lossless or end-to-end speedup claim.
- The separate 10,000-text COMI-LINGUA stress study has no QA gold. It exposes
  dropped negations/numbers, clipping and punctuation-only output. Its original
  Roman texts and derived romanizations are separate strata.

The 500-row Belebele annotation sheet and 3,491-row router verification sheet
have no completed human-verification fields in the saved copies. Recover any
external annotations before treating either corpus as human-validated.

## Next research priorities

1. Build the annotation protocol and fresh source-family-disjoint data; reserve
   a sealed test before further selection. Start a small development annotation
   pilot and determine final test size by passage-clustered power simulation.
2. Restore SSH access and inspect shared GPU occupancy. Saved setup evidence
   confirms a 32 GB RTX 5000 Ada and four GPU-tested Qwen models; the bounded
   7 November SSH check timed out, so live availability is unknown.
3. Validate an independent answer family and the pinned XProvence baseline on
   development data. Gemma/XProvence asset pins exist; no completed independent
   family evaluation was found. Use native-token caps for the new comparison.
4. Repair evidence-unit selection and prefix fallback; test retrieval versus
   relational-span preservation separately. Evaluate a cheap student ranker
   against the existing 35B teacher, strong baselines and identical packing.
5. Freeze one candidate, primary budget, hypotheses, failure policy and analysis;
   evaluate once on the fresh human-validated test. Measure full prompts, outputs,
   compression + inference time, and a practical quality/efficiency tradeoff.

This is a prospective plan, not a new preregistration. The working contribution
is code-mixed evidence preservation under spelling variation, negation and
relational dependencies. Generic multilingual pruning or distillation alone is
not an established novelty claim; see the [literature review](docs/research/HINGLISH_LITERATURE_2026-10-29.md).

## Router track

The gateway, learned scorer and per-language certification implementation exist.
Historical paired-GSM8K results and train-only v2 improvements are supporting
evidence, not compressor validation. The selected pair-2 GBM candidate is
uncertified; the pair-1 artifact currently routes all its calibration examples
cheap at alpha 0.10. Preserve the 30/10/60 scorer_train/pilot/cert split and opt-in
v2 policy. Audit model bindings and repeated daily certification before any new
serving claim. See [paired router results](backend/data/bench/router_baselines_table_paired_gsm8k.md).

## Reproduction and project entry points

- [Raw evidence snapshot and checksum manifest](https://github.com/tusharsaharan/Research/releases/tag/evidence-2026-11-07)
  preserve benchmark and legacy router-track data; credentials, runtime/test
  caches and runtime logs are excluded. Dataset licenses remain applicable.
- Extract the snapshot into the repository root, then run
  `python backend/scripts/bench/review_hinglish_scaleup.py --data backend/data/bench/hinglish_scaleup_full_20261029`.
  This verifies saved evidence without model inference.
- [Backend setup](backend/README.md), [benchmark scripts](backend/scripts/bench/README.md),
  [roadmap](docs/progress/ROADMAP.md), [preregistration history](docs/research/PREREG.md),
  [handoff log](docs/progress/AGENT_LOG.md).
- Frontend: `npm run dev:frontend`; targeted tests: `npm run test -- src/lib/__tests__/hinglish.test.ts`.

Older slides, thesis material and study plans describe earlier tasks and stages.
Use the dated evidence above for the current compressor direction.
