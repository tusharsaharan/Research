"""Conformal Cascade baseline (arXiv 2607.25018, Algorithm 1) on the pair-2 cert split.

Tier 1 = Qwen2.5-3B, N=16 samples at T=0.7 (data/bench/kaggle-cc/answers.jsonl, one row per
item|lang with a list "samples"). Nonconformity of an answer a = 1 - freq(a) among the N samples.
K=2 tiers (cheap, premium), kappa=1: threshold qhat = the ceil((n+1)(1-alpha))/n empirical quantile of
the nonconformity of the GOLD answer on the calibration half. Prediction set = {a: 1-freq(a) <= qhat}
(sampled answers only); accept the cheap tier iff the set is a singleton, otherwise escalate to premium.
Loss = accepted, the accepted (modal) answer is wrong, and premium is right (same "quality lost vs
premium" as the router). Cheap tier cost = 0 (local), saving = 1 - cost/premium-cost as in router_baselines.
Splits: identical to router_baselines.run (cert items shuffled in place by random.Random(seed), first half
= calibration, 1,000 re-splits, same alpha grid); marginal = one qhat pooled, per-language = one per language.

    python backend/scripts/bench/conformal_cascade.py   # -> data/bench/conformal_cascade_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict

import numpy as np

from common import BENCH, read_jsonl
from grade import extract, extract_letter, same

LANGS = ["english", "hinglish"]


def answer_of(task: str, text: str) -> str:
    a = extract_letter(text) if task == "mcq" else extract(text)
    return "__none__" if a is None else a


def norm(task: str, a: str) -> str:
    if task == "mcq" or a == "__none__":
        return a
    try:
        return repr(round(float(a), 6))
    except ValueError:
        return a


def build_rows(grades: list[dict], answers: dict, items: dict) -> list[dict]:
    """Per cert row: freq dict over answers, gold (normalised), modal answer."""
    out = []
    for g in grades:
        if g["split"] != "cert" or g["lang"] not in LANGS:
            continue
        a = answers.get(f'{g["item_id"]}|{g["lang"]}')
        if a is None:
            continue
        task = g["task"]
        cnt = Counter(norm(task, answer_of(task, s)) for s in a["samples"])
        n = sum(cnt.values())
        freq = {k: v / n for k, v in cnt.items()}
        gold = norm(task, items[g["item_id"]]["gold"])
        mode = max(sorted(freq), key=lambda k: freq[k])
        out.append({"item_id": g["item_id"], "lang": g["lang"], "freq": freq, "gold": gold, "mode": mode,
                    "pc": float(g["premium_correct"]), "pu": g["cost_premium_usd"], "cu": g["cost_cheap_usd"]})
    return out


def qhat(rows: list[dict], alpha: float) -> float:
    s = np.sort([1.0 - r["freq"].get(r["gold"], 0.0) for r in rows])
    n = len(s)
    k = math.ceil((n + 1) * (1 - alpha))
    return math.inf if n == 0 or k > n else float(s[k - 1])


def accept(r: dict, q: float) -> bool:
    return sum(1.0 - f <= q + 1e-12 for f in r["freq"].values()) == 1


def metrics(rows: list[dict], q: float) -> dict:
    acc = np.array([accept(r, q) for r in rows])
    ok = np.array([r["mode"] == r["gold"] for r in rows])
    pc = np.array([r["pc"] for r in rows])
    loss = acc & ~ok & (pc > 0)
    pu = np.array([r["pu"] for r in rows])
    cu = np.array([r["cu"] for r in rows])
    base = pu.sum()
    cost = np.where(acc, cu, pu).sum()
    return {"risk": float(loss.mean()), "cheap_share": float(acc.mean()),
            "saving": float(1 - cost / base) if base else 0.0}


def run(rows: list[dict], splits: int, alphas: list[float], seed: int) -> dict:
    items = sorted({r["item_id"] for r in rows})
    ids = np.array([r["item_id"] for r in rows])
    lang = np.array([r["lang"] for r in rows])
    rng = random.Random(seed)
    acc = defaultdict(lambda: defaultdict(list))
    for _ in range(splits):
        rng.shuffle(items)
        cal_set = set(items[: len(items) // 2])
        in_cal = np.array([i in cal_set for i in ids])
        for alpha in alphas:
            qm = qhat([r for r, c in zip(rows, in_cal) if c], alpha)
            for lg in LANGS:
                cal_lg = [r for r, c, l in zip(rows, in_cal, lang) if c and l == lg]
                test = [r for r, c, l in zip(rows, in_cal, lang) if not c and l == lg]
                if not test:
                    continue
                for name, q in (("cc_marginal", qm), ("cc_perlang", qhat(cal_lg, alpha))):
                    m = metrics(test, q)
                    for k, v in m.items():
                        acc[(name, alpha, lg)][k].append(v)
                    acc[(name, alpha, lg)]["violated"].append(float(m["risk"] > alpha))
    res = []
    for (method, alpha, lg), m in sorted(acc.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        res.append({"method": method, "alpha": alpha, "lang": lg,
                    "violation_rate": round(float(np.mean(m["violated"])), 3),
                    "mean_risk": round(float(np.mean(m["risk"])), 4),
                    "cheap_share": round(float(np.mean(m["cheap_share"])), 3),
                    "cost_saving": round(float(np.mean(m["saving"])), 3)})
    return {"n_rows": len(rows), "n_items": len(items), "splits": splits, "seed": seed, "results": res}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=1000)
    ap.add_argument("--alphas", default="0.05,0.10,0.20")
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--answers", default=str(BENCH / "kaggle-cc" / "answers.jsonl"))
    a = ap.parse_args()
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    answers = {r["key"]: r for r in read_jsonl(a.answers)}
    rows = build_rows(read_jsonl(BENCH / "grades_pair2.jsonl"), answers, items)
    rep = run(rows, a.splits, [float(x) for x in a.alphas.split(",")], a.seed)
    rep["note"] = "Conformal Cascade K=2, kappa=1, N=16, T=0.7; gold-coverage calibration; cheap tier cost 0 (local)"
    (BENCH / "conformal_cascade_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("done", rep["n_rows"], "rows")


if __name__ == "__main__":
    main()
