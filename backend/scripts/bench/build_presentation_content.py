"""Write presentation-ready Markdown from the frozen compressor artifacts.

No inference or statistical refitting. Tables read the saved analysis outputs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from compressor_artifacts import digest

ROOT=Path(__file__).resolve().parents[3]
BENCH=ROOT/'backend/data/bench'


def build(output):
    paths={
        'historical':BENCH/'restored_audit_20261116/verified_review.json',
        'qwen':BENCH/'qwen_student_20261116/analysis/report.json',
        'native':BENCH/'neural_student_20261116/results/combined/report.json',
        'training':BENCH/'neural_student_20261116/results/training_report.json',
        'annotation':BENCH/'gpu_annotation_review_20261116/merged/report.json',
        'native_audit':BENCH/'neural_student_20261116/results/combined/token_replay_audit.json',
        'archive':ROOT/'docs/research/COMPRESSOR_AI_ONLY_ARCHIVE.json',
    }
    data={key:json.loads(path.read_text(encoding='utf-8')) for key,path in paths.items()}
    h,q,n,t,a,audit,archive=[data[key] for key in paths]
    assert h['verified'] and n['status']=='complete' and q['status']=='complete'
    assert a['rows']==500 and not audit['native_cap_misses']
    m=n['metrics'];c=a['counts'];smallest=min(r['holm_p_all_comparisons'] for r in n['comparisons'])
    lines=[]
    def add(text=''):lines.extend(text.strip('\n').split('\n'));lines.append('')
    def table(headers,rows):
        def cell(value):return str(value).replace('|',' / ').replace('\n',' ')
        lines.append('| '+' | '.join(map(cell,headers))+' |')
        lines.append('| '+' | '.join('---' for _ in headers)+' |')
        lines.extend('| '+' | '.join(map(cell,row))+' |' for row in rows);lines.append('')
    def source(key):add('**Evidence:** ['+paths[key].name+']('+paths[key].as_posix()+').')
    add('''# Hinglish Compressor: Presentation Content and Speaker Notes

**Prepared:** 16 November 2026  
**Format:** Markdown only; no PowerPoint or PDF is created by this delivery.  
**Scope:** the compressor study. The separate router study is not evidence for compressor performance.

## How to use this file

Sections labelled "Slide" contain suggested slide text and speaker notes.
There are 15 suggested main slides, followed by complete result tables and Q&A
for backup. The number of slides is a suggestion, not a requirement.
Keep the qualifications next to the numbers they affect. Use the full tables
in backup slides rather than squeezing every row onto the main slides.

All measured numbers below come from saved project artifacts. Explanations
that were not isolated experimentally are identified as hypotheses.

## The central, defensible statement

We implemented and evaluated question-aware context compression for Roman
Hinglish. Large-model evidence ranking produced higher observed compressed-input
accuracy than the configured baselines in Qwen development experiments. It
still lost accuracy relative to full context and introduced overhead. Two
tested student rankers did not establish the intended quality/efficiency gain.
The independent-family experiment did not establish superiority after the
disclosed multiple-comparison adjustment.

The AI-only implementation and fixed experimental study are complete. The
original goal of demonstrating a better, faster compressor was not achieved.

---

## Slide 1 — Evaluating Context Compression for Roman Hinglish

**On-slide text**

Teacher ranking, student distillation, and measured quality–efficiency tradeoffs

Exploratory AI-only development study · November 2026

**Speaker notes**

"We studied whether selecting question-relevant evidence can reduce Roman
Hinglish input length without losing too much answer quality, and whether a
smaller student can replace a large teacher. We report both observed gains and
the parts that did not meet our objective."

Do not add "state of the art", "lossless", "guaranteed" or "faster" to the title.

## Slide 2 — Research objective and actual outcome

**On-slide text**''')
    table(['Objective','Observed outcome'],[
        ['Reduce context tokens','Achieved in the tested compression conditions'],
        ['Improve compressed-input QA over baselines','Higher teacher point estimates; broad superiority not established'],
        ['Retain full-context accuracy','Not consistently achieved'],
        ['Replace the teacher with a cheaper student','Not established by either tested student'],
        ['Demonstrate end-to-end speedup','Not established'],
        ['Produce reproducible implementation and results','Completed within the AI-only exploratory scope'],
    ])
    add('''**Speaker notes**

"Completing the experiment and achieving the performance objective are
different. We completed the first; the combined quality and speed target
remains unmet."

## Slide 3 — Compression pipeline

**On-slide text**

Passage + question → source spans → relevance ranking → token-budgeted packing
→ answer model → accuracy, token and timing analysis

- Teacher ranks source span IDs rather than generating replacement evidence.
- Selected text retains original wording.
- The compressor receives no answer choices or gold answers.
- The answering model receives the question and choices; gold is used for grading.

**Speaker notes**

"Extraction avoids inventing evidence, but it does not guarantee complete
meaning. Removing a negation, a number or one half of a relation can still
change the meaning of the remaining text."

## Slide 4 — Data and experimental scope

**On-slide text**''')
    table(['Component','Size and interpretation'],[
        ['Historical full-pool QA','900 questions / 488 source passages'],
        ['Historical saved answer records','75,600, including exact-prompt reuse'],
        ['Student training','717 questions / 391 exact source groups'],
        ['Student development','183 questions / 97 other exact source groups'],
        ['Independent answer family','Mistral 7B on all 183 development questions'],
        ['AI annotation review','500 rows; no human review'],
        ['Unlabelled stress study','10,000 texts / 80,000 outputs; not QA accuracy'],
    ])
    add('''**Visible qualification**

All existing Belebele examples have historical exposure. Source-group separation
between train and development does not make development a fresh test.

**Speaker notes**

"Four Qwen sizes are one model family. Mistral adds one independent family.
Record counts include multiple conditions and response reuse: we did not have
75,600 independent questions or make that many fresh calls in this continuation.
The groups are exact source-passage groups, not fully audited paraphrase families."

## Slide 5 — Methods and comparison boundaries

**On-slide text**

- Large teacher: Qwen3.6-35B source-span ranking.
- Lexical student: a learned ranker using six relevance/text features.
- Neural student: XLM-R encoder with its last block and ranking head trained.
- Baselines: BM25, LLMLingua-2 large and XProvence.
- Controls: full context, no context and shuffled context.

**Important configuration disclosure**

In the native experiment, the configured LLMLingua-2 call compresses the passage
without receiving the question. Our rankers and XProvence receive the question.
LLMLingua-2 and XProvence outputs then undergo explicit word-boundary clipping
if they exceed the Mistral native-token cap. XProvence uses threshold .3 with
no forced first sentence. These are the pipelines we evaluated, not a
reproduction of either paper's published benchmark setup.

**Speaker notes**

"We compare these configured systems under a context-token cap. Their
information inputs, inference costs and achieved retained lengths differ.
The results do not isolate a uniquely Hinglish algorithmic advantage."

## Slide 6 — Historical teacher results on 900 questions

**On-slide table: accuracy at the 50% context-budget target**''')
    labels={'qwen3.5:4b':'Qwen 4B','qwen3.6:35b':'Qwen 35B','qwen3.8:27b':'Qwen 27B','qwen3.5:9b':'Qwen 9B'}
    table(['Answer model','Full context','Strict BM25','LLMLingua-2 large','Teacher'],[
        [labels[model]]+[f"{cells[key]['accuracy']:.2%}" for key in ['original','bm25_strict@0.5','llml2L_strict@0.5','bqwen35b_span@0.5']]
        for model,cells in h['metrics'].items()])
    gains=[100*(cells['bqwen35b_span@0.5']['accuracy']-cells['bm25_strict@0.5']['accuracy']) for cells in h['metrics'].values()]
    add(f'''**Speaker notes**

"The teacher produced higher observed accuracy than BM25 in all four Qwen
sizes, by approximately {min(gains):.1f}–{max(gains):.1f} percentage points. It also had higher point
estimates than our LLMLingua-2 configuration. Full context remained more accurate."

**Visible qualification:** exposed development; one answer-model family;
Qwen2.5 reference-token budgets. Do not describe this as having surpassed
LLMLingua-2 generally or the Microsoft research paper.''')
    source('historical')
    add('''## Slide 7 — Context savings and full-prompt savings

**On-slide text**

Historical primary condition, first Qwen answer model, approximately:

- Context kept: 44.8%; context reduction: 55.2%.
- Full prompt kept: 68.8%; full-prompt reduction: 31.2%.
- The question, options and instructions remain outside the context-only cap.

**Speaker notes**

"These are different denominators. Removing about 55% of the passage tokens
does not mean saving 55% of the complete input, total inference, money or time.
Output tokens and the compression model also have a cost."

The historical percentages are rounded summaries from the saved audit. A target
is an upper token budget, not a promise that every output retains exactly 50%.

## Slide 8 — What was trained

**On-slide text**

- Supervision: saved teacher span order, without QA choices/gold as training inputs.
- Lexical student: six weights, trained on 27,476 directed ranking comparisons.
- Neural student: existing XLM-R large encoder; last block plus linear head updated.
- Training and development have no exact source-group overlap.
- Each student used one fixed training configuration, without development-score early stopping.
''')
    table(['Neural training detail','Recorded result'],[
        ['Encoder parameters',f"{t['total_encoder_parameters']:,}"],
        ['Trainable block/head parameters',f"{t['trainable_parameters']:,}"],
        ['Epochs / updates',f"2 / {t['steps']:,}"],
        ['Training duration',f"{t['training_seconds']:.2f} seconds"],
        ['Development top-1 teacher agreement',f"{t['teacher_imitation']['top1_teacher_agreement']:.2%}"],
        ['Development NDCG@3',f"{t['teacher_imitation']['ndcg_at_3']:.4f}"],
    ])
    add('''**Speaker notes**

"We did not train a foundation model from scratch or fine-tune every encoder
parameter. Ranking agreement is a teacher-imitation measure; it is not answer
accuracy and does not establish evidence preservation. The neural candidate
was introduced after the lexical student's Qwen result, making this exploratory
development adaptation. The final fixed checkpoint was saved and reloaded."
''');source('training')
    add('''## Slide 9 — Independent-family results

**On-slide table: Mistral 7B, 183 questions, 50% native context cap**''')
    main=['original','teacher_atomic@0.5','bm25_atomic@0.5','llml2_strict@0.5','xprovence_strict@0.5','student_atomic@0.5','student_neural@0.5']
    display={'original':'Full context','teacher_atomic@0.5':'Teacher atomic','bm25_atomic@0.5':'BM25 atomic','llml2_strict@0.5':'LLMLingua-2 strict','xprovence_strict@0.5':'XProvence strict','student_atomic@0.5':'Lexical student','student_neural@0.5':'Neural student'}
    table(['Method','Accuracy'],[[display[key],f"{m[key]['accuracy']:.2%}"] for key in main])
    add('''**Speaker notes**

"The teacher's point estimate is higher than the compressed baselines, but
neither student demonstrates the desired advantage. The full-context Mistral
baseline is only 48.09%, so this is one additional model with modest competence,
not broad validation across strong independent models. Gemma was unavailable
because of the proxy download failure; Mistral was selected before its outputs."

The Qwen full-pool and Mistral tables use different models and slices. Their
absolute accuracies are not a before/after progress curve. Both budgets and
all controls are included in the backup tables below.
''');source('native')
    add('''## Slide 10 — Statistical uncertainty

**On-slide text**

- Comparisons use the same questions, with whole-passage clustering.
- Reported 95% bootstrap intervals are exploratory and unadjusted.
- Holm p-values adjust across the 24 disclosed native comparisons.
''')
    selected=[r for r in n['comparisons'] if r['candidate'] in ['teacher_atomic@0.5','student_neural@0.5'] and r['baseline']=='bm25_atomic@0.5']
    table(['Comparison','Difference, percentage points','95% interval','Adjusted p'],[
        [r['candidate']+' vs BM25',f"{100*r['delta']:+.2f}",f"[{100*r['ci95'][0]:.2f}, {100*r['ci95'][1]:.2f}]",f"{r['holm_p_all_comparisons']:.4f}"] for r in selected])
    add(f'''No native comparison passes adjusted p < .05; the smallest adjusted
p-value is {smallest:.4f}.

**Speaker notes**

"A higher observed percentage is not automatically a reliable improvement.
This experiment did not establish independent-family superiority after the
disclosed correction. Failure to establish a difference also does not prove
that all methods are equivalent. The correction covers these 24 comparisons,
not all historical choices and experiments in the project."

Do not present the displayed confidence intervals as simultaneously adjusted
intervals, or interpret a p-value as the probability that our method works.

## Slide 11 — Timing and practical relevance

**On-slide table: native .50 local component means**''')
    table(['Method','Compression + generation seconds/query'],[
        [display[key],f"{m[key]['compression_plus_generation_seconds_mean']:.4f}"]
        for key in ['original','bm25_atomic@0.5','student_atomic@0.5','student_neural@0.5','teacher_atomic@0.5']])
    add(f'''Original native prompts average **{m['original']['prompt_tokens_mean']:.2f} input tokens**.
This is a short-QA study, not a long-document speed benchmark.

**Speaker notes**

"The measured accounts do not demonstrate a speedup. They include exact-output
reuse, and teacher costs combine historical ranking measurements with current
generation. Setup is separate. This is not an interleaved production latency
or throughput benchmark. Short inputs offer limited prefill savings; ranking
overhead and changed answer lengths may offset those savings. We did not
experimentally isolate the cause or test much longer inputs."

The neural .50 condition averages 12.88 output tokens versus 11.15 for original.
Fewer input tokens do not necessarily mean proportionately less generation work.

## Slide 12 — Failure analysis

**On-slide text**

- Selecting original words does not ensure that their necessary relationships survive.
- Negations, numbers and connected clauses can be removed or separated.
- A model may answer correctly using prior knowledge despite missing evidence.
- Removing punctuation-only outputs can create empty outputs instead.

**Saved example to discuss: bb-428**

The passage connects black clouds with confusion about an apparent eruption.
The lexical student omits the clouds/confusion link and selects the weather-office
option. BM25 retains the clouds/confusion sentence and selects the gold option A.
Full source, choices and actual replies are included in Appendix E.

**Speaker notes**

"This illustrates a failure mechanism; one example is not a population estimate.
In another saved example, bb-246, both compared selections omit the small-river
inflow fact, yet one answer is correct. QA accuracy alone therefore cannot
certify that the required evidence survived."

## Slide 13 — AI review and verification

**On-slide text**''')
    table(['Measure','Recorded count'],[
        ['Reviewed rows',a['rows']],['Rows revised relative to earlier AI labels',a['changed_rows']],
        ['Meaning: yes / partly / no',f"{c['same_meaning:yes']} / {c['same_meaning:partly']} / {c['same_meaning:no']}"],
        ['Same-gold answerable: yes / no',f"{c['answerable_same_gold:yes']} / {c['answerable_same_gold:no']}"],
        ['Native served prompts replay-verified',audit['exact_rendered_prompts_verified']],
        ['Native context-cap violations',len(audit['native_cap_misses'])],
    ])
    add('''**Speaker notes**

"The owner accepted AI-only working annotations. Revising 286 labels is not
proof that 286 mistakes were corrected. We do not claim human validation,
inter-annotator agreement or guaranteed label correctness. Original gold and
frozen QA rows were preserved, rather than filtered to improve accuracy."

There were 497 valid initial GPU reviews; three invalid initial reviews and
other disputed judgments were handled in 30 source-based AI adjudications.
The count of 30 includes the three invalid cases; do not add them as 33.
''');source('annotation')
    add('''## Slide 14 — Completed work and limits

**On-slide text**

Completed: compression/ranking implementations, two trained students, configured
baseline comparisons, AI review, native token checks, raw-output preservation,
replay analysis, figures, checkpoint and internal evidence package.

Limits: exposed development data; AI-only labels; possible source-gold issues;
exact rather than fully audited source families; one modest independent model;
short prompts; limited student configurations; no established speedup or
independent-family superiority.

**Speaker notes**

"The reproducible implementation is a real engineering deliverable. Passing
checks establishes the things those checks test, not research novelty,
production readiness, or semantic correctness. We did not change serving
defaults based on these student results."

## Slide 15 — Conclusions

**On-slide text**

1. Teacher ranking produced promising compressed-input development point estimates.
2. The tested students did not establish the desired quality/efficiency advantage.
3. Actual token savings, answer quality and total compute must be reported separately.
4. Evidence relationships remain a central failure mode in the inspected cases.
5. The experimental study is complete; the original performance objective is unmet.

**Suggested closing statement**

"We implemented and evaluated a question-aware Roman-Hinglish compression
pipeline. Large-model ranking improved observed compressed-input accuracy in
our Qwen development experiments, while retaining an accuracy gap to full
context and adding overhead. The tested students did not reproduce the intended
quality/efficiency advantage. Independent-family and failure analyses limit
the claims we can make. The outcome is a reproducible exploratory study with
documented tradeoffs, rather than a proven faster or superior compressor."

---

## Appendix A — Complete native result table

All methods use 183 development questions. The 50% and 33% labels are context
caps. Original/no-context are common controls. Actual context retention differs
between methods; an equal cap does not mean equal achieved retained length.
Native accuracy uses the original frozen gold labels.
''')
    table(['Condition','Accuracy','Context kept','Full prompt kept','Output tokens mean','Component seconds/query','Invalid','Errors','Empty contexts'],[
        [key,f"{v['accuracy']:.2%}",f"{v['context_retention']:.2%}",f"{v['full_prompt_retention']:.2%}",f"{v['answer_tokens_mean']:.2f}",f"{v['compression_plus_generation_seconds_mean']:.4f}",v['invalid'],v['errors'],v['empty_contexts']]
        for key,v in m.items()])
    add('''Across the combined native cells, 12 capped records and two other invalid
records remain incorrect. These are counts across method cells, not necessarily
14 distinct questions or independent generations. No-context emptiness is an
intentional control, not a compressor failure.

## Appendix B — All 24 native comparisons

Differences are candidate minus baseline accuracy, in percentage points.
Intervals are exploratory paired passage-bootstrap 95% intervals; the p-values
use Holm adjustment across the 24 rows.
''')
    table(['Candidate','Baseline','Difference (pp)','95% interval (pp)','Holm p'],[
        [r['candidate'],r['baseline'],f"{100*r['delta']:+.2f}",f"[{100*r['ci95'][0]:.2f}, {100*r['ci95'][1]:.2f}]",f"{r['holm_p_all_comparisons']:.4f}"] for r in n['comparisons']])
    add('''## Appendix C — Qwen 4B student-development follow-up

This is the 183-question development slice, not the 900-question table.
It uses Qwen2.5 reference-token text budgets, not verified native Qwen3.5 caps.
There are 2,196 saved records: 1,586 historical-archive reuses, 31 within-run
reuses and 579 new calls. These are not 2,196 independent new examples.
''')
    table(['Condition','Accuracy','Invalid','Recorded errors'],[
        [key,f"{v['accuracy']:.2%}",v['invalid'],v['errors']] for key,v in q['metrics'].items()])
    add('All six declared Qwen follow-up comparisons are shown below; the adjustment is separate from the native family.')
    table(['Candidate','Baseline','Difference (pp)','95% interval (pp)','Holm p'],[
        [r['candidate'],r['baseline'],f"{100*r['delta']:+.2f}",f"[{100*r['ci95'][0]:.2f}, {100*r['ci95'][1]:.2f}]",f"{r['holm_p_all_comparisons']:.4f}"] for r in q['comparisons']])
    add('''The historical same-family evidence and these development contrasts do not
become fresh confirmation because a within-family comparison has a small
p-value. Conversely, absence of adjusted significance in the native family
does not justify saying that no numerical difference exists anywhere.

## Appendix D — All historical full-pool conditions

Each cell has 900 questions. These are saved development results under reference
token accounting, including exact-prompt reuse. The following table preserves
all four answer models and all 21 conditions, rather than selecting a favourable
budget. Compression and generation columns are recorded component means; they
are not an all-inclusive production benchmark. Checkpoint and configuration
details remain in the archived manifests.

Method-key legend: `bqwen35b_span` is the teacher ranker;
`llml2L_strict` is the large LLMLingua-2 configuration;
`bspan_bm25` is the saved same-packing lexical control;
`bm25_strict` is the strict BM25 baseline; and `bhybrid_char_clause` is the
historical character/clause hybrid condition. The number after `@` is the
target retained-context fraction, not the percentage removed.
''')
    table(['Answer model','Condition','Accuracy','Invalid','Reference-cap misses','Mean context kept','Mean full prompt kept','Compression seconds','Generation seconds'],[
        [labels[model],key,f"{v['accuracy']:.2%}",v['invalid'],v['reference_budget_misses'],f"{v['mean_context_ratio']:.2%}",f"{v['mean_full_prompt_ratio']:.2%}",f"{v['mean_compression_seconds']:.4f}",f"{v['mean_generation_seconds']:.4f}"]
        for model,cells in h['metrics'].items() for key,v in cells.items()])
    add('''## Appendix E — Saved real failure examples

The cases below are illustrations already saved by the native analysis script.
They are not a representative random sample or additional accuracy evidence.
The text below is taken from the saved records, not newly invented examples.
''')
    for e in n['examples']:
        r=e['source'];add('### '+r['item_id'])
        add('**Original Hinglish context**\n\n'+r['context'])
        add('**Question**\n\n'+r['question'])
        add('\n'.join(f"- {chr(65+i)}: {choice}" for i,choice in enumerate(r['options'])))
        add('**Frozen source gold:** '+r['gold'])
        add('**Lexical-student selection**\n\n'+e['student']['text'])
        add('**BM25 selection**\n\n'+e['bm25']['text'])
        add('**Actual lexical-student reply:** '+e['student_answer']['content'])
        add('**Actual BM25 reply:** '+e['bm25_answer']['content'])
    add('''### Stress-repair tradeoff

The unlabelled 10,000-text stress study separates 2,178 original Roman texts
from 7,822 derived romanizations. On the original-Roman stratum at the .33
budget, a complete-span teacher candidate changed punctuation-only outputs
from 60 to zero, but empty outputs from 27 to 1,464. On the derived stratum,
7,049 outputs became empty. These findings concern this repair policy and
these data. They are not QA accuracy, proof that all atomic selection fails,
or evidence that removing punctuation-only outputs guarantees better semantics.

The candidate was not promoted as a successful repair.

## Appendix F — Questions and honest answers

**Did we beat LLMLingua-2 or Microsoft?**

No general superiority claim is established. Our configured teacher had higher
point estimates in these development runs. The native independent-family
comparison did not establish superiority after the disclosed adjustment.
Information inputs, achieved retained lengths and compute costs also differ.
We did not reproduce and surpass the paper's published benchmark results.

**What is the actual contribution?**

An implemented Hinglish-focused evidence-selection study, teacher/student
comparisons, independent-family/native-token checks, measured cost and failure
analysis, and preserved reproducible artifacts. We do not claim that extraction,
distillation or context compression was invented in this project.

**Did the original objective succeed?**

The implementation and fixed AI-only study were completed. The combined goal
of a better, faster compressor was not established. Administrative closure is
not scientific success or production certification.

**Why did the students underperform?**

Possible explanations include insufficient representations/training and the
mismatch between imitating span order and preserving answer-critical evidence.
We did not isolate causes experimentally; do not present any explanation as proven.
These are two fixed configurations, not evidence that distillation cannot work.

**Why was shorter input not faster?**

Measured component accounts include ranking overhead, and output behavior
changes after compression. The native inputs are short. These are plausible
contributors, not an isolated causal result. Long-document and deployment
throughput performance remain untested.

**Are the 500 labels definitely correct?**

No. They are accepted AI working judgments. There was no human review or
independent human agreement measurement. Owner acceptance does not guarantee
correctness. Eleven original source-gold judgments were flagged, including
ambiguity; those flags were not used to rewrite or filter the frozen QA scores.

**Did native-token verification prove semantic safety?**

No. It checks token counts, caps and exact rendered prompts. Meaning and answer
evidence can still be lost while every token-count check passes.

**Should the tested student replace the current compressor?**

The results do not justify that change. No serving default was changed.
Performance on other workloads would require its own evaluation.

**Can we present this now?**

Yes, as an exploratory implementation and empirical study with mixed/negative
findings. Do not present it as an established superior algorithm, a validated
production system or a guaranteed publication. Assessment depends on the rubric.

**What comes next scientifically?**

Potential separate work includes relation-aware selection, better supervision,
broader independent-model evaluation and long-context timing studies. These
are proposals, not completed results. A future confirmatory claim would need
suitable new validation and a frozen evaluation. No human-review task is being
assigned in this AI-only delivery.

## Appendix G — Claim wording
''')
    table(['Use this wording','Avoid this wording'],[
        ['Higher observed development accuracy for the configured teacher','We beat Microsoft or LLMLingua-2 generally'],
        ['AI-reviewed working annotations; 286 judgments revised','500 human-validated examples or 286 proven errors fixed'],
        ['Approximately 55.2% context reduction in the reported condition','55.2% money saved or 55.2% faster'],
        ['Four Qwen sizes and one additional Mistral family','Five independent model families'],
        ['Exact source-group-separated development; historically exposed','Fresh unseen test set'],
        ['No native comparison passes the disclosed adjusted threshold','The methods are proven equivalent'],
        ['One teacher-prefix cell matches aggregate original accuracy','Lossless compression or identical correct answers'],
        ['Current implementation and AI-only study finalized','Original performance goal or production readiness achieved'],
    ])
    add('''## Appendix H — Figure files and evidence

The existing figures may be used in the later PowerPoint. They are explanatory
views of the saved results, not additional experiments. Keep their scope and
timing/uncertainty qualifications visible.
''')
    for filename in ['native_tradeoff.png','native_student_differences.png']:
        path=BENCH/'compressor_figures_20261116'/filename
        add(f'- [{filename}]({path.as_posix()})')
    add('### Evidence files and checksums')
    table(['Evidence','SHA-256'],[[f'[{key}]({path.as_posix()})',digest(path)] for key,path in paths.items()])
    add(f"The previously finalized internal archive contains {len(archive['files'])} files and is {archive['archive']['bytes']:,} bytes. This new Markdown content file is a separate presentation deliverable; it is not claimed to be inside that older archive.")
    add('''The machine-readable closeout and complete reproducibility record are available at:

- [AI-only closeout](C:/Research/docs/research/COMPRESSOR_AI_ONLY_FINAL.json)
- [Methods and execution record](C:/Research/docs/research/COMPRESSOR_STATUS_20261116.md)
- [Current AI-label CSV](C:/Research/docs/annotation/belebele_cm_ai_reviewed.csv)
- [Final internal evidence archive](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip)

Upstream source/data/model licenses remain applicable. The study archive is
internal and was not publicly uploaded. The router certification study remains
separate. There is no completed fresh sealed confirmation represented here.
''')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(output=str(output),lines=len(lines),historical_cells=sum(len(cells) for cells in h['metrics'].values()),native_cells=len(m),native_comparisons=len(n['comparisons']),sha256=digest(output))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(p.parse_args().output)
