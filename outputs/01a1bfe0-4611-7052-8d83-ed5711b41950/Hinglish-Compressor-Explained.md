# Hinglish Compressor: What We Did and What the Results Actually Mean

Detailed project explanation | 16 November 2026

## 1. The answer in plain language

We built software that tries to shorten a Hinglish passage by keeping the parts
that seem useful for a question. We then checked whether an AI could still
answer that question correctly after reading the shortened passage.

The strongest approach used a large AI model to choose the useful parts. In
our original Qwen experiments, that approach produced more correct answers
than the particular BM25 and LLMLingua-2 pipelines we ran. However, using the
complete passage still gave better accuracy. The large selection model also
added enough work that we did not demonstrate an overall speedup.

We tried to replace the expensive selection model with two cheaper learned
rankers. Neither established the intended quality-and-efficiency improvement.
Testing on another answer-model family did not establish reliable superiority
over the baselines after accounting for multiple comparisons.

**What we have is a working experimental system, trained candidates, saved
datasets and labels, and a completed evaluation with mixed and negative
findings. We do not have a proven better, faster production compressor.**

The distinction matters: the implementation and the recorded experiments are
finished, but the original performance objective was not achieved. A label
such as "study complete" does not change that result.

## 2. What problem were we trying to solve?

An answering model may receive a passage plus a question. Processing a longer
input takes input-token capacity and may involve a charge in a paid service.
The idea behind context compression is to remove less useful text before
asking the answering model to respond.

For this project, the text is Roman Hinglish: Hindi and English mixed together,
mostly written using the English alphabet. The question is not merely whether
we can delete words. It is whether we can delete words without deleting the
fact, negation or relationship needed to answer the question.

For example, imagine the sentence "Ravi Delhi nahi gaya; woh Jaipur gaya."
If a compressor drops "nahi", the remaining words can change the meaning.
This is an illustrative example to explain the problem, not a measured test
case or a claim about a particular model output.

Our intended result was a system that saved input tokens, kept answer quality
close to the original passage, and cost less total compute or time than simply
using the original passage. We needed to measure all three. Succeeding only
at deleting tokens would not be enough.

### The few technical words used in this report

A **token** is one piece of text counted by a model's text-processing system.
It is not always a complete word. A **context** is the passage supplied to help
answer the question. A **span** is a selected piece of that passage, such as a
sentence or clause. A **ranker** orders spans from more useful to less useful.
A **baseline** is a comparison method. A **checkpoint** is a saved set of model
weights that lets us load the trained model again.

**Accuracy** here means the fraction of multiple-choice questions for which
the model's answer matches the saved correct-option label. That label is called
the **gold answer**. Gold is the scoring reference; it is not a guarantee that
every original dataset label is beyond dispute.

## 3. How the system actually works

The system begins with the full passage and its question. It breaks the passage
into source spans. A ranking method then decides which spans look relevant.
The packing code selects original spans that fit the allowed context-token
budget. Finally, a separate answering model reads the shortened passage,
question and multiple-choice options, and produces an answer.

The **compressor does not receive the answer choices or gold answer**. Otherwise,
it could choose evidence by looking at the answer it was supposed to preserve.
The answering model does receive the choices because this is multiple-choice
QA. Gold is used afterwards for scoring.

Our teacher method selects source wording rather than asking the model to
invent a replacement explanation. That avoids one source of invented evidence,
but it does not guarantee correct meaning. A real source sentence can become
misleading if a necessary neighbouring sentence is omitted.

We evaluated two ways of handling tight budgets. A prefix policy can keep a
shortened beginning when a whole selected span does not fit. An atomic policy
keeps complete eligible spans and may return an empty context if none fits.
The first can break a relationship; the second can remove all evidence. Both
tradeoffs were recorded instead of being treated as automatically safe.

## 4. Which data did we use, and what did we create?

### The main question-answering data

The historical campaign uses the project's Hinglish adaptation of Belebele:
900 questions associated with 488 English source passages. Each item has a
passage, a question, four choices and a saved correct option. The project also
has English/Hinglish pairs for translation checks.

We did not create Belebele from scratch. Nor did this continuation establish
that every Hinglish adaptation is independently human-validated, naturally
written Hinglish. The detailed translation lineage and redistribution terms
are not fully audited in the project data card.

There are fewer passages than questions because several questions can refer
to the same passage. Those questions are related; counting them as completely
independent would exaggerate how much independent evidence we have.

