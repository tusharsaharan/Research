"""Step 3: get cheap and premium answers for every language variant.

Resumable: rows already in answers.jsonl are skipped, so run it every day until
done. Stops cleanly when a model's daily token budget is used up (set it just
under your provider's tokens-per-day limit; check the console).

Only variants that passed the automatic checks are answered; failed ones go
back to translation (translate.py --retry-failed) or human repair.

Teammates can split the work with --shard 1/3, 2/3, 3/3 (each on their own
machine and key) and then concatenate their answers.jsonl files; grade.py
de-duplicates by (item, language, tier).

    python backend/scripts/bench/collect.py --limit 20
    python backend/scripts/bench/collect.py --tiers premium --daily-token-budget 190000 --shard 2/3
"""

from __future__ import annotations

import argparse

from common import ANSWERS, BENCH, BudgetExhausted, append_jsonl, chat, in_shard, latest_variants, provider, read_jsonl, variant_ok

SYSTEM = {
    "math": "Solve the problem. You may think briefly. End your reply with a final line of the "
            "form '#### <number>' containing only the final numeric answer.",
    "mcq": "Answer the multiple-choice question. You may think briefly. End your reply with a final "
           "line of the form '#### <letter>' containing only the letter of the correct option.",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="cheap,premium")
    ap.add_argument("--limit", type=int, default=0, help="max new calls per tier this run")
    ap.add_argument("--daily-token-budget", type=int, default=190_000)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--shard", default=None, help="i/n, e.g. 1/3")
    ap.add_argument("--source", default=None, help="only items whose id starts with this, e.g. arc")
    args = ap.parse_args()

    task = {r["item_id"]: r.get("task", "math") for r in read_jsonl(BENCH / "items.jsonl")}
    variants = [v for v in latest_variants() if variant_ok(v) and in_shard(v["item_id"], args.shard)
                and (not args.source or v["item_id"].startswith(args.source))]
    done = {(a["item_id"], a["lang"], a["tier"]) for a in read_jsonl(ANSWERS) if a.get("status") == "ok"}
    for tier in args.tiers.split(","):
        p = provider(tier)
        todo = [v for v in variants if (v["item_id"], v["lang"], tier) not in done]
        if args.limit:
            todo = todo[: args.limit]
        print(f"{tier} ({p['model']}): {len(todo)} calls to make")
        for n, v in enumerate(todo, 1):
            try:
                out = chat(p["model"], [{"role": "system", "content": SYSTEM[task[v["item_id"]]]}, {"role": "user", "content": v["text"]}],
                           base_url=p["base_url"], api_key=p["api_key"], max_tokens=args.max_tokens,
                           daily_token_budget=args.daily_token_budget)
            except BudgetExhausted as e:
                print("stopping tier:", e)
                break
            except RuntimeError as e:  # a failed call is a row, never a silent gap
                append_jsonl(ANSWERS, {"item_id": v["item_id"], "lang": v["lang"], "tier": tier,
                                       "model": p["model"], "status": "error", "error": str(e)[:300]})
                continue
            append_jsonl(ANSWERS, {"item_id": v["item_id"], "lang": v["lang"], "tier": tier, "model": p["model"],
                                   "status": "ok", **out})
            if n % 25 == 0:
                print(f"  {n}/{len(todo)}")


if __name__ == "__main__":
    main()
