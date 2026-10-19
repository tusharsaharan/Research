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

> **Correction (2026-10-19): `tokopt` is not lossless — findings 3 and R2 are withdrawn.**
> Its "same word" test (consonant skeleton + final vowel) merges different words, and the
> cheapest-token target is often an English word. All 63 merges it learned from the
> Hinglish-Instruct corpus change the word (single-annotator check): *kiya→kya* (did→what),
> *abhi→bhi* (now→also), *apni→pani* (own→water), *bechne→bachane* (sell→save),
> *khel→kal* (game→tomorrow), *uspar→superior*, *wahan→when*. This explains why
> CRF+tokopt costs Hinglish 9.3 accuracy points (English words were protected, English only −1.1).
> `tokopt.py` now has `strict=True` (variant_form + a distributional check on the
> Hinglish-Everyday-Conversations corpus), which leaves ~2 merges — i.e. no safe saving.
> Token savings reported for tokopt below are real but came from meaning-changing edits.

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

## Baseline: LLMLingua-2 (added 2026-10-16)

`microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`, run through
the repo wrapper with protected spans forced (`llmlingua2+spans`), keep-rates
0.7 and 0.5, same 8,000 prompts. Token ratios use o200k (the gpt-oss tokenizer).
"Deleted" = digits / option labels no longer present; "reformatted" = same
digits but split ("$5.50" → "$ 5. 50", "10,440,000" → "10, 440, 000").

| Lang | Method | o200k kept | Numbers deleted | Numbers reformatted | Option labels deleted | Negation lost | Question word lost |
|---|---|---|---|---|---|---|---|
| English | crf | 0.970 | 0.1% | 0% | 0.5% | 0.0% | 0.3% |
| English | llmlingua2+spans@0.7 | 0.665 | 0.0% | 13.3% | 26.6% | 23.2% | 64.3% |
| English | llmlingua2+spans@0.5 | 0.473 | 0.8% | 13.2% | 88.1% | 58.9% | 94.9% |
| Hinglish | crf+tokopt[o200k] | 0.942 | 0.1% | 0% | – | 0.4% | 0.2% |
| Hinglish | llmlingua2+spans@0.7 | 0.691 | 0.4% | 7.7% | – | 21.7% | 36.7% |
| Hinglish | llmlingua2+spans@0.5 | 0.503 | 1.0% | 7.7% | – | 57.0% | 73.4% |

Finding 6: LLMLingua-2 compresses 6–10× more than CRF but deletes a negation
in about one in five prompts that contain one at keep-rate 0.7 (both
languages), and most question words. Example: "bhai mera phone kaam nahi kar
raha hai … phir bhi nahi chal raha, kya karun?" → "mera raha Rs. 2,500 charger
liya phir chal raha karun" (meaning inverted). Whether these edits change
answers is what `compress_answers.py` measures; that is the paper's key
compression result (pending, API-limited).

## Guarded LLMLingua-2 (added 2026-10-17)

`guarded@r` (`backend/src/gateway/modules/m2_compressor/guarded.py`): LLMLingua-2
with (1) negations and question words forced to stay, (2) multiple-choice
options kept verbatim (only the stem is compressed), (3) numbers that the
model split restored to their original spelling. Same 8,000 prompts. "Sim" =
mean cosine similarity of multilingual-MiniLM embeddings, original vs
compressed, over changed prompts (`sem_sim.py`).

| Lang | Method | o200k kept | Negation lost | Question word lost | Numbers deleted | Sim | Sim < 0.80 |
|---|---|---|---|---|---|---|---|
| English | crf+tokopt[o200k] | 0.970 | 0.0% | 0.3% | 0.1% | 0.997 | 0.1% |
| English | llmlingua2+spans@0.7 | 0.665 | 23.2% | 64.3% | 0.0% | 0.910 | 2.2% |
| English | guarded@0.7 | 0.784 | 0.0% | 0.0% | 0.0% | 0.936 | 1.0% |
| English | llmlingua2+spans@0.5 | 0.473 | 58.9% | 94.9% | 0.8% | 0.835 | 24.9% |
| English | guarded@0.5 | 0.654 | 0.0% | 0.0% | 0.2% | 0.879 | 12.8% |
| English | guarded@0.4 | 0.595 | 0.0% | 0.0% | 0.5% | 0.840 | 28.0% |
| Hinglish | crf+tokopt[o200k] | 0.942 | 0.4% | 0.2% | 0.1% | 0.969 | 0.6% |
| Hinglish | llmlingua2+spans@0.7 | 0.691 | 21.7% | 36.7% | 0.4% | 0.899 | 4.0% |
| Hinglish | guarded@0.7 | 0.689 | 0.0% | 0.1% | 0.4% | 0.899 | 3.8% |
| Hinglish | llmlingua2+spans@0.5 | 0.503 | 57.0% | 73.4% | 1.0% | 0.812 | 36.2% |
| Hinglish | guarded@0.5 | 0.501 | 0.0% | 0.3% | 1.0% | 0.814 | 35.5% |
| Hinglish | guarded@0.4 | 0.410 | 0.0% | 0.3% | 1.2% | 0.763 | 64.0% |

Finding 7: on Hinglish the guards cost **no compression** (0.501 vs 0.503
kept at r = 0.5) and remove all negation loss and almost all question-word
loss. On English the cost is the verbatim options (0.654 vs 0.473 kept).