### The data used to train and examine the students

From the saved teacher-ranking data, we created a training/development split:

| Partition | Questions | Exact source-passage groups | Use |
| --- | --- | --- | --- |
| Training | 717 | 391 | Learn how to rank spans |
| Development | 183 | 97 | Measure the trained candidate and run follow-up QA |

All questions from the same exact source group stay on the same side of
this split. That prevents the identical grouped passage from appearing on
both sides. It does not detect every paraphrase, mirrored article or related
source family.

Most importantly, these 900 items had already been involved in earlier project
development and evaluation. The 183-question development subset is therefore
**not a new, never-used test set**. Splitting old data again does not erase its
history. The split is useful for training discipline, but not fresh confirmation.

### The 500-row AI review

We reviewed a 500-row subset containing English/Hinglish passages, questions,
choices and gold labels. This was used to diagnose translation and answerability
issues. It is part of the same historically exposed pool, not another independent
500-question test. Its labels were not used to filter or relabel the frozen QA
results to make them look better.

### The separate stress data

The COMI-LINGUA stress study contains 10,000 text inputs: 2,178 original Roman
texts and 7,822 derived romanizations. Different methods and budgets produced
80,000 saved outputs. These texts do not supply the QA gold needed to calculate
answer accuracy. They help expose empty outputs, punctuation-only outputs and
loss of literal words such as numbers or negations.

Original Roman material and mechanically derived romanizations are different
types of data. Their counts and failure rates must remain separate.

### Why the experiment counts are much larger than the dataset

The historical study has 75,600 answer records because it covers 900 questions,
21 conditions and four Qwen answer models. Some identical prompts reuse a
saved response. This does not mean 75,600 different questions or 75,600 new
independent model generations.

The follow-up Qwen study contains 2,196 records: 183 questions times 12 conditions.
Of these records, 1,586 reuse verified historical replies, 31 reuse replies
within the run and 579 are new calls. The initial Mistral comparison has 2,928
records; adding the two neural-student budget conditions gives 3,294 combined
records. The combined report includes the original Mistral records; it is not
an additional independent repetition of all of them.

## 5. What were the baselines?

We need comparisons to know whether a complicated approach is actually useful.
These methods play different roles:

| Method | What it does and why it is included |
| --- | --- |
| Full context | Keeps the complete passage. It is the quality and timing reference. |
| No context | Provides the question/options without passage evidence. It shows how often the model can answer without that passage. |
| Shuffled context | Uses question-independent source selection/order as a control. It checks whether relevance ranking adds useful information. |
| BM25 | Uses word-based relevance scoring. It is a simple, inexpensive ranking comparison. |
| LLMLingua-2 large | An existing learned compression method; we used its configured large checkpoint pipeline. |
| XProvence | An existing query-aware context-pruning model; included in the native Mistral comparison. |

The most important comparison boundaries are these. In our native run,
LLMLingua-2 compressed the passage without receiving the question, whereas
our rankers and XProvence received it. LLMLingua-2 and XProvence outputs were
also clipped at word boundaries if they exceeded the answering model's token
cap. XProvence used threshold 0.3 and no forced first sentence.

That is the actual setup we evaluated. It is not a reproduction of all settings,
datasets and results in the original LLMLingua-2 or XProvence papers. The
methods also differ in compute cost and achieved retained text length. A higher
number here describes a configured pipeline in this study; it does not prove
that we invented a generally superior compression algorithm.

In particular, we should not say "we beat Microsoft's paper". Who developed a
method is not the statistical question, and our experiment does not establish
that broad claim anyway.

## 6. What did we build and train ourselves?

### The large teacher ranker

The teacher is the existing Qwen3.6-35B model used to rank numbered source spans.
We built the ranking request, validation and budgeted selection pipeline around
it. We did not train the 35-billion-parameter model. Its job in this project is
to supply a useful order for keeping evidence.

The "B" in model names means billions of parameters. Parameters are learned
numbers inside a model; model size is not an accuracy score or a count of
training examples. The "teacher" supplies ranking preferences, while a "student"
is a smaller scoring system trained to imitate those preferences.

This is more computationally demanding than keyword scoring. It may recognize
relevance beyond exact word overlap, but we did not isolate that ability as the
cause of the observed accuracy differences.

### The six-weight lexical student

This student is a small learned scoring rule, not a language model. Its six
features describe word-based relevance, query-word coverage, character overlap,
span length, source position and a causal-language match. It learns how to
combine them to imitate teacher preferences.

