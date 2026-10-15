"""Step 1: build source items with gold answers (English), split by item.

Source: GSM8K test set (Cobbe et al. 2021, MIT licence), downloaded from the
official repo. Gold = the number after '####'. Numeric exact match means the
routing loss needs no judge.

    python backend/scripts/bench/build_items.py            # all 1,319 items
    python backend/scripts/bench/build_items.py --limit 50 # smoke run
"""

from __future__ import annotations

import argparse
import json
import random

from common import ITEMS, SEED, split_for

GSM8K_TEST = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"


def gold_number(answer: str) -> str:
    return answer.split("####")[-1].strip().replace(",", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all items")
    args = ap.parse_args()

    import httpx

    rows = [json.loads(line) for line in httpx.get(GSM8K_TEST, timeout=60).text.splitlines() if line.strip()]
    order = list(range(len(rows)))
    random.Random(SEED).shuffle(order)
    if args.limit:
        order = order[: args.limit]

    existing = {json.loads(line)["item_id"] for line in ITEMS.read_text(encoding="utf-8").splitlines()} if ITEMS.exists() else set()
    added = 0
    with ITEMS.open("a", encoding="utf-8") as fh:
        for idx in order:
            item_id = f"gsm8k-test-{idx:04d}"
            if item_id in existing:
                continue
            r = rows[idx]
            fh.write(json.dumps({
                "item_id": item_id,
                "source": "gsm8k/test",
                "task": "math",
                "question_en": r["question"],
                "gold": gold_number(r["answer"]),
                "split": split_for(item_id),
            }, ensure_ascii=False) + "\n")
            added += 1
    print(f"items: +{added} (total {len(existing) + added}) -> {ITEMS}")


if __name__ == "__main__":
    main()