Finding 8: **embedding similarity does not see the difference.** Guarded and
plain score the same similarity on Hinglish (0.814 vs 0.812) even though one
deletes negations in 57% of prompts and the other in 0%. Sentence-embedding
similarity — a common "meaning preserved" metric — is blind to negation and
question-word deletion, so it cannot certify compression safety. This
justifies unit-level checks plus answer-level evaluation (pending).

`tokopt` adds nothing on top of guarded@0.5 under o200k (0.498 vs 0.501).

Spot checks (AGENTS.md rule): (a) embedding blindness confirmed directly —
"mera phone kaam nahi kar raha hai" vs the same without "nahi": similarity
0.872, while an opposite-meaning paraphrase scores 0.917. (b) The guarded
number deletions (0.2–1.2%) are real: numbers fused with units were dropped
("5kg aur 7kg" → "5kg aur", "1tbsp", "10am"), because LLMLingua-2 only
protects pure-digit tokens. Fixed 2026-10-17 by forcing every word that
contains a digit; the guarded rows above predate the fix (re-run queued).

## Rate sweep: compression vs meaning-unit loss (added 2026-10-17)

All 8,000 prompts, o200k kept ratio; loss = share of prompts containing the
unit that lose at least one. Guarded rows are pre digit-word fix (guarded2 re-run pending).

| Lang | Rate | Plain kept | Plain neg lost | Plain qword lost | Guarded kept | Guarded neg lost | Guarded qword lost |
|---|---|---|---|---|---|---|---|
| EN | 0.8 | 0.777 | 11.1% | 40.5% | 0.859 | 0.0% | 0.0% |
| EN | 0.7 | 0.665 | 23.2% | 64.2% | 0.784 | 0.0% | 0.0% |
| EN | 0.6 | 0.567 | 43.5% | 83.3% | 0.717 | 0.0% | 0.0% |
| EN | 0.5 | 0.473 | 58.9% | 94.9% | 0.654 | 0.0% | 0.0% |
| EN | 0.4 | 0.384 | 73.4% | 99.0% | 0.595 | 0.0% | 0.0% |
| EN | 0.3 | 0.298 | 82.4% | 99.7% | 0.537 | 0.0% | 0.0% |
| HI | 0.8 | 0.797 | 11.6% | 18.5% | 0.794 | 0.0% | 0.1% |
| HI | 0.7 | 0.691 | 21.7% | 36.7% | 0.689 | 0.0% | 0.1% |
| HI | 0.6 | 0.596 | 37.6% | 56.0% | 0.593 | 0.0% | 0.1% |
| HI | 0.5 | 0.503 | 57.0% | 73.4% | 0.501 | 0.0% | 0.3% |
| HI | 0.4 | 0.411 | 72.5% | 86.1% | 0.410 | 0.0% | 0.3% |
| HI | 0.3 | 0.322 | 81.4% | 94.1% | 0.322 | 0.4% | 0.3% |

Finding 9: plain LLMLingua-2's negation loss grows steadily with compression
(11% → 82% of negated prompts), in both languages. The guards remove it at
every rate; on Hinglish they cost zero compression at every rate (kept ratio
identical to within 0.003). On English the guarded curve flattens below ~0.54
because multiple-choice options stay verbatim.

## Adaptive guarded compression (added 2026-10-18)

`compress_adaptive` (`guarded.py`): per prompt, the most aggressive guarded2
rate in {0.4,…,0.8} whose multilingual-MiniLM similarity to the original is
≥ τ (else the lightest rate). Evaluated offline on 7,647 prompts that have all
five rates (`adaptive_eval.py` → `adaptive_report.json`).

| Lang | Method | o200k kept | Mean sim | Sim < 0.80 | Neg lost | Qword lost |
|---|---|---|---|---|---|---|
| EN | fixed guarded2@0.5 | 0.652 | 0.879 | 12.5% | 0% | 0% |
| EN | adaptive τ=0.85 | 0.654 | 0.896 | 0.2% | 0% | 0% |
| EN | fixed guarded2@0.7 | 0.781 | 0.937 | 1.0% | 0% | 0% |
| EN | adaptive τ=0.93 | 0.769 | 0.941 | 0.2% | 0% | 0% |
| HI | fixed guarded2@0.5 | 0.496 | 0.813 | 36.2% | 0% | 0.2% |
| HI | adaptive τ=0.80 | 0.509 | 0.844 | 0.9% | 0% | 0.2% |
| HI | fixed guarded2@0.6 | 0.589 | 0.859 | 13.6% | 0% | 0.2% |
| HI | adaptive τ=0.85 | 0.591 | 0.881 | 1.0% | 0% | 0.2% |

Finding 10: at matched compression, adaptive rate selection raises mean
similarity by 2–3 points and cuts badly-compressed prompts (sim < 0.80) by
13–40× (e.g. Hinglish 36.2% → 0.9% at ~0.50 kept). At matched similarity it
compresses slightly more. Caveat (important): the selection uses the same
similarity metric it is scored on, and finding 8 shows that metric is blind to
negation — the guards cover negation/question words/numbers, but other content
can still drop (e.g. "phone" in the phone-complaint example). Answer-level
accuracy (Kaggle run) is the real test.

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