We trained it using 27,476 directed pair comparisons. A pair expresses a
teacher preference such as "span A should rank ahead of span B". The training
inputs use question/span text and teacher order, not the correct QA option.

### The neural student

We also adapted a pretrained XLM-R large encoder. A small scoring head reads
its representation of a question/span pair. We trained the final transformer
block and that head, keeping the rest of the encoder's weights fixed.

| Neural training fact | Value |
| --- | --- |
| Encoder size | 558,943,232 parameters, about 559 million |
| Parameters updated | 12,597,249, about 12.6 million |
| Training passes | Two fixed epochs |
| Optimizer updates | 1,718 |
| Recorded training time | 80.55 seconds on the research GPU |

This was a bounded first neural candidate, not an extensively optimized new
model. The neural candidate was introduced after seeing the lexical student's
Qwen development result. That is exploratory development, rather than a single
untouched confirmatory test. Each candidate used a fixed training setup; we did
not keep changing settings and report only a successful retry.

Keeping most weights fixed reduces training work, but those encoder layers
still run during inference. Training only 12.6 million parameters does not mean
that answering-time ranking uses only 12.6 million parameters.

The saved neural checkpoint contains the changed tensors and metadata. It
needs the pinned base encoder to reconstruct the ranker. We verified that the
saved tensors could be reloaded before evaluating it.

### Did the students learn the teacher's rankings well?

On the 183 development questions, the lexical student's top-ranked span matched
the teacher's top span 43.72% of the time. BM25 matched it 45.90% of the time.
The neural student's top-span match rate was 39.34%.

These are agreement-with-teacher figures, not answer accuracies. The teacher
itself is not guaranteed to choose the ideal evidence. We also recorded other
ranking measures, including NDCG@3, but a value near 0.8 on such a ranking metric
does not mean 80% of questions were answered correctly.
NDCG@3 summarizes how closely the top three selected positions match the
teacher's preferred order, giving more importance to earlier positions.

## 7. What did the original 900-question experiment show?

The following table is the main historical comparison at a target of retaining
at most approximately half the context tokens. The percentages are answer
accuracy against the saved gold option.

| Answering model | Full passage | BM25 | LLMLingua-2 | Teacher |
| --- | --- | --- | --- | --- |
| Qwen 4B | 69.11% | 58.67% | 60.44% | 63.44% |
| Qwen 35B | 79.56% | 65.78% | 71.22% | 71.78% |
| Qwen 27B | 83.11% | 68.89% | 72.67% | 75.00% |
| Qwen 9B | 74.22% | 60.78% | 62.22% | 68.11% |

In the first row, the full-passage model answered 622 of 900 questions
correctly. BM25 answered 528 correctly; the teacher answered 571
correctly. The teacher therefore gets 43 more right than BM25 in this condition,
but 51 fewer right than using the complete passage.

Across the four Qwen sizes, the teacher's observed advantage over BM25 is about
4.8 to 7.3 percentage points. Full context is more accurate in every row. The
teacher also has higher point estimates than our LLMLingua-2 configuration,
but the advantage varies: it is only about 0.56 percentage points for Qwen 35B.

The useful finding is that large-model evidence ranking is promising within
these development runs. The stronger conclusion - that it is generally better
than existing compression research - is not established. The data are exposed,
all four answer models are from the Qwen family, and the budgets use a Qwen2.5
reference tokenizer rather than verified native serving tokenizers for every
answer model.

This study reused and audited historical saved evidence. Restoring those files
and reproducing their analysis is different from generating 75,600 new answers
in the latest continuation.

## 8. What happened in the student follow-up experiments?

### Qwen 4B on the 183-question development slice

At the half-context reference budget, the key results were:

| Method | Correct out of 183 | Accuracy |
| --- | --- | --- |
| Full passage | 130 | 71.04% |
| Teacher atomic | 122 | 66.67% |
| BM25 atomic | 101 | 55.19% |
| Lexical student | 97 | 53.01% |

The lexical student did not replace the teacher successfully: it was below
BM25, and well below the teacher. The teacher itself was below full context.

The uncompressed percentage here differs from the 900-question table because
this is a particular 183-question subset. It is not evidence that a new version
of the answering model improved from 69.11% to 71.04%. The neural student was
not evaluated on Qwen in this follow-up; its added QA evaluation was on Mistral.

### Why we also used Mistral

