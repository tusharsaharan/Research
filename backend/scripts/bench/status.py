"""Progress counts for the benchmark (used by the weekly report)."""

from __future__ import annotations

import json
from collections import Counter

from common import ANSWERS, BENCH, GRADES, LEDGER, latest_variants, read_jsonl


def status() -> dict:
    items = read_jsonl(BENCH / "items.jsonl")
    variants = latest_variants()
    answers = read_jsonl(ANSWERS)
    hi = [v for v in variants if v["lang"] == "hinglish"]
    return {
        "items": len(items),
        "splits": dict(Counter(r["split"] for r in items)),
        "hinglish_variants": len(hi),
        "hinglish_auto_checks_passed": sum(all(v["checks"].values()) for v in hi),
        "answers_ok": dict(Counter(f"{a['tier']}/{a['lang']}" for a in answers if a.get("status") == "ok")),
        "answer_errors": sum(a.get("status") == "error" for a in answers),
        "graded_pairs": len(read_jsonl(GRADES)),
        "tokens_by_day": json.loads(LEDGER.read_text()) if LEDGER.exists() else {},
    }


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
