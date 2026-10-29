<!-- LOVABLE:BEGIN -->

> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

<!-- LOVABLE:END -->

# Research quality first; minimize tokens

Primary goal: rigorous **Hinglish compressor research** supporting a possible
paper. Validity and reproducibility outrank token savings. Never promise publication
or manufacture a win. Keep negative findings.

## Minimal context and communication

- Start with this file and the last **6 lines** of `docs/progress/AGENT_LOG.md`.
  Reuse context already read. Read ROADMAP only for planning, and relevant
  PREREG/DECISIONS sections before experiment changes.
- Use `rg`, bounded reads and batched independent queries. Summarize large data
  with scripts; never dump JSONL, full logs or the research library.
- No subagents/separate chats unless explicitly requested. Use the cheapest
  available model adequate for the task; reserve deep reasoning for validity,
  experiment design and paper arguments. Never pretend to switch models.
- Routine checks: state/counts plus a short log tail, once. No polling loops.
  Lead replies with results and a few bullets; link necessary detailed artifacts.
- Honour requested hourly updates in one sentence. Notify failures/completion;
  remove obsolete monitors. Do not repeat plans or earlier analysis.

## Research safeguards — never trade these for fewer tokens

- Focus on Hinglish. Freeze source/data/model hashes, prompts, budgets, splits,
  metrics and selection rules before evaluation; date changes in `PREREG.md`.
- Select on development data only; group related examples by source and track
  exposure. Existing Belebele is historically exposed. Bigger reruns are not
  fresh tests. Keep original, derived and synthetic data distinct.
- Confirmatory claims require suitable source-disjoint human-validated data,
  strong baselines, ablations and an independent answer-model family. Multiple
  Qwen sizes are one family. Check primary literature before novelty claims.
- Never give choices/gold to a question-only compressor. Unlabelled stress
  checks are not QA accuracy or proof of semantic preservation.
- Verify actual token caps; label reference-token/fixed-text transfer honestly.
  Report paired passage-clustered uncertainty, failures, token savings and
  compression plus inference cost. Explain multiple-comparison limitations.
  Do not cherry-pick budgets/models/subsets or retry until scores improve.
- Numbers must trace to saved `backend/data/bench/` artifacts from committed
  scripts. Preserve raw outputs and hashes. Check at least three real examples
  for suspicious gains or metric failures. Keep invalid answers in denominators
  under the frozen policy. Evidence precedes serving-default changes.

## Efficient execution

- Reuse verified artifacts, checkpoints and identical prompts with matching
  configs. Run targeted tests once; repeat only for relevant changes/failures.
  Documentation edits do not need the full suite.
- Background jobs need logs, atomic state and explicit compute/time caps. No
  duplicates or automatic repeated retries. Verify GPU use and completion.
- Share `research-gpu` through `/home/user/hinglish-research/gpu-campaign.lock`;
  coordinate existing users. CPU parallelism uses bounded `--shard i/n` shell
  processes (14 cores locally; ≥1.5 GB free RAM per LLMLingua-2 process).
- Prefer installed models/free GPUs. State material costs briefly; proceed with
  already authorized work. Ask only for new costs/scope/destructive effects.
- Provider batches only through `backend/scripts/bench/run_daily.py` and its
  budget: configured free-tier gpt-oss-20b/120b, low reasoning, capped outputs,
  no account rotation. Local Ollama is separate. Paid services require approval.
- Preserve unrelated edits. Commit completed work locally; push only if asked.
  Never rewrite published Git history.

## Preserve the separate router study

Keep scorer_train/pilot/cert = 30/10/60. Select with item-grouped scorer_train CV;
cert is touched once through `backend/scripts/bench/certify.py`. New scorers stay
opt-in (`ROUTER_SCORER=v2`); serving requires model-bound certification.

## Handoff

Append at most **6 short lines** to `docs/progress/AGENT_LOG.md`: date/commit,
verified result, running job/status/log, evidence path, next step. Clearly separate
planned/running/complete/failed. Store history there, not in this policy file.