All the original answer models were Qwen-family models, and the teacher was
also Qwen. We therefore added Mistral-7B-Instruct-v0.3 as another answer-model
family. A larger planned Gemma download failed at the college proxy, so the
cached Mistral checkpoint was selected before seeing its QA answers.

For Mistral, the same checkpoint's actual tokenizer counted the text that was
packed and the exact prompts supplied for generation. This is a stronger token
accounting check than transferring text packed with a different reference
tokenizer.

### Mistral at the half-context native budget

| Method | Correct out of 183 | Accuracy |
| --- | --- | --- |
| Full passage | 88 | 48.09% |
| Teacher atomic | 87 | 47.54% |
| BM25 atomic | 76 | 41.53% |
| LLMLingua-2 strict | 77 | 42.08% |
| XProvence strict | 77 | 42.08% |
| Lexical student | 75 | 40.98% |
| Neural student | 68 | 37.16% |

The teacher gets 87 questions correct, versus 76 for BM25, 77 for each of
LLMLingua-2 and XProvence, and 88 with the full passage. The lexical student
gets 75 correct and the neural student gets 68 correct.

Those counts make the observed result easy to see. They do not remove the
uncertainty from a small, related set of questions. The students did not show
the intended advantage, and the statistical analysis did not establish a
reliable teacher advantage in this independent-family experiment.

Mistral's full-context accuracy is only 48.09%. This gives us evidence from
one additional family with modest performance on the task, not proof of
transfer across many strong independent models.

## 9. Why higher percentages did not prove that we won

An experiment reports the result for the questions it contains. With a different
sample of source passages, the observed gap can change. Several questions
also share a passage, so their errors are related.

We compared methods on the same questions and estimated uncertainty by
resampling whole passage groups. We also adjusted the native comparison
p-values because we examined 24 candidate/baseline contrasts. Testing many
contrasts makes it easier to notice an apparently favourable result by chance
if the comparison policy ignores that search.

For the teacher versus LLMLingua-2 at the half-context native budget, the
observed advantage is 5.46 percentage points. Its reported 95% uncertainty
interval runs from -1.08 to +12.09 percentage points. That range crosses zero:
the result is not precise enough to support a confident superiority claim.

For teacher versus BM25, the observed difference is +6.01 points, with an
interval of [0.00, 11.96]. The Holm-adjusted p-value is 0.9621 in the native
24-comparison family. For neural student versus BM25, the difference is -4.37
points, with interval [-10.06, 1.12] and adjusted p=1.0000.

None of the 24 native comparisons passes the selected adjusted threshold of
0.05; the smallest adjusted p-value is about 0.1384. The intervals displayed
in our reports are exploratory, unadjusted bootstrap intervals. The adjustment
is applied to the p-values; we do not claim those are simultaneous adjusted
confidence intervals or that this correction covers all historical project
experimentation.

In simple terms: **we observed differences, but did not establish reliable
independent-family superiority under the disclosed analysis.** This is not
proof that every method is identical, nor is a p-value the probability that
our method works.

The separate Qwen follow-up has some teacher-versus-BM25 contrasts with small
adjusted p-values within its six-comparison family. Those remain same-family,
exposed-development results. We should neither hide them nor turn them into
fresh independent confirmation.

## 10. How much text did we remove?

For the teacher at the historical half-context target, the recorded mean
context kept is about 44.8%. That corresponds to removing about 55.2% of the
context tokens. For the first answer model, mean full-prompt retention is
about 68.8%, or about 31.2% reduction in the full input.

Why are the percentages different? The passage is only one part of the prompt.
The question, choices and instructions remain. A context-token budget does not
remove half of those other parts.

As an explanatory example, suppose a passage takes 1,000 tokens and the rest
of the prompt takes 400. The original prompt is 1,400 tokens. Cutting the
passage to 500 gives a 900-token prompt. That removes half the passage, but
only 35.7% of the complete prompt. These example numbers explain the arithmetic;
they are not another measured experiment.

Methods do not always use every allowed token. A 50% target is a cap, rather
than a guarantee of exactly 50% achieved retention. For instance, at that
native cap the teacher atomic condition retains 45.54% of context, LLMLingua-2
47.05%, and XProvence 39.10%. This matters when comparing their accuracies.

We did not demonstrate a measured percentage reduction in money spent. A paid
service's bill would depend on input/output prices and the extra selection
model, not just the number of passage tokens removed.

## 11. Was the system faster or cheaper in practice?

