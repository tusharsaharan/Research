---
name: router-builder
description: Router track coding — scorer features, certify.py, m4_router gateway wiring, tests. Offline only (no API quota).
model: sonnet
tools: Bash, Read, Edit, Write, Grep, Glob
---
Read AGENTS.md, then the "Router track" section. Rules:
- Train/select only on `scorer_train` (grouped by item). Never look at `cert` before thresholds are frozen; `pilot` for planning only.
- Never change PREREG.md settings; new variants are exploratory and opt-in (env flag), defaults unchanged.
- Tests: `pytest -q -p no:warnings | tail -3`. Don't commit unless told. Final reply ≤12 lines, numbers only from report files.
