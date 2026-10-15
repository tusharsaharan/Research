"""Answer-level check of compression on gold-answer items (uses API quota).

For gold items whose ORIGINAL prompt already has a cheap-model answer, send the
COMPRESSED prompt to the same model with the same system prompt and compare
correctness pairwise (original vs compressed). Only prompts the compressor
actually changed are sent; unchanged prompts count as identical (documented
assumption). Real prompt-token savings come from provider usage, i.e. the
serving model's own tokenizer.

    python backend/scripts/bench/compress_answers.py --methods crf,crf+tokopt --daily-token-budget 160000
    python backend/scripts/bench/compress_answers.py --report
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict

from collect import SYSTEM
from common import ANSWERS, BENCH, BudgetExhausted, append_jsonl, chat, latest_variants, provider, read_jsonl, variant_ok
from compress_eval import BACKEND, HINGLISH_INSTRUCT, load_tokenizers
from grade import correct
from scipy.stats import binomtest
from tokopt import TokOptNormalizer

from gateway.modules.m2_compressor.compressor import Compressor
from gateway.tokenizer import TokenCounter

OUT = BENCH / "compress_answers.jsonl"
REPORT = BENCH / "compress_answers_report.json"


def build_methods() -> dict:
    comp = Compressor(counter=TokenCounter(), use_crf=True,
                      crf_model_path=BACKEND / "data" / "models" / "crf_compressor.pkl",
                      tfidf_path=BACKEND / "data" / "tfidf" / "hinglish_idf.json")
    with HINGLISH_INSTRUCT.open(encoding="utf-8-sig") as fh:
        corpus = [row["prompt"] for row in csv.DictReader(fh)]
    english = [r["question_en"] for r in read_jsonl(BENCH / "items.jsonl")]
    norm = TokOptNormalizer(load_tokenizers()["qwen2.5"], corpus, english)
    return {
        "heuristic": lambda t: comp.compress_heuristic(t).compressed,
        "crf": lambda t: comp.compress_crf(t).compressed,
        "crf+tokopt": lambda t: norm(comp.compress_crf(t).compressed),
    }


def report() -> None:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    base = {}
    for a in read_jsonl(ANSWERS):
        if a.get("status") == "ok" and a["tier"] == "cheap":
            base[(a["item_id"], a["lang"])] = a
    agg: dict = defaultdict(lambda: defaultdict(float))
    for r in read_jsonl(OUT):
        if r.get("status") != "ok":
            continue
        key = (r["item_id"], r["lang"])
        if key not in base:
            continue
        it = items[r["item_id"]]
        task, gold = it.get("task", "math"), it["gold"]
        o_ok = correct(task, base[key]["content"], gold)
        c_ok = correct(task, r["content"], gold) if r["changed"] else o_ok
        p_o = base[key]["usage"].get("prompt_tokens", 0)
        p_c = r["usage"].get("prompt_tokens", p_o) if r["changed"] else p_o
        for g in (f"{r['method']}|{r['lang']}", f"{r['method']}|{it['source'].split('/')[0]}|{r['lang']}"):
            a = agg[g]
            a["n"] += 1
            a["changed"] += r["changed"]
            a["orig_correct"] += o_ok
            a["comp_correct"] += c_ok
            a["broke"] += o_ok and not c_ok
            a["fixed"] += (not o_ok) and c_ok
            a["prompt_tok_orig"] += p_o
            a["prompt_tok_comp"] += p_c
    out = {}
    for g, a in sorted(agg.items()):
        n = a["n"]
        disc = int(a["broke"] + a["fixed"])
        p = binomtest(int(a["broke"]), disc, 0.5).pvalue if disc else 1.0  # exact McNemar
        out[g] = {"n": int(n), "changed_share": round(a["changed"] / n, 3),
                  "acc_original": round(a["orig_correct"] / n, 4), "acc_compressed": round(a["comp_correct"] / n, 4),
                  "broke": int(a["broke"]), "fixed": int(a["fixed"]), "mcnemar_p": round(p, 4),
                  "prompt_token_ratio_serving_model": round(a["prompt_tok_comp"] / max(a["prompt_tok_orig"], 1), 4)}
    REPORT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{'group':38} {'n':>5} {'chg':>5} {'accO':>6} {'accC':>6} {'broke':>5} {'fixed':>5} {'p':>6} {'tok':>6}")
    for g, r in out.items():
        print(f"{g:38} {r['n']:>5} {r['changed_share']:>5} {r['acc_original']:>6} {r['acc_compressed']:>6} "
              f"{r['broke']:>5} {r['fixed']:>5} {r['mcnemar_p']:>6} {r['prompt_token_ratio_serving_model']:>6}")
    print("report ->", REPORT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="crf,crf+tokopt")
    ap.add_argument("--daily-token-budget", type=int, default=160_000, help="cheap-model tokens/day total cap")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
        return

    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    texts = {(v["item_id"], v["lang"]): v["text"] for v in latest_variants() if variant_ok(v)}
    base = {(a["item_id"], a["lang"]) for a in read_jsonl(ANSWERS) if a.get("status") == "ok" and a["tier"] == "cheap"}
    done = {(r["item_id"], r["lang"], r["method"]) for r in read_jsonl(OUT) if r.get("status") == "ok"}
    methods = build_methods()
    p = provider("cheap")
    todo = [(k, m) for k in sorted(base) if k in texts or k[1] == "english"
            for m in args.methods.split(",") if (k[0], k[1], m) not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} (prompt, method) pairs to check")
    for n, ((item_id, lang), m) in enumerate(todo, 1):
        orig = texts.get((item_id, lang)) or items[item_id]["question_en"]
        comp = methods[m](orig)
        row = {"item_id": item_id, "lang": lang, "method": m, "model": p["model"], "compressed": comp,
               "changed": comp != orig}
        if not row["changed"]:
            append_jsonl(OUT, row | {"status": "ok", "content": "", "usage": {}})
            continue
        try:
            out = chat(p["model"], [{"role": "system", "content": SYSTEM[items[item_id].get("task", "math")]},
                                    {"role": "user", "content": comp}],
                       base_url=p["base_url"], api_key=p["api_key"], max_tokens=1024,
                       daily_token_budget=args.daily_token_budget)
        except BudgetExhausted as e:
            print("stopping:", e)
            break
        except RuntimeError as e:
            append_jsonl(OUT, row | {"status": "error", "error": str(e)[:300]})
            continue
        append_jsonl(OUT, row | {"status": "ok", **out})
        if n % 25 == 0:
            print(f"  {n}/{len(todo)}")
    report()


if __name__ == "__main__":
    main()