We did not establish an overall speedup. The native half-context component
accounts are shown below. They add the measured ranking/packing component
and answer-generation component, with historical teacher-ranking cost included
for teacher conditions.

| Method | Approximate seconds per query |
| --- | --- |
| Full passage | 0.3586 |
| BM25 atomic | 0.3928 |
| Lexical student | 0.4018 |
| Neural student | 0.4150 |
| Teacher atomic | 0.8856 |

The uncompressed reference is about 0.359 seconds, versus about 0.415 for
the neural student and 0.886 for the teacher. These accounts do not justify
saying that our compressor made the system faster.

There are important measurement limits. The teacher account combines historical
ranking measurements with current generation. Exact-prompt response reuse is
recorded. Model-loading/setup time is separate. This was not an interleaved,
repeated production throughput benchmark in which every component was timed
fresh for each condition under identical deployment scheduling.

The inputs also matter. The original native prompts average only **266.60
input tokens**. We tested short multiple-choice QA prompts, not long documents
with thousands of input tokens. On such short inputs, there may be little input
processing time to save, while the extra ranker still has to run.

Output behaviour changes too. The original condition averages 11.15 output
tokens, compared with 12.88 for the neural half-context condition. Shorter
input does not force the answer to become shorter or faster.

Limited input savings, extra ranking and changed output lengths are plausible
contributors to the timing result. We did not experimentally isolate which
caused how much of it. Nor does this short-input result prove that compression
would never help on long contexts; that workload was not established here.

## 12. What did the 500-row AI review actually tell us?

The review checked whether the Hinglish version kept the English meaning,
whether the same gold option remained answerable, and how natural the
Hinglish sounded. All 500 rows now have working AI judgments.

The GPU model produced 497 valid initial structured reviews. Three initial
reviews were invalid. A subsequent source-based Codex AI pass handled those
and other disputed judgments on 30 rows in total. The three are included in
the 30; the total is not 33. This was AI checking AI, not independent human review.

"Valid structured review" means the response had the expected fields and passed
the programmed consistency checks. It does not mean that its judgment was
independently shown to be correct.

| Judgment | Final AI counts |
| --- | --- |
| Meaning preserved | 268 yes; 88 partly; 144 no |
| Same gold still answerable | 406 yes; 94 no |
| Naturalness | 13 at level 1; 255 at level 2; 232 at level 3 |
| Rows changed from earlier AI pass | 286 |
| Original source-gold judgments flagged | 11 |

Naturalness level 1 means hard to understand, 2 means understandable but
awkward, and 3 means natural/clear under the review's judgment. Different labels
measure different things: an item can lose some meaning while the same answer
still happens to be supported.

There are 286 revised rows, not 286 independently proven mistakes corrected.
Eleven source-gold judgments were flagged, including ambiguity; a flag does
not prove that the original gold is wrong. The original source/gold fields and
frozen QA denominators were preserved.

These labels are useful working annotations and diagnostics. We cannot give
their true annotation accuracy from this process alone. Proceeding without
human review does not make them human-validated or guaranteed correct. No
human-review task remains assigned in the current AI-only delivery.

## 13. What failed, and what can we reasonably say about the reasons?

### Failure 1: the teacher did not retain full-context accuracy consistently

On all four historical Qwen models at the half-context target, full context
was more accurate than the teacher. Some necessary information was apparently
not available or not usable in the selected evidence. We inspected real cases
of missing facts and relationships; we did not prove that every error has the
same cause.

### Failure 2: the students did not replace the teacher successfully

The lexical student fell below matched BM25 on the Qwen half-context follow-up,
and neither student established an advantage on Mistral. Learning a teacher's
span order is not the same as learning exactly which combination of facts makes
an answer possible. The teacher order can also be imperfect.

Insufficient representations, limited training or that supervision mismatch
could contribute. These are explanations to investigate, not causes proved by
the current experiments. We tested one fixed configuration of each student,
not every reasonable architecture or training strategy.

### Failure 3: reducing text did not demonstrate faster total inference

Running an additional ranker has a cost. The current native workload is short,
and compressed prompts sometimes produce longer answers. Our component accounts
did not show a net speed benefit. We do not have a production timing guarantee.

### Failure 4: one attempted repair traded one problem for another

We tested a complete-span policy intended to avoid broken or punctuation-only
fragments. On the original-Roman stress stratum at the 33% budget:

| Output problem | Earlier output | Complete-span candidate |
| --- | --- | --- |
| Punctuation-only output | 60 | 0 |
| Empty output | 27 | 1,464 |

