# Recent literature and an independent model family

Checked 2026-10-29. Recommendation: add **Gemma 4 26B-A4B as the answer model** and **XProvence as a multilingual compressor baseline**. These are proposed additions, not measured Hinglish improvements. No downloads or inference runs were started in this review.

## Papers that change our next experiment

| Paper | What it contributes | Implication for this project |
|---|---|---|
| [XProvence: Zero-Cost Multilingual Context Pruning for Retrieval-Augmented Generation](https://arxiv.org/abs/2601.18886), 2026; author model card lists ECIR 2026 | Adds a pruning head to a multilingual reranker, jointly encoding question and passage. | Highest-priority missing learned baseline. Multilingual query-aware extraction and teacher-labelled pruning already exist; those alone are insufficient novelty. “Zero-cost” means integration into an already-required reranker, not free standalone compression. |
| [Lost in Compression: A Controlled Cross-Lingual Audit of Extractive Prompt Compressors](https://arxiv.org/abs/2608.26175), 2026 preprint | Audits cross-language compression under target-tokenizer budgets with full, absent and shuffled context controls; documents transfer and silent over-compression failures. | Direct overlap with a generic multilingual compression audit. Add no-context and shuffled-context controls to distinguish retained evidence from answer-model knowledge. Its monolingual parallel-language evaluation does not establish Roman Hinglish performance. |
| [IterCOMP: Reasoning-aware Adaptive Prompt Compression for Multi-hop Question Answering](https://aclanthology.org/2026.acl-long.1559/), ACL 2026 | Iteratively selects evidence, checks answerability and generates follow-up questions. | Preserve dependencies among evidence spans; selecting individually relevant spans is already a known limitation. Its iterative reasoning cost must be included if used as a comparator. |
| [DisComp: A Two-Stage Prompt Optimization Framework Combining Task-Agnostic and Task-Aware Compression](https://aclanthology.org/2025.findings-naacl.58/), Findings NAACL 2025 | Distils summarization into a smaller model, then prunes sentences using query relevance. | A cheap distilled compressor needs a specific demonstrated contribution beyond distillation plus relevance ranking. |
| [EXIT: Context-Aware Extractive Compression for Enhancing Retrieval-Augmented Generation](https://aclanthology.org/2025.findings-acl.253/), Findings ACL 2025 | Classifies sentences with their surrounding context and supports parallel extraction. | Relevant comparator for dependency preservation and total latency; avoid treating isolated-sentence ranking as the strongest alternative. |
| [Evaluating Cross-lingual Knowledge Consistency in Code-Mixed vis-a-vis Indian Languages using IndicKLAR](https://aclanthology.org/2026.findings-emnlp.1655/), Findings EMNLP 2026 | Native-speaker-verified aligned knowledge queries include code-mixed variants and expose language-dependent recall. | Useful for language-competence controls and annotation design. Knowledge recall is not passage-grounded compression QA; do not substitute it for a fresh context benchmark. |

Also relevant: [CAVEWOMAN](https://aclanthology.org/2026.emnlp-main.1235/), EMNLP 2026, separates accuracy, response semantic agreement and realized cost under linguistic compression. Its findings motivate separate evidence-preservation and cost measurements; they are not directly transferable effect sizes for our extractor.

Review depth: inspected XProvence and Lost in Compression full-text method sections, IterCOMP and DisComp PDF material, and official publication abstracts for EXIT, IndicKLAR and CAVEWOMAN. The last two PDFs were unavailable through the browsing tool. This is a targeted shortlist, not an exhaustive systematic review or a confirmed novelty assessment. Published claims above are attributed to their papers, not reproduced locally.

## Concrete model choices

**Independent answer family: `google/gemma-4-26B-A4B-it`, locally `gemma4:26b`.** Google's [model card](https://ai.google.dev/gemma/docs/core/model_card_4) describes a multilingual MoE with approximately 25.2B total and 3.8B active parameters, configurable thinking and Apache 2.0 licensing. This is a separate developer/model family from Qwen; independent training-data provenance is not established. General multilingual support does not prove Hinglish competence.

The [Ollama listing](https://ollama.com/library/gemma4:26b) currently shows a **19 GB Q4_K_M llama.cpp package**, short identifier `001e5dafc3c7`; its separate MLX package is not the CUDA target. This is a plausible fit for our recorded 32 GB RTX 5000 Ada at bounded context, **an estimate pending a GPU smoke test**. Download bytes are not total VRAM usage. KV cache, runtime, projector/draft components and other users consume additional memory. Freeze the full resolved digest and runtime configuration before evaluation; the tag and short identifier are not a complete immutable manifest. [Google's original weights](https://huggingface.co/google/gemma-4-26B-A4B-it) identify the upstream model.

**Independent compressor baseline: `naver/xprovence-reranker-bgem3-v2`.** Its [author card](https://huggingface.co/naver/xprovence-reranker-bgem3-v2) identifies a BGE-M3/XLM-R-based pruner with Hindi among its training languages. Training examples are monolingual, so Roman code-mixing remains an empirical question. Keep [v1](https://huggingface.co/naver/xprovence-reranker-bgem3-v1) as a separately labelled sensitivity check if budget permits: the cross-lingual audit reports version-specific empty-output behavior. Choose versions before testing, not by whichever wins. Cards label the license CC BY-NC-ND 4.0; verify the pinned license file before adaptation or redistribution. Review and pin its custom loading code before execution.

## Research decision

The defensible hypothesis to investigate is **whether a cheap Hinglish extractor preserves answer-bearing negation, quantities and clause relationships across spelling variation better than strong multilingual pruning at the same serving-token budget**. This is a hypothesis, not a novelty or superiority claim. Existing failure evidence is in [the verified scale-up report](../../backend/data/bench/hinglish_scaleup_full_20261029/RESULTS.md).

Next work, when implementation resumes:

1. Smoke-test Gemma under the shared GPU lock with fixed thinking/output settings, native chat formatting, recorded digest and verified GPU residency. Calibrate uncompressed Hinglish answer parsing before testing compressed conditions.
2. Reuse frozen compressed texts for a clearly labelled **cross-family transfer** check. For strict budget comparisons, separately repack every method using Gemma's verified tokenizer and count the complete rendered prompt. Keep BM25, LLMLingua-2, original and same-packing controls; add XProvence and no/shuffled context. Do not retune our selector on Gemma test answers.
3. Freeze the resulting method and analysis before fresh, source-disjoint, human-validated Hinglish QA. Include spelling/negation/quantity ablations, invalid answers, paired passage-level uncertainty and compression-plus-generation cost. Existing exposed QA can diagnose transfer, but cannot become a fresh test by changing the answer family.

No preregistered settings or serving defaults changed. New downloads and runs remain pending; this review supplies the concrete candidates and rationale.
