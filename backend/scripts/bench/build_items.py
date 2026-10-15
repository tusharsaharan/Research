"""Step 1: build source items with gold answers (English), split by item.

Sources (all gold-answer, so the routing loss needs no judge):
  gsm8k  GSM8K test, 1,319 math word problems, numeric gold (MIT licence)
  arc    ARC-Challenge test, 1,172 science multiple-choice questions (CC BY-SA 4.0)
  mmlu   MMLU test, 57 subjects, multiple-choice; sampled (MIT licence)

    python backend/scripts/bench/build_items.py --source gsm8k
    python backend/scripts/bench/build_items.py --source arc
    python backend/scripts/bench/build_items.py --source mmlu --limit 1000
"""

from __future__ import annotations

import argparse
import json
import random

from common import ITEMS, SEED, split_for

GSM8K_TEST = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
HF_ROWS = "https://datasets-server.huggingface.co/rows"
LETTERS = "ABCDEFGH"


def gold_number(answer: str) -> str:
    return answer.split("####")[-1].strip().replace(",", "")


def hf_rows(dataset: str, config: str, split: str) -> list[dict]:
    import httpx

    import time

    out, offset = [], 0
    while True:
        for attempt in range(8):  # the public rows API rate-limits bursts and drops connections
            try:
                r = httpx.get(HF_ROWS, params={"dataset": dataset, "config": config, "split": split,
                                               "offset": offset, "length": 100}, timeout=120)
            except httpx.TransportError:
                time.sleep(5 * 2**attempt)
                continue
            if r.status_code != 429:
                break
            time.sleep(float(r.headers.get("retry-after", 5 * 2**attempt)))
        r.raise_for_status()
        time.sleep(0.5)
        j = r.json()
        out += [x["row"] for x in j["rows"]]
        offset += 100
        if offset >= j["num_rows_total"]:
            return out


def mcq_text(question: str, choices: list[str]) -> str:
    return question.strip() + "\n\n" + "\n".join(f"{LETTERS[i]}) {c}" for i, c in enumerate(choices))


def load(source: str) -> list[dict]:
    if source == "gsm8k":
        import httpx

        rows = [json.loads(x) for x in httpx.get(GSM8K_TEST, timeout=60).text.splitlines() if x.strip()]
        return [{"item_id": f"gsm8k-test-{i:04d}", "source": "gsm8k/test", "task": "math",
                 "question_en": r["question"], "gold": gold_number(r["answer"])} for i, r in enumerate(rows)]
    if source == "arc":
        rows = hf_rows("allenai/ai2_arc", "ARC-Challenge", "test")
        items = []
        for r in rows:
            labels = r["choices"]["label"]
            if r["answerKey"] not in labels:
                continue
            items.append({"item_id": f"arc-{r['id']}", "source": "ai2_arc/ARC-Challenge/test", "task": "mcq",
                          "question_en": mcq_text(r["question"], r["choices"]["text"]),
                          "gold": LETTERS[labels.index(r["answerKey"])]})
        return items
    if source == "mmlu":
        rows = hf_rows("cais/mmlu", "all", "test")
        return [{"item_id": f"mmlu-{i:05d}", "source": f"mmlu/test/{r['subject']}", "task": "mcq",
                 "question_en": mcq_text(r["question"], r["choices"]), "gold": LETTERS[int(r["answer"])]}
                for i, r in enumerate(rows)]
    raise SystemExit(f"unknown source {source}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="gsm8k", choices=["gsm8k", "arc", "mmlu"])
    ap.add_argument("--limit", type=int, default=0, help="0 = all items (random sample otherwise)")
    args = ap.parse_args()

    rows = load(args.source)
    random.Random(SEED).shuffle(rows)
    if args.limit:
        rows = rows[: args.limit]
    existing = {json.loads(x)["item_id"] for x in ITEMS.read_text(encoding="utf-8").splitlines()} if ITEMS.exists() else set()
    added = 0
    with ITEMS.open("a", encoding="utf-8") as fh:
        for r in rows:
            if r["item_id"] in existing:
                continue
            fh.write(json.dumps(r | {"split": split_for(r["item_id"])}, ensure_ascii=False) + "\n")
            added += 1
    print(f"{args.source}: +{added} items (file total {len(existing) + added}) -> {ITEMS}")


if __name__ == "__main__":
    main()
