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

# Working rules for AI agents (read first — these are strict)

The owner is on a limited plan. **Spend tokens like they are money.**

## Start and end of every session (no lost context)

1. Read, in this order and nothing else first: this file, the last 30 lines of
   `docs/progress/AGENT_LOG.md`, then the current week in `docs/progress/ROADMAP.md`.
2. Research context lives in `docs/research/`: `PREREG.md` (hypotheses, frozen
   settings), `COMPRESSION_STUDY.md`, `ROUTER_COMPRESSOR_REPORT.md`, `DECISIONS.md`.
   Never change pre-registered settings without adding a dated change-log line.
3. Before ending (or when context runs long), append to `AGENT_LOG.md`:
   date · what was done (commits) · what is running (job, log file) · next step.
   Max 6 lines. This file is the handoff; keep it accurate.
4. Commit finished work locally with a clear message; never push unless asked.

## Doing the work well

- Results must be traceable: every number in a doc comes from a file in
  `backend/data/bench/` produced by a committed script. Say "pending" otherwise.
- Check suspicious metrics on 2–3 real examples before reporting them (several
  "failures" so far were metric bugs).
- CPU jobs: use all cores via `--shard i/n` processes (14 cores here; keep
  ≥ 1.5 GB free RAM per LLMLingua-2 process). Start them in the background,
  write output to a log file, and do not poll.
- API jobs only through `run_daily.py` (scheduled 06:00).

## Which agent for which job

| Job | Agent / model |
|---|---|
| Find files or symbols across the repo | built-in Grep/Glob; `Explore` agent (Haiku) only if many places |
| Mechanical edits, running scripts, reading logs | main session on Haiku or Sonnet, low effort |
| New scripts, bug fixes, gateway wiring, tests | Sonnet |
| Statistical guarantees, proofs, experiment design, paper text | Opus |
| Parallel CPU work | shell processes (`--shard`), never sub-agents |

Sub-agents and side sessions only when the user asks for them by name.

## Router track (cheap vs premium, certified per language)

- Code: scorer + certification `backend/scripts/bench/certify.py`; offline v2 scorer
  `backend/scripts/bench/router_v2.py`; serving `backend/src/gateway/modules/m4_router/certified.py`;
  artifacts `backend/data/router_artifacts/`. Labels: `backend/data/bench/grades*.jsonl`.
- Splits are frozen (`scorer_train` 30 / `pilot` 10 / `cert` 60). Select models on
  `scorer_train` (item-grouped CV) only; `cert` is touched once, by `certify.py`.
- Defaults stay pre-registered; any new scorer is opt-in via `ROUTER_SCORER=v2`.
- More labels = the real lever, and they cost API quota: only via `run_daily.py`.
- Project subagents (`.claude/agents/`): `log-reader` (Haiku, status checks),
  `router-builder` (Sonnet, router code), `stats-reviewer` (Opus, validity review).
  Use them only when the user asks for sub-agents; pick the cheapest that fits.

## Token discipline

- Do exactly what was asked. No unrequested refactors, reports, docs or "while I'm here" fixes; propose them in one line instead.
- Read narrowly: use `grep`/`sed -n` line ranges, not whole files. Never re-read a file you just edited.
- Never print big data. `backend/data/bench/*.jsonl` and logs can be MBs: use `head`, `tail -5`, counts, or a 5-line Python summary.
- Keep tool output short: pipe test runs to `| tail -3`; quiet flags (`-q`, `-p no:warnings`).
- Don't poll or wait in loops. Long jobs: start once in the background and stop; check later only if asked.
- No parallel sub-agents or side sessions unless the user explicitly asks — each one re-reads the repo from scratch.
- Don't web-search for things already in `docs/research/` (plan, PREREG, COMPRESSION_STUDY, ROUTER_COMPRESSOR_REPORT).
- Answers: short. Lead with the result, then at most a few bullets. No restating the plan, no long tables unless asked.
- Before an expensive step (full 8,000-prompt rerun ~40 min CPU, any API batch, model downloads), say the cost in one line and ask.

## Which assistant model to use

| Task | Use |
|---|---|
| Research design, proofs, reviewing a statistical guarantee, paper writing | Opus (largest) — only for these |
| Normal coding: new scripts, bug fixes, tests, wiring the gateway | Sonnet (default) |
| Mechanical work: renames, formatting, running commands, reading logs, small edits | Haiku (cheapest) |

Default to Sonnet; switch up only when the task needs deep reasoning, down when it's mechanical. Use low reasoning effort for routine edits.

## Which project LLM (API quota, Groq free tier)

| Purpose | Model | Why |
|---|---|---|
| Hinglish translation, cheap-tier answers, compression answer check | `openai/gpt-oss-20b` | half the price; quota shared by all three uses |
| Premium-tier answers (reference) | `openai/gpt-oss-120b` | ~200k tokens/day, ~550 calls; the bottleneck |
| Never for bulk jobs | any paid model | free tier only |

- Always `reasoning_effort="low"` and capped `max_tokens` (see `scripts/bench/common.py`).
- Bulk API work goes through `scripts/bench/run_daily.py` (scheduled 06:00 daily; it stops at the daily budget). Don't start extra API runs by hand.
- One API key per person; never rotate accounts to dodge limits.
- Offline work (compression benchmark, tokenizers, CRF, LLMLingua-2) costs no API quota — prefer it.