Those counts are out of 2,178 original-Roman texts. About two-thirds became
empty under that particular candidate/budget. In the separate derived-romanization
stratum, 7,049 of 7,822 outputs became empty.

The method had cleaner-looking fragments but often provided no evidence at
all. We therefore did not promote it as a successful repair. The practical
lesson is that removing a visible formatting failure does not necessarily
improve semantic usefulness. These are stress-data findings, not failure rates
on the different 183-question QA slice.

### Engineering problems that were fixed

GPU lock contention initially stopped a review attempt before any rows were
processed. The other job released the lock; we did not kill it. Missing Python
dependencies also stopped initial setup attempts and were repaired before the
relevant model results were generated. A pinned XProvence asset download needed
a bounded continuation after timeout. The Gemma download remained unavailable
and its failure was retained.

Solving those problems made the experiments run. It did not improve their
scientific result by itself, and setup retries should not be confused with
rerunning evaluations until a score improves.

## 14. A real example of why preserving relationships matters

One saved development item, bb-428, describes earthquake reports, a volcano and
black clouds. A sentence says that the clouds caused confusion about whether
an explosion had happened. Its question asks which thing explains the confusion.
The saved gold is the option referring to black clouds.

The lexical student's selected context keeps earthquake-report information but
omits the clouds/confusion connection. Its actual answer is the option about
the Icelandic weather-office report. BM25's selected text retains the
clouds/confusion sentence and its answer is the black-cloud option.

This is an English explanation of the saved Hinglish example, not a new test
case. It shows a concrete failure mechanism, rather than proving a population
rate. The complete source and actual outputs are in the saved native report.

Another item, bb-246, asks where the Amazon gets water. Both compared selections
omit the final small-river inflow fact, but one model answer is still correct.
That could involve prior knowledge, inference or answer-choice clues; we did
not determine which. It demonstrates why a correct multiple-choice answer alone
does not prove that the necessary passage evidence survived compression.

## 15. What makes these results limited?

**The data are development-exposed.** We have not shown the result on a new,
untouched source-family-disjoint test corpus. The training/development split
controls exact source overlap, but not all historical selection effects.

**The Hinglish labels and translation quality are uncertain.** We have AI
working judgments, not independent human verification. Errors or ambiguity in
the underlying question, translation or gold can affect measured QA accuracy.

**The original answer models share a family with the teacher.** Four sizes of
Qwen are useful checks but not four independent families. The added Mistral run
is only one checkpoint, with modest task accuracy.

**The pipelines have different inputs and costs.** The teacher is question-aware
and expensive. The LLMLingua-2 configuration did not receive the question.
Strict post-clipping also affects baseline outputs. Their point estimates do
not isolate algorithmic novelty or reproduce the original papers' settings.
We also did not establish an advantage unique to Hinglish compared with English;
these are Hinglish-side QA comparisons, not proof of a new language-specific effect.

**The native workload is short.** An average original prompt of about 267 tokens
does not establish performance on long documents. Timing is component accounting,
not a production deployment benchmark, and money saved was not measured.

**The student search was limited.** Two fixed candidates cannot establish that
all lexical ranking or all distillation will fail. The neural encoder is still
substantial even though relatively few parameters were updated.

**We explored many conditions.** The native 24-comparison adjustment is disclosed,
but it does not account for every historical experiment or decision. Our intervals
and conclusions remain exploratory.

**Verification has a limited meaning.** We replayed all 3,294 native served
prompts and found zero native context-cap violations. Twelve capped records and
two other invalid records stayed incorrect. Replaying analysis reproduced its
numbers. These checks support implementation consistency; they do not prove
label truth, semantic preservation, a speedup or state-of-the-art performance.

The answer records include reuse, so these invalid-record counts are counts
across method cells, not necessarily 14 distinct questions or fresh generations.

### What did the sample-size planning contribute?

We also ran a simulation asking how much independent passage data might be
needed to detect a three-percentage-point improvement under specified historical
assumptions. On the tested grid, the smallest sizes reaching 80% simulated
power were 1,200 passages for a BM25 comparison and 2,000 for a LLMLingua-2
comparison, using a conservative per-comparison threshold of 0.025.

Those are planning scenarios, not universal minimum requirements or data we
actually collected. They depend on assumed disagreement patterns and effect
size. The practical lesson is that a small development sample cannot be treated
as decisive evidence of a small improvement. This simulation did not validate
the method or repair the existing data-exposure limitations.

