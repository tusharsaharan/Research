"""Step 4: grade answers against gold and summarise per language group.

Routing loss per (item, language): u = 1 if the cheap answer is wrong and the
premium answer is right (the quality lost by routing cheap instead of premium).
Also reports the tokenizer tax (provider prompt tokens, Hinglish / English, same
items) and real cost from provider usage at the dated prices in gateway.pricing.

    python backend/scripts/bench/grade.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

from common import ANSWERS, BENCH, GRADES, latest_variants, read_jsonl, variant_ok

from gateway.pricing import tier_cost_usd

_FINAL = re.compile(r"####\s*\$?\s*(-?[\d,]*\.?\d+)")
_ANYNUM = re.compile(r"-?\d[\d,]*\.?\d*")


def extract(text: str) -> str | None:
    m = _FINAL.findall(text or "")
    if not m:
        nums = _ANYNUM.findall(text or "")
        if not nums:
            return None
        m = nums
    return m[-1].replace(",", "").rstrip(".")


def same(a: str | None, gold: str) -> bool:
    if a is None:
        return False
    try:
        return abs(float(a) - float(gold)) < 1e-6
    except ValueError:
        return False


def main() -> None:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    # Only grade variants whose latest version passed checks (stale answers to
    # superseded or failed translations are ignored).
    ok_variants = {(v["item_id"], v["lang"]) for v in latest_variants() if variant_ok(v)}
    by_key: dict[tuple, dict] = {}
    for a in read_jsonl(ANSWERS):
        if a.get("status") == "ok" and (a["item_id"], a["lang"]) in ok_variants:
            by_key[(a["item_id"], a["lang"], a["tier"])] = a  # last ok row wins

    rows = []
    for (item_id, lang, tier), a in by_key.items():
        if tier != "cheap" or (item_id, lang, "premium") not in by_key:
            continue
        p = by_key[(item_id, lang, "premium")]
        gold = items[item_id]["gold"]
        c_ok = same(extract(a["content"]), gold)
        p_ok = same(extract(p["content"]), gold)
        cu, pu = a["usage"], p["usage"]
        rows.append({
            "item_id": item_id, "lang": lang, "split": items[item_id]["split"],
            "cheap_correct": c_ok, "premium_correct": p_ok, "u": int((not c_ok) and p_ok),
            "prompt_tokens": pu.get("prompt_tokens", 0),
            "cost_cheap_usd": tier_cost_usd("cheap", cu.get("prompt_tokens", 0), cu.get("completion_tokens", 0)),
            "cost_premium_usd": tier_cost_usd("premium", pu.get("prompt_tokens", 0), pu.get("completion_tokens", 0)),
        })
    GRADES.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    agg: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        g = agg[r["lang"]]
        g["n"] += 1
        g["cheap_acc"] += r["cheap_correct"]
        g["premium_acc"] += r["premium_correct"]
        g["u_rate"] += r["u"]
        g["prompt_tokens"] += r["prompt_tokens"]
        g["cost_cheap"] += r["cost_cheap_usd"]
        g["cost_premium"] += r["cost_premium_usd"]
    summary = {}
    for lang, g in agg.items():
        n = g["n"]
        summary[lang] = {
            "n": int(n),
            "cheap_accuracy": round(g["cheap_acc"] / n, 4),
            "premium_accuracy": round(g["premium_acc"] / n, 4),
            "u_rate_cheap_wrong_premium_right": round(g["u_rate"] / n, 4),
            "mean_prompt_tokens": round(g["prompt_tokens"] / n, 1),
            "cost_ratio_cheap_over_premium": round(g["cost_cheap"] / max(g["cost_premium"], 1e-12), 4),
        }
    # Tokenizer tax on items answered in both languages.
    paired = defaultdict(dict)
    for r in rows:
        paired[r["item_id"]][r["lang"]] = r["prompt_tokens"]
    both = [v for v in paired.values() if "english" in v and "hinglish" in v and v["english"]]
    if both:
        summary["tokenizer_tax_hinglish_over_english"] = round(sum(v["hinglish"] / v["english"] for v in both) / len(both), 4)
    (BENCH / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
