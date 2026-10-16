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

# Working rules for AI agents (read first)

The owner is on a limited plan. **Spend tokens like they are money.**

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
