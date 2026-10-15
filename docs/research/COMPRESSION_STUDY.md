# Compression study — 8,000 prompts (study C1)

Status: offline token and safety results are final for this run. Answer-level
results (does compression change correctness?) accumulate daily via
`compress_answers.py` and are **pending**. Reproduce:

```bash
python backend/scripts/bench/compress_eval.py --n 8000
python backend/scripts/bench/compress_answers.py --report
```

Raw rows: `backend/data/bench/compress_rows.jsonl` (48,000 rows = 8,000 prompts × 6 methods).

## Prompts

| Source | Language | n |
|---|---|---|
| GSM8K test (math, numeric gold) | English | 1,319 |
| GSM8K test, model-translated (automatic checks passed) | romanized Hinglish | 285 |
| ARC-Challenge test (multiple choice) | English | 1,172 |
| MMLU test sample (multiple choice) | English | 1,000 |
| Hinglish-Instruct (real romanized prompts) | Hinglish 3,350 · English-classified 874 | 4,224 |
| **Total** | | **8,000** |

Tokenizers (offline): Qwen2.5 byte-level BPE, XLM-R SentencePiece (multilingual),
English BERT WordPiece. The serving model's own token counts (gpt-oss, o200k)
come from provider usage in the answer-level check.

## Methods

- `heuristic` — lexicon filler pruning.
- `crf` — the CRF linguistic compressor (protected spans, negation/question guards).
- `tokopt[tok]` — **new**: tokenizer-aware spelling normalisation for romanized
  Hindi. Each word is rewritten to the attested spelling of the *same word*
  (same consonant skeleton and final vowel, ≥ 5 corpus occurrences) that the
  target tokenizer encodes in the fewest tokens. Deletes nothing; never touches
  English words, numbers, names, negations or question words.
- `crf+tokopt[tok]` — both, stacked.

## Results (all 8,000 prompts, after the safety fix below)

Kept ratio = tokens after / tokens before (lower = more compression).

| Language | Method | Qwen2.5 | XLM-R | Numbers kept | Options kept | Negation lost | Question word lost |
|---|---|---|---|---|---|---|---|
| English | heuristic | 0.981 | 1.000 | 100% | 100% | 0.0% | 0.0% |
| English | crf | 0.971 | 0.990 | 99.9% | 99.3% | 0.0% | 0.3% |
| English | tokopt[qwen] | 0.999 | 1.000 | 100% | 100% | 0.0% | 0.0% |
| Hinglish | heuristic | 0.996 | 0.997 | 100% | – | 0.0% | 0.0% |
| Hinglish | crf | 0.954 | 0.956 | 99.8% | – | 0.4% | 0.4% |
| Hinglish | tokopt[qwen] | 0.985 | 0.996 | 100% | – | 0.0% | 0.0% |
| Hinglish | tokopt[xlmr] | 0.996 | 0.994 | 100% | – | 0.0% | 0.0% |
| Hinglish | crf+tokopt[qwen] | **0.940** | 0.952 | 99.8% | – | 0.4% | 0.3% |

Per dataset (Qwen2.5 kept ratio, crf → crf+tokopt): GSM8K-Hinglish 0.932 → 0.914;
Hinglish-Instruct 0.958 → 0.945; GSM8K-English 0.980 → 0.980; ARC 0.959; MMLU 0.968.

## Findings

1. **Compression is small on short task prompts.** Best stacked method saves
   6.0% of Hinglish input tokens and ~3% of English. Filler pruning alone
   saves 0.4% on Hinglish.
2. **Input is only 23–30% of the bill.** On the collected gpt-oss answers the
   prompt is 170 tokens per call, the completion 98 (20b) to 143 (120b) tokens
   including reasoning; with output priced 4× input, input is 30.2% (cheap) and
   22.9% (premium) of cost. So 6% input compression saves ~1.5–2% of cost, and
   even perfect input compression could save at most ~30%.