## 16. What do we have that someone can actually use?

We have code for question-aware source selection and token-budgeted packing;
the trained lexical weights; a safely saved neural adaptation checkpoint and
base-model references; fixed experiment runners and analysis scripts; the
500-row working AI-label file and workbook; raw answers and compression outputs;
token/prompt audit receipts; figures; and a checksummed internal evidence archive.

The GPU work ran on the research workstation's RTX 5000 Ada with 32 GB VRAM.
Jobs used the shared lock and explicit time caps. The dataset, checkpoint and
model hashes allow the recorded configuration to be identified again. Full
base-model weights are referenced rather than bundled into the small archive.

These are useful engineering and research artifacts. They are not evidence that
the new student should replace the current serving default. We did not make
that change. Nor do the separate project's router certification results certify
this compressor. Upstream data/model licenses still govern redistribution; the
archive is internal, and no public release is implied.

## 17. Is the project done, and can we present it?

The answer depends on the meaning of "done". The AI-only implementation, fixed
training attempts, recorded comparisons, annotation workflow and reporting are
finished. There is no pending human-review assignment for this delivery.

The original goal - a compressor with an established quality-and-efficiency
advantage - is not finished successfully. The current candidates did not meet
it. Calling the files finalized cannot turn that into a positive result.

You can present this now as a completed exploratory engineering and evaluation
study. You can explain the method, the observed teacher point estimates, the
unsuccessful student hypotheses, the timing result and the limitations. That
is a defensible description of real work.

You should not present it as a generally superior compressor, a proven
improvement over Microsoft's research, a lossless method or a validated
production system. If a course rubric specifically requires an improved
algorithm, our current evidence does not establish that requirement. Publication
or marks cannot be promised from these results.

We did not invent compression, evidence ranking or distillation. Any claim of
algorithmic novelty would need separate literature support and stronger
evidence. The actual contribution here is the implemented study, its specific
Hinglish-focused comparisons, its measurements and its documented failures.

## 18. Our final conclusions, with practical reasons

**Teacher ranking is promising within the tested development setup.** It got
more questions right than the configured compressed baselines in the Qwen
experiments. That supports further investigation; it does not establish broad
superiority, especially given exposure, shared model family and cost differences.

**Full context remains the stronger reference in the primary reported setting.**
Compressing it usually lost answers, and the measured native component accounts
did not show an overall speed advantage. These results do not justify deploying
our student in place of the existing default.

**The tested students did not learn a useful enough replacement.** Their small
size or lower ranking cost is not sufficient if evidence selection makes more
answers wrong. The negative result applies to these fixed models and settings.

**Input length, answer quality and total cost must stay separate.** We removed
passage tokens, but removed less of the full prompt and added selection work.
Output lengths and the original workload size also affect the practical benefit.

**Evidence preservation is a stronger requirement than clean-looking text or
a correct multiple-choice guess.** The saved examples show relationships being
lost, and sometimes correct answers despite missing evidence. Both facts limit
what accuracy and formatting checks alone can establish.

**This is a finished exploratory study with an unmet performance target.** Its
real value is an implemented, reproducible examination of the tradeoffs and
failure modes. It should be described that way, without manufacturing a win.

Possible further research would examine better ranking supervision, preservation
of connected evidence, other independent answer models and long-context timing.
Those are future experiments, not results we already achieved. A stronger fresh
confirmation would be a separate study, not a relabelling of the present data.

## Appendix A. Both budgets in the native Mistral experiment

The same 183 questions appear in every condition. "50%" and "33%" refer to the
context-token cap, not the percentage removed. Original/no-context are common
controls; they were not independently repeated for each budget. Prefix and
atomic teacher packing are shown separately rather than selecting the nicer
result.

| Method | Accuracy at 50% cap | Accuracy at 33% cap |
| --- | --- | --- |
| Full passage | 48.09% | Same control |
| No context | 27.32% | Same control |
| Teacher prefix | 47.54% | 48.09% |
| Teacher atomic | 47.54% | 47.54% |
| BM25 atomic | 41.53% | 40.98% |
| LLMLingua-2 strict | 42.08% | 36.61% |
| XProvence strict | 42.08% | 42.08% |
| Lexical student | 40.98% | 42.08% |
| Neural student | 37.16% | 38.80% |
| Shuffled context | 38.80% | 32.79% |

