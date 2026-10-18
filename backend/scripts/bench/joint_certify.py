"""Joint certified compress-or-route (Learn-then-Test over method x threshold).

Configuration c = (m, lam): a query with router score s(x) <= lam goes to the cheap
model with its prompt compressed by method m; everything else goes to premium with
the original prompt. Loss of a cheap-routed query: u_m(x) = 1[cheap_m wrong and
premium right]. For each method, thresholds are tested in fixed sequence with
Clopper-Pearson p-values; methods are Bonferroni-corrected (delta / (|M| * |alphas|)),
so every certified configuration is simultaneously valid w.p. >= 1 - delta and the
cheapest one on calibration can be selected without breaking the guarantee
(Angelopoulos et al. 2021, LTT). Run per language (Mondrian) and pooled (marginal).

Cost model: cheap calls priced at the cheap API tier (gpt-oss-20b list rates,
pricing.py) for the tokens actually used (compressed input + observed output);
premium at gpt-oss-120b rates on its observed tokens. Only ratios are reported.

    python joint_certify.py --splits 1000
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict

import numpy as np
from certify import LANGS, train_scorer
from common import BENCH, latest_variants, read_jsonl
from grade import correct
from scipy.stats import binom

from gateway.pricing import tier_cost_usd

METHODS = ["original", "heuristic", "crf+tokopt[o200k]",
           *[f"guarded2@{r}" for r in ("0.8", "0.7", "0.6", "0.5")],
           *[f"llmlingua2+spans@{r}" for r in ("0.8", "0.7", "0.6", "0.5")]]


def load():
    grades = {(r["item_id"], r["lang"]): r for r in read_jsonl(BENCH / "grades_pair2.jsonl") if r["lang"] in LANGS}
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    prem = {}  # premium observed tokens from the Groq answers
    for a in read_jsonl(BENCH / "answers.jsonl"):
        if a.get("tier") == "premium" and a.get("status") == "ok":
            u = a.get("usage") or {}
            prem[(a["item_id"], a["lang"])] = (u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
    cheap = {}
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        key = (a["item_id"], a["lang"])
        if key not in grades:
            continue
        it = items[a["item_id"]]
        ok = correct(it.get("task", "math"), a["content"], it["gold"])
        for m in a["methods"]:
            if m in METHODS:
                cheap[key + (m,)] = (ok, tier_cost_usd("cheap", a["prompt_tokens"], a["completion_tokens"]))
    rows = []
    for key, g in grades.items():
        if not all(key + (m,) in cheap for m in METHODS):
            continue
        pt, ct = prem.get(key, (g.get("prompt_tokens", 0), 0))
        rows.append({**g, "premium_cost": tier_cost_usd("premium", pt, ct),
                     "u_m": {m: int((not cheap[key + (m,)][0]) and g["premium_correct"]) for m in METHODS},
                     "cost_m": {m: cheap[key + (m,)][1] for m in METHODS}})
    return rows


def certify_method(s, u, grid, alpha, delta):
    """Fixed-sequence CP test along the grid; returns the largest certified threshold (or -inf)."""
    order = np.argsort(s)
    s_sorted, cu = s[order], np.concatenate([[0], np.cumsum(u[order])])
    n, lam = len(u), -math.inf
    for g in grid:
        k = int(cu[np.searchsorted(s_sorted, g, side="right")])
        if binom.cdf(k, n, alpha) <= delta:
            lam = g
        else:
            break
    return lam


def policy_cost(rows, s, m, lam):
    cheap = s <= lam
    c = sum(r["cost_m"][m] if ch else r["premium_cost"] for r, ch in zip(rows, cheap))
    return c, cheap


def choose(rows, s, grid, alpha, delta, methods):
    """Cheapest certified (method, lam) on these calibration rows."""
    best = (None, -math.inf, sum(r["premium_cost"] for r in rows))
    for m in methods:
        u = np.array([r["u_m"][m] for r in rows])
        lam = certify_method(s, u, grid, alpha, delta / len(methods))
        if lam == -math.inf:
            continue
        c, _ = policy_cost(rows, s, m, lam)
        if c < best[2]:
            best = (m, lam, c)
    return best[0], best[1]


def preselect(rows, s, alpha, methods):
    """Method choice on the scorer_train split (disjoint from cert), so certifying the single
    chosen method on calibration needs no multiplicity correction: for each method take the
    largest threshold with empirical risk <= alpha and keep the cheapest."""
    best, best_c = "original", math.inf
    for m in methods:
        u = np.array([r["u_m"][m] for r in rows])
        ok = [g for g in np.unique(s) if (u * (s <= g)).mean() <= alpha]
        if not ok:
            continue
        c, _ = policy_cost(rows, s, m, max(ok))
        if c < best_c:
            best, best_c = m, c
    return best


def evaluate(rows, s, m, lam):
    base = sum(r["premium_cost"] for r in rows)
    if m is None:
        return 0.0, 0.0, 0.0
    c, cheap = policy_cost(rows, s, m, lam)
    u = np.array([r["u_m"][m] for r in rows])
    return float((cheap * u).mean()), float(cheap.mean()), float(1 - c / base)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=1000)
    ap.add_argument("--alphas", default="0.05,0.10,0.20")
    ap.add_argument("--delta", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=20261019)
    a = ap.parse_args()
    alphas = [float(x) for x in a.alphas.split(",")]
    rows = load()
    texts = {(r["item_id"], "english"): r["question_en"] for r in read_jsonl(BENCH / "items.jsonl")}
    texts |= {(v["item_id"], v["lang"]): v["text"] for v in latest_variants()}
    for r in rows:
        r["u"] = r["u_m"]["original"]  # scorer target: does the cheap model need help on this query?
    scores, desc, _ = train_scorer(rows, texts)
    tr = np.array([scores[(r["item_id"], r["lang"])] for r in rows if r["split"] == "scorer_train"])
    grid = np.unique(np.quantile(tr, np.linspace(0, 1, 101)))
    cert = [r for r in rows if r["split"] == "cert"]
    print(f"{len(rows)} rows with all methods; cert {Counter(r['lang'] for r in cert)}; scorer: {desc}")
    items = sorted({r["item_id"] for r in cert})
    rng = random.Random(a.seed)
    res = defaultdict(lambda: defaultdict(list))
    picks = defaultdict(Counter)
    policies = {"routing only (no compression)": ["original"], "joint compress-or-route": METHODS}
    train = [r for r in rows if r["split"] == "scorer_train"]
    pre = {(lg, al): preselect([r for r in train if r["lang"] == lg],
                               np.array([scores[(r["item_id"], lg)] for r in train if r["lang"] == lg]), al, METHODS)
           for lg in LANGS for al in alphas}
    pre_marg = {al: preselect(train, np.array([scores[(r["item_id"], r["lang"])] for r in train]), al, METHODS)
                for al in alphas}
    print("pre-selected on scorer_train:", pre, pre_marg)
    policies["joint, method pre-selected on train split"] = None
    for _ in range(a.splits):
        rng.shuffle(items)
        cal_ids = set(items[: len(items) // 2])
        for alpha in alphas:
            d = a.delta / len(alphas)
            for pname, ms0 in policies.items():
                for mode in ("per-language", "marginal"):
                    ms = ms0 if ms0 is not None else [pre_marg[alpha]]
                    if mode == "marginal":
                        cal = [r for r in cert if r["item_id"] in cal_ids]
                        sc = np.array([scores[(r["item_id"], r["lang"])] for r in cal])
                        m, lam = choose(cal, sc, grid, alpha, d, ms)
                    for lg in LANGS:
                        cal = [r for r in cert if r["item_id"] in cal_ids and r["lang"] == lg]
                        test = [r for r in cert if r["item_id"] not in cal_ids and r["lang"] == lg]
                        if mode == "per-language":
                            if ms0 is None:
                                ms = [pre[(lg, alpha)]]
                            sc = np.array([scores[(r["item_id"], lg)] for r in cal])
                            m, lam = choose(cal, sc, grid, alpha, d, ms)
                        st = np.array([scores[(r["item_id"], lg)] for r in test])
                        risk, share, saving = evaluate(test, st, m, lam)
                        k = (pname, mode, lg, alpha)
                        res[k]["violate"].append(risk > alpha)
                        res[k]["saving"].append(saving)
                        res[k]["share"].append(share)
                        if pname.startswith("joint"):
                            picks[k][m or "all-premium"] += 1
    out = {}
    for k, v in sorted(res.items()):
        o = {"violation_rate": round(float(np.mean(v["violate"])), 4), "mean_saving": round(float(np.mean(v["saving"])), 4),
             "cheap_share": round(float(np.mean(v["share"])), 4)}
        if k in picks:
            o["chosen_method"] = dict(picks[k].most_common(4))
        out[" | ".join(map(str, k))] = o
        print(f"{k[0]:31} {k[1]:12} {k[2]:8} a={k[3]:.2f} viol={o['violation_rate']:.3f} save={o['mean_saving']:+.3f} "
              f"cheap={o['cheap_share']:.2f} {o.get('chosen_method', '')}")
    (BENCH / "joint_certify_report.json").write_text(json.dumps({"scorer": desc, "delta": a.delta, "splits": a.splits,
                                                                  "results": out}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