3. **The optimal spelling depends on the tokenizer.** XLM-R: "mujhe" 1 token,
   "muje" 2; Qwen2.5: 3 vs 2. `tokopt` tuned for Qwen saves 1.5% under Qwen but
   only 0.4% under XLM-R, and vice versa — there is no universal "canonical"
   romanization; it must be chosen per serving model. It is lossless by
   construction and stacks with CRF (adds 1.3–1.8 points on Hinglish).
4. **The CRF compressor altered tasks** (bug, now fixed). Before the fix it
   de-duplicated numeric lists — `arr = [1, 2, 2, 3, 4, 4, 5]` became
   `[1, 2, 3, 4, 5]` in a "remove duplicates" task, `[2, 2] ∪ [3, 3]` became
   `[2, ∪ [3,` — and shortened quoted text ("No, no, no." → "No, no."). Numbers
   were lost in 0.5–0.7% of prompts. Fix: bracketed numeric groups, quoted text
   and arithmetic are now protected spans (`safety_span.py`, regression tests in
   `tests/test_compressor_benchmark_regressions.py`); number loss fell to
   0.1–0.2% with the same compression. Ratio- or BLEU-based evaluation would
   never have caught this: the edits are tiny and the text still reads fine.
5. **Tokenizer tax is a tokenizer choice.** Same GSM8K item, Hinglish vs
   English input tokens: 1.07× (gpt-oss o200k, provider usage), 1.15× (XLM-R),
   1.29× (Qwen2.5), 1.37× (English BERT). Prior Hinglish work measured GPT-2 only.

Measurement notes: "negation" counts strict negations only; the Hinglish
particle "na" (usually a softener, "batao na") is reported separately and is
legitimately dropped as filler. Compressors join lines, so option labels are
checked in order anywhere in the text. On ARC/MMLU, CRF counts as "changed" on
every prompt partly because of that line joining.

## Novel research directions for compression

**R1. Task-altering edits as the safety metric, certified per language.**
Compression papers report ratio and task accuracy on averages. The failures
found here — de-duplicating lists, breaking intervals, editing quotes,
deleting negations — change *what is asked* while leaving the text fluent.
Contribution: a unit-level audit (numbers, structure, negation, question words,
quotes, option labels) and a per-language certificate that the rate of
task-altering edits is ≤ α with confidence 1−δ, using the same fixed-sequence
machinery as the router. Novelty: no compression paper certifies edit safety,
and none audits code-mixed input. Risk: low (data and code exist).

**R2. Tokenizer-targeted orthographic compression (`tokopt`).** A lossless
compressor specific to romanized, non-standardised scripts: choose the spelling
the serving model's tokenizer encodes most cheaply. Claims to test: (a) savings
are model-specific (shown above), (b) accuracy is unchanged — or improves,
because normalising spelling reduces entropy for the model. Pending the
answer-level check. Risk: savings are modest (1.5–2%); strongest as a
component, not a standalone paper.

**R3. Compress the output, not the input (recommended to pursue next).**
Finding 2 says 70–77% of cost is completion tokens, mostly reasoning. The
largest compression lever is therefore per-query reasoning effort (low /
medium / high, or a token budget), chosen per language with the same
certification: the cheapest reasoning budget whose quality loss vs. the
default is certified ≤ α. This reuses the routing pipeline (a third "tier"
axis) and the gold-answer benchmark. Novelty to check before committing:
adaptive thinking-budget work exists for English; certified, per-language
budget selection for code-mixed queries was not found in the October 2026
searches. Risk: medium; needs one extra answer column per effort level.

**R4. Joint compression + routing certificate.** Certify the pair
(compressor setting, model tier) end to end instead of two separate
guarantees. Given finding 2, the gain from the compression axis will be small
unless contexts are long (e.g. PRESTO dialogues with history).

## Next steps

- Answer-level check accumulates daily (≈100 compressed-prompt answers/day on
  the free tier); report accuracy original vs compressed with exact McNemar
  tests per language and dataset.
- LLMLingua-2 baseline needs `pip install llmlingua` plus its ~700 MB
  multilingual checkpoint (not installed on this machine).
- Exact o200k token counts offline need the gpt-oss tokenizer file (a few MB
  download); until then serving-model tokens come from provider usage.
