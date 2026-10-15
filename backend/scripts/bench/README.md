# Benchmark pipeline (paired English / Hinglish, gold answers)

Produces the real data the prototype and the paper need: for each GSM8K test
item, an English and a romanized-Hinglish version, the cheap and premium
models' answers, and an exact-match grade. Everything is append-only JSONL in
`backend/data/bench/` (git-ignored; share files through Drive).

## Daily runbook

From the repo root:

```bash
python backend/scripts/bench/build_items.py                 # once: 1,319 items + splits
python backend/scripts/bench/translate.py --shard 1/3       # each teammate takes 1/3, 2/3, 3/3
python backend/scripts/bench/translate.py --export-sheet    # verify_sheet.csv for human checks
python backend/scripts/bench/collect.py --shard 1/3         # run daily; stops at the token budget
python backend/scripts/bench/grade.py                       # summary.json per language
python backend/scripts/bench/status.py                      # counts for the weekly report
```

- Each teammate runs their shard with **their own** API key in `backend/.env`.
  Don't rotate several accounts per person to dodge rate limits.
- `--daily-token-budget` should sit just under your provider's tokens-per-day
  limit (Groq free tier for gpt-oss-120b is about 200k/day; check your console).
- Merge shards by concatenating `answers.jsonl` / `variants.jsonl`; `grade.py`
  de-duplicates by (item, language, tier).
- Failed automatic checks (numbers changed, currency changed, still English)
  are excluded from answering; fix them in `verify_sheet.csv` or re-run
  `translate.py --retry-failed`.

## Files

| File | Row = |
|---|---|
| `items.jsonl` | source item: English question, gold answer, split (`scorer_train` 30% / `pilot` 10% / `cert` 60%, by item) |
| `variants.jsonl` | (item, language) text + automatic checks; last row wins |
| `answers.jsonl` | one model call, with raw content, reasoning, usage; errors are rows too |
| `grades.jsonl` | (item, language): cheap correct, premium correct, `u` = cheap wrong and premium right, real cost |
| `summary.json` | per-language accuracy, `u` rate, tokens, cost ratio, tokenizer tax |
| `ledger.json` | tokens spent per model per UTC day |
