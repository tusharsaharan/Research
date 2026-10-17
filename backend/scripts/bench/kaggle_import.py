"""Grade local-model answers from the Kaggle notebook and analyse them.

Input:  backend/data/bench/kaggle/answers.jsonl (from kaggle/local_answers_t4.ipynb)
Output: kaggle/answer_report.json — per (method, language): accuracy, paired
        change vs the original prompt (broke / fixed, exact McNemar p), and real
        prompt-token ratio under the answering model's tokenizer;
        grades_pair2.jsonl — routing labels for model pair 2
        (cheap = local model on the original prompt, premium = gpt-oss-120b answers
        already in answers.jsonl), same schema as grades.jsonl.

    python backend/scripts/bench/kaggle_import.py
"""

from __future__ import annotations

import json
from collections import defaultdict

from common import ANSWERS, BENCH, read_jsonl
from grade import correct
from scipy.stats import binomtest

from gateway.pricing import tier_cost_usd

K = BENCH / "kaggle"


def main() -> None:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    rows = read_jsonl(K / "answers.jsonl")
    if not rows:
        raise SystemExit(f"no answers in {K / 'answers.jsonl'}")
    model = rows[0]["model"]
    res: dict = {}  # (item, lang, method) -> (correct, prompt_tokens)
    for r in rows:
        it = items[r["item_id"]]
        ok = correct(it.get("task", "math"), r["content"], it["gold"])
        for m in r["methods"]:
            res[(r["item_id"], r["lang"], m)] = (ok, r["prompt_tokens"])

    agg: dict = defaultdict(lambda: defaultdict(float))
    for (item_id, lang, m), (ok, ptok) in res.items():
        base = res.get((item_id, lang, "original"))
        if base is None:
            continue
        src = items[item_id]["source"].split("/")[0]
        for g in (f"{m}|{lang}", f"{m}|{src}|{lang}"):
            a = agg[g]
            a["n"] += 1
            a["correct"] += ok
            a["orig_correct"] += base[0]
            a["broke"] += base[0] and not ok
            a["fixed"] += ok and not base[0]
            a["tok"] += ptok
            a["tok_orig"] += base[1]
    report = {"model": model}
    for g, a in sorted(agg.items()):
        disc = int(a["broke"] + a["fixed"])
        report[g] = {"n": int(a["n"]), "acc": round(a["correct"] / a["n"], 4),
                     "acc_original": round(a["orig_correct"] / a["n"], 4),
                     "delta_pts": round(100 * (a["correct"] - a["orig_correct"]) / a["n"], 2),
                     "broke": int(a["broke"]), "fixed": int(a["fixed"]),
                     "mcnemar_p": round(binomtest(int(a["broke"]), disc, 0.5).pvalue, 4) if disc else 1.0,
                     "prompt_token_ratio": round(a["tok"] / max(a["tok_orig"], 1), 4)}
    (K / "answer_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"model: {model}\n{'method|lang':32} {'n':>5} {'acc':>6} {'orig':>6} {'Δpts':>6} {'broke':>5} {'fixed':>5} {'p':>7} {'tok':>6}")
    for g, r in report.items():
        if g == "model" or g.count("|") != 1:
            continue
        print(f"{g:32} {r['n']:>5} {r['acc']:>6} {r['acc_original']:>6} {r['delta_pts']:>6} {r['broke']:>5} "
              f"{r['fixed']:>5} {r['mcnemar_p']:>7} {r['prompt_token_ratio']:>6}")

    # Routing labels, pair 2: cheap = local model (original prompt), premium = gpt-oss-120b.
    prem = {(a["item_id"], a["lang"]): a for a in read_jsonl(ANSWERS)
            if a.get("status") == "ok" and a["tier"] == "premium"}
    out = []
    for (item_id, lang, m), (ok, ptok) in res.items():
        if m != "original" or (item_id, lang) not in prem:
            continue
        it, p = items[item_id], prem[(item_id, lang)]
        p_ok = correct(it.get("task", "math"), p["content"], it["gold"])
        pu = p["usage"]
        out.append({"item_id": item_id, "lang": lang, "split": it["split"], "source": it["source"].split("/")[0],
                    "task": it.get("task", "math"), "cheap_correct": ok, "premium_correct": p_ok,
                    "u": int((not ok) and p_ok), "prompt_tokens": pu.get("prompt_tokens", 0),
                    "cost_cheap_usd": 0.0,  # self-hosted: no API cost
                    "cost_premium_usd": tier_cost_usd("premium", pu.get("prompt_tokens", 0), pu.get("completion_tokens", 0)),
                    "cheap_model": model})
    (BENCH / "grades_pair2.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out), encoding="utf-8")
    by = defaultdict(lambda: [0, 0, 0])
    for r in out:
        by[r["lang"]][0] += 1
        by[r["lang"]][1] += r["cheap_correct"]
        by[r["lang"]][2] += r["u"]
    print("pair 2 routing labels:", {k: {"n": v[0], "cheap_acc": round(v[1] / v[0], 3), "u_rate": round(v[2] / v[0], 3)}
                                     for k, v in by.items()})


if __name__ == "__main__":
    main()