The teacher prefix condition at 33% happens to match full-context aggregate
accuracy. That does not mean the same questions were answered correctly, that
the answers are equivalent or that compression was lossless.

## Appendix B. Both budgets in the Qwen 4B development follow-up

These are the 183-question reference-token comparisons, not the 900-question
historical table. The neural student was not run in this Qwen follow-up.

| Method | Accuracy at 50% cap | Accuracy at 33% cap |
| --- | --- | --- |
| Full passage | 71.04% | Same control |
| No context | 37.16% | Same control |
| Teacher prefix | 66.67% | 60.11% |
| Teacher atomic | 66.67% | 59.56% |
| BM25 atomic | 55.19% | 53.01% |
| Lexical student | 53.01% | 51.91% |
| Shuffled context | 49.73% | 46.99% |

## Appendix C. All four historical budgets for the three main compressors

The rows below report all four registered retained-context targets, rather than
only a favourable one. Each cell has 900 questions. These are reference-token,
same-family, exposed-development results. The original uncompressed accuracy
is stated once for each model.

### Qwen 4B: full-context accuracy 69.11%

| Context target | BM25 | LLMLingua-2 | Teacher |
| --- | --- | --- | --- |
| 25% | 49.89% | 49.56% | 54.67% |
| 33% | 52.56% | 50.67% | 59.33% |
| 50% | 58.67% | 60.44% | 63.44% |
| 75% | 60.44% | 66.00% | 66.56% |

### Qwen 35B: full-context accuracy 79.56%

| Context target | BM25 | LLMLingua-2 | Teacher |
| --- | --- | --- | --- |
| 25% | 54.11% | 60.22% | 63.00% |
| 33% | 58.00% | 62.44% | 65.78% |
| 50% | 65.78% | 71.22% | 71.78% |
| 75% | 71.44% | 76.56% | 76.33% |

### Qwen 27B: full-context accuracy 83.11%

| Context target | BM25 | LLMLingua-2 | Teacher |
| --- | --- | --- | --- |
| 25% | 58.22% | 61.22% | 66.00% |
| 33% | 63.67% | 64.67% | 71.78% |
| 50% | 68.89% | 72.67% | 75.00% |
| 75% | 75.11% | 79.89% | 79.33% |

### Qwen 9B: full-context accuracy 74.22%

| Context target | BM25 | LLMLingua-2 | Teacher |
| --- | --- | --- | --- |
| 25% | 52.89% | 52.00% | 58.56% |
| 33% | 56.11% | 56.67% | 63.00% |
| 50% | 60.78% | 62.22% | 68.11% |
| 75% | 65.44% | 70.22% | 70.56% |

The full historical study also includes character/clause and same-packing
lexical-control conditions. All 84 model/condition cells are preserved in the
machine-readable historical audit and the earlier full-table content file.
The tables here focus on the main comparisons and are not a replacement for
those raw-derived records.

## Appendix D. Where to find the actual work

| Artifact | What it contains |
| --- | --- |
| backend/src/gateway/modules/m2_compressor/qwen_evidence.py | Teacher ranking requests, source spans and packing |
| backend/src/gateway/modules/m2_compressor/student_ranker.py | Lexical-student features and scoring |
| backend/data/bench/compact_student_20261116/ | Lexical weights and training/development report |
| backend/data/bench/neural_student_20261116/results/ | Neural patch, training results, added answers and combined comparison |
| docs/annotation/belebele_cm_ai_reviewed.csv | Accepted working AI judgments for 500 items |
| backend/data/bench/restored_audit_20261116/verified_review.json | Historical 900-question result audit |
| backend/data/bench/atomic_replay_20261116/report.json | Recorded stress-repair tradeoffs |
| docs/research/COMPRESSOR_STATUS_20261116.md | Detailed methods, failures, execution history and reproduction commands |

The figures and all 24 native comparison intervals are available in the saved
native report. The internal evidence archive is linked below; it contains
the previously finalized study artifacts, not this new explanatory document.

- [Native result report](C:/Research/backend/data/bench/neural_student_20261116/results/combined/report.json)
- [Internal evidence archive](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/compressor_ai_only_final_20261116.zip)
- [Earlier full numerical tables](C:/Research/outputs/01a1bfe0-4611-7052-8d83-ed5711b41950/Hinglish-Compressor-Presentation-Content.md)

This explanation uses the saved experiment artifacts. No new model inference,
new annotation, changed gold or re-scoring policy was introduced to write it.
