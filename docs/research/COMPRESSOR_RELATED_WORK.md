# Hinglish compressor: related-work audit

**Prepared:** 2026-11-09
**Status:** literature notes for study design; not a novelty claim or result section.

## Scope

This note reviews five directly relevant works named in the compressor plan. It is
kept separate from `paper_router/main.tex` and the router thesis chapter: those
files describe the distinct risk-controlled routing study. The proposed Hinglish
compressor study is still exploratory, and its human-validation, fresh-data,
independent-family, native-token, and end-to-end efficiency gates remain open.

## Closest work

### XProvence: multilingual context pruning

Mohamed et al. introduce XProvence as multilingual context pruning for RAG. The
work extends the Provence pruning/reranking approach, trains with multilingual
data, and evaluates across multilingual QA benchmarks. This is the closest
baseline to any broad claim that a query-aware compressor works across
languages. A defensible Hinglish study therefore needs a direct comparison,
under the same passage groups, target-model token accounting, and downstream
answer model. XProvence is not a novelty gap to claim around; it is a required
baseline whose performance on Roman-script code-mixed Hinglish is an empirical
question.

Source: [XProvence: Zero-Cost Multilingual Context Pruning for RAG (arXiv)](https://arxiv.org/abs/2601.18886).

### Lost in Compression: cross-lingual failure audit

Lukauskas audits extractive prompt compressors across ten languages and reports
that compression behavior depends on the language and on the compression
supervision. The paper includes both English-trained systems and a multilingual
pruner, and argues for measuring achieved utilization and downstream behavior
instead of assuming a fixed keep rate transfers uniformly. This rules out a
generic “multilingual compressors fail” framing. The narrower open question is
whether code-mixed Roman Hinglish, with its spelling variation and
English-Hindi relational clauses, has error patterns that the available
multilingual baselines do not handle. That question requires direct evidence;
the present exposed Belebele results do not establish it.

Source: [Lost in Compression: A Controlled Cross-Lingual Audit of Extractive Prompt Compressors (arXiv)](https://arxiv.org/abs/2608.26175).

### IterCOMP: multi-hop evidence dependencies

Yun and Kim propose an iterative, reasoning-aware compression loop for
multi-hop QA. Their approach segments evidence and uses answerability checks
and targeted follow-up questions to retain linked information. It addresses a
failure that one-pass ranking can miss: individually relevant facts may need to
be retained together to support a multi-step answer. A single-pass Hinglish
selector should therefore be scoped to its tested task and dependency length;
it should not imply general multi-hop preservation without a comparable
evaluation. IterCOMP is a relevant comparator if the task is extended to
multi-hop questions.

Source: [IterCOMP: Reasoning-aware Adaptive Prompt Compression for Multi-hop QA (arXiv)](https://arxiv.org/abs/2608.13588).

### DisComp: distillation plus task-aware pruning

Liu et al. describe a two-stage framework: task-agnostic compression through
distillation, followed by query-aware sentence pruning. The paper reports
quality and latency comparisons on LongBench, ZeroSCROLLS, and NaturalQuestions.
This overlaps with the planned lightweight-student direction. A student trained
from a large ranker should be compared against both direct ranking baselines
and a distillation-plus-pruning approach where feasible. Teacher imitation
alone is not evidence that the student preserves answer-bearing Hinglish
relations or improves total serving time.

Source: [DisComp (Findings of NAACL 2025)](https://aclanthology.org/2025.findings-naacl.58/).

### CAVEWOMAN: quality, cost, and reference agreement

Adeyemi et al. evaluate input and output linguistic compression separately,
scoring task accuracy, realized per-item cost, and agreement with an
uncompressed reference. Their reported input-compression results warn that
fewer input tokens do not guarantee lower total cost when the answer expands.
This makes end-to-end measurement essential: count native input tokens, output
tokens, compressor inference, and latency together. Reference agreement is a
useful complementary outcome, but it cannot replace task correctness or
human-validated semantic evidence.

Source: [CAVEWOMAN: How LLMs Behave Under Linguistic Input and Output Compression (arXiv)](https://arxiv.org/abs/2606.24083).

## Consequences for this project

1. State the research question narrowly: whether a frozen question-aware
   selector preserves answer-bearing relations in Roman-script Hinglish under
   measured target-model token caps, and at what quality and total-cost tradeoff.
2. Do not claim novelty for multilingual pruning, query-aware compression,
   distillation, or token-efficiency measurement in general.
3. Treat negation, numbers, agents, actions, causes, temporal relations, and
   cross-language dependencies as predeclared error analyses. Presence of a
   protected literal is only a diagnostic; it does not prove a proposition was
   preserved.
4. Compare XProvence, BM25 with matched segmentation/packing, LLMLingua-2, and
   no-context/shuffled controls on identical source families and answer-model
   prompts. Keep one independent answer-model family outside Qwen.
5. Report context retention separately from full-prompt retention, answer
   tokens, compressor and generation latency, invalid/empty outputs, and total
   inference cost. Do not infer serving speedup from context-token reduction.
6. Keep historical Belebele strictly in exposed development. Confirmatory
   claims require fresh, licensed, source-disjoint Hinglish data with human
   validation and the frozen analysis plan.

## Open checks before citing in a paper

- Verify final venue/version metadata and any published versions for each
  preprint at manuscript freeze.
- Inspect each paper's task, tokenization, and baseline details before making a
  fine-grained comparison; this memo intentionally avoids quoting exact scores.
- Confirm the XProvence checkpoint/license and the permitted use of its outputs
  before running or redistributing the comparison.
- Search for additional 2026 work at the preregistration freeze; this list is
  not an exhaustive systematic review.
