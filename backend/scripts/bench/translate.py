"""Step 2: make the romanized-Hinglish variant of every item.

English variant = the original question. Hinglish variant = model translation
"as typed on WhatsApp", then automatic checks (all numbers kept, Roman script,
actually code-mixed). Every Hinglish item still needs one human check: this
script writes verify_sheet.csv for the annotators.

    python backend/scripts/bench/translate.py --limit 50
    python backend/scripts/bench/translate.py --export-sheet
"""

from __future__ import annotations

import argparse
import csv
import json
import re

from common import (
    BENCH,
    VARIANTS,
    BudgetExhausted,
    append_jsonl,
    chat,
    in_shard,
    latest_variants,
    provider,
    read_jsonl,
    variant_ok,
)

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio, language_group

_STYLE = (
    "in natural romanized Hinglish (Hindi-English mix, Latin script only, the way Indian "
    "students type on WhatsApp). Keep every number as digits, every name, unit and currency "
    "symbol exactly as given (do not convert $ to ₹)."
)
PROMPTS = {
    "math": "Rewrite this math word problem " + _STYLE
            + " Do not solve it. Output only the rewritten problem.\n\n{q}",
    "mcq": "Rewrite this multiple-choice question and its options " + _STYLE
           + " Keep the option labels A), B), C), D) exactly, one option per line, in the same order."
           " Do not answer it. Output only the rewritten question and options.\n\n{q}",
}
_OPT = re.compile(r"^\s*([A-H])\)", re.MULTILINE)
_NUM = re.compile(r"\d+(?:\.\d+)?")
_CURRENCY = re.compile(r"[$₹€£]|\bRs\.?|\bINR\b|\bUSD\b")


def checks(en: str, hi: str) -> dict:
    opts = {"options_kept": _OPT.findall(en) == _OPT.findall(hi)} if _OPT.search(en) else {}
    nums_en = sorted(_NUM.findall(en.replace(",", "")))
    nums_hi = sorted(_NUM.findall(hi.replace(",", "")))
    return {
        "numbers_kept": nums_en == nums_hi,
        "currency_kept": sorted(_CURRENCY.findall(en)) == sorted(_CURRENCY.findall(hi)),
        "roman_only": not re.search(r"[ऀ-ॿ]", hi),
        "is_hinglish": language_group(hi) == "hinglish" and hi.strip() != en.strip(),
        "nonempty": bool(hi.strip()),
    } | opts


def export_sheet() -> None:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    out = BENCH / "verify_sheet.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "english", "hinglish", "auto_ok", "meaning_same(1/0)", "natural(1-3)", "annotator", "notes"])
        for v in latest_variants():
            if v["lang"] != "hinglish":
                continue
            w.writerow([v["item_id"], items[v["item_id"]]["question_en"], v["text"], int(all(v["checks"].values())), "", "", "", ""])
    print("sheet ->", out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tier", default="cheap", help="which configured model translates")
    ap.add_argument("--daily-token-budget", type=int, default=400_000)
    ap.add_argument("--export-sheet", action="store_true")
    ap.add_argument("--recheck", action="store_true", help="re-run automatic checks on existing variants")
    ap.add_argument("--retry-failed", action="store_true", help="re-translate items whose checks failed")
    ap.add_argument("--shard", default=None, help="i/n, e.g. 1/3")
    ap.add_argument("--source", default=None, help="only items whose id starts with this, e.g. arc")
    args = ap.parse_args()
    if args.export_sheet:
        export_sheet()
        return
    if args.recheck:
        items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
        rows = read_jsonl(VARIANTS)
        for v in rows:
            if v["lang"] == "hinglish":
                v["checks"] = checks(items[v["item_id"]]["question_en"], v["text"])
        VARIANTS.write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in rows), encoding="utf-8")
        print("rechecked", sum(v["lang"] == "hinglish" for v in rows), "variants")
        return

    p = provider(args.tier)
    latest = {(v["item_id"], v["lang"]): v for v in latest_variants()}
    done = {k for k, v in latest.items() if variant_ok(v) or not args.retry_failed}
    todo = [r for r in read_jsonl(BENCH / "items.jsonl")
            if (r["item_id"], "hinglish") not in done and in_shard(r["item_id"], args.shard)
            and (not args.source or r["item_id"].startswith(args.source))]
    if args.limit:
        todo = todo[: args.limit]
    for n, r in enumerate(todo, 1):
        if (r["item_id"], "english") not in done:
            append_jsonl(VARIANTS, {"item_id": r["item_id"], "lang": "english", "text": r["question_en"],
                                    "cmi": code_mix_ratio(r["question_en"]), "checks": {}, "by": "source"})
        try:
            out = chat(p["model"], [{"role": "user", "content": PROMPTS[r.get("task", "math")].format(q=r["question_en"])}],
                       base_url=p["base_url"], api_key=p["api_key"], max_tokens=900,
                       daily_token_budget=args.daily_token_budget)
        except BudgetExhausted as e:
            print("stopping:", e)
            break
        hi = out["content"].strip()
        append_jsonl(VARIANTS, {"item_id": r["item_id"], "lang": "hinglish", "text": hi,
                                "cmi": code_mix_ratio(hi), "checks": checks(r["question_en"], hi),
                                "by": p["model"], "usage": out["usage"]})
        if n % 25 == 0:
            print(f"{n}/{len(todo)} translated")
    print("variants ->", VARIANTS)


if __name__ == "__main__":
    main()
