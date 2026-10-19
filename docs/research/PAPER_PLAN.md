# Paper plan (2026-10-19)

## Working title
**Translate, Don't Delete: Certified Meaning-Preserving Prompt Compression for Code-Mixed Queries**

## Claim (what our data already supports — KEY_RESULTS A–L)
1. Deletion-based compression loses meaning on code-mixed input beyond what token or
   similarity metrics show: facts (GSM8K/ARC/MMLU, CondaQA), meaning units (Hinglish-TOP
   slots), and tone/intent (human chat messages). Negation guards fix only negation.
2. Hinglish is fragile because every deleted word costs ~2× the accuracy it costs in English
   (dose, not word class); a tokenizer-driven respelling method (tokopt) silently changed words.
3. The real lever is the tokenizer tax: human English versions of the same Hinglish commands
   need 28–33% fewer tokens; a perfect translation also raises 3B accuracy 63.5% → 85.1%.
4. Proposed method: small local translator → cheap fidelity verifier (numbers, options,
   negation, question form, length) → send English if verified, else the original; the
   accept rule is certified per language with Learn-then-Test (accuracy drop ≤ α vs the
   original, finite-sample, δ = 0.1). Cheap meaning signals cannot certify deletion
   (oracle headroom 29%, certifiable ≤ 4%), so the gate is placed on translation instead.

## Closest work and the gap
| Work | What it does | Missing for our setting |
|---|---|---|
| Cross-Lingual Token Arbitrage 2606.03618 | local LLM translates + rewrites coding prompts | romanized code-mixing, meaning verification, guarantee |
| LUAR 2606.02465 | RL-trained model learns when to call a translator | needs training; native-script languages; no cost or guarantee |
| RAAI 2609.04653 | picks target/English/bilingual mode by calibration | no code-mixing, no finite-sample guarantee, no token accounting |
| Success probes 2610.06216 | calibrated multilingual routing probes | no code-mixing, no translation |
| Self-translate 2308.01223, Is Translation All You Need 2403.10258, CoTR 2409.04512 | translate-test helps | no cost lens, no verification, no code-mixed romanized input |
| Telegraph English 2605.04426, Lexical PC 2609.13154, Cross-lingual audit 2608.26175, Referential dangling 2608.04569 | compression quality / failure modes | deletion only; English-centric |
| Tokenizer Tax 2607.24276, Removable vs irreducible tax 2609.00378 | measure the tax | do not convert it into a compression method |

## Experiments still needed (in order)
1. Finish local translation (translate_back.py; shard 2/2 paused for RAM) → verifier stats,
   TOP slot survival, Kaggle answer-level check of translated prompts (3B).
2. Native code-mixed gold sets (removes "our Hinglish is machine-translated" objection):
   Belebele code-mixed (Thanmay/belebele_hin_Latn_codemixed, 900 MCQ, parallel to English
   Belebele) and Hinglish-TOP intent accuracy (gold intent per human query).
3. Translator ablation: Qwen2.5-1.5B (local) vs Qwen2.5-3B/7B (Kaggle) vs a cheap API.
4. Second and third answering models (Qwen-14B on Kaggle; Gemini Flash / GPT mini with billing).
5. Certify the accept rule (LTT, per language) and report total cost incl. translation.

## Venue path
arXiv preprint as soon as 1–2 are done → code-mixing / low-resource workshop (CALCS, LoResLM)
→ ACL Findings via ARR with 3–5 done.
