"""Meaning-gated compression with a certified bound on the accuracy drop.

For every prompt the candidates are the original and each compressed version that was
answered (Kaggle, Qwen2.5-3B). A gate g with threshold lam picks the most compressed
candidate whose risk score s_g <= lam (the original always qualifies).
Loss of a prompt = orig_correct - chosen_correct in {-1, 0, 1} (accuracy drop; answer
churn that breaks and fixes in equal measure cancels out).

Certification (per language, Learn-then-Test, fixed sequence over lam from conservative
to aggressive): reject H0: E[loss] > alpha when U_break - L_fix <= alpha, with
Clopper-Pearson bounds at delta/2 each (union bound -> level delta per test).
The risk model was fit on scorer_train items (meaning_signals.py); only cert items are
used here, re-split 500x into calibration / test halves.

Gates: rate-only (1 - token ratio), similarity (1 - multilingual MiniLM cosine; our earlier
adaptive method), learned risk (logistic model, meaning_signals.py), and a "fixed method"
baseline (one method for all prompts, methods ordered by token ratio).

    python gated_compress.py --splits 500
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

import numpy as np
from common import BENCH, read_jsonl
from scipy.stats import beta

LANGS = ("english", "hinglish")


def cp_upper(k, n, d):
    return 1.0 if k >= n else float(beta.ppf(1 - d, k + 1, n - k))


def cp_lower(k, n, d):
    return 0.0 if k <= 0 else float(beta.ppf(d, k, n - k + 1))


def load():
    by = defaultdict(list)
    for r in read_jsonl(BENCH / "meaning_pairs.jsonl"):
        if r["split"] == "cert":
            by[(r["item_id"], r["lang"])].append(r)
    items = []
    for (iid, lang), rs in by.items():
        o = int(rs[0]["orig_correct"])
        cands = [{"method": "original", "tok": 1.0, "correct": o, "s": {"rate": 0.0, "sim": 0.0, "learned": 0.0}}]
        for r in rs:
            cands.append({"method": r["method"], "tok": min(1.0, r["tok_ratio"]), "correct": int(r["comp_correct"]),
                          "s": {"rate": 1 - min(1.0, r["tok_ratio"]), "sim": 1 - r["cosine"], "learned": r["risk_broke"]}})
        items.append({"id": iid, "lang": lang, "orig": o, "cands": cands})
    return items


def choose(it, gate, lam):
    if lam == -np.inf:
        return it["cands"][0]
    ok = [c for c in it["cands"] if c["s"][gate] <= lam]
    return min(ok, key=lambda c: (c["tok"], c["s"][gate]))


def stats(items, pick):
    b = f = 0
    tok = 0.0
    for it in items:
        c = pick(it)
        b += it["orig"] and not c["correct"]
        f += (not it["orig"]) and c["correct"]
        tok += c["tok"]
    n = len(items)
    return b, f, n, 1 - tok / n


def certify(cal, picks, alpha, delta):
    """picks: list of pick-functions ordered conservative -> aggressive. Returns last certified index or -1."""
    best = -1
    for i, p in enumerate(picks):
        b, f, n, _ = stats(cal, p)
        if cp_upper(b, n, delta / 2) - cp_lower(f, n, delta / 2) <= alpha:
            best = i
        else:
            break
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=500)
    ap.add_argument("--alphas", default="0.01,0.02,0.05")
    ap.add_argument("--delta", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=20261019)
    a = ap.parse_args()
    alphas = [float(x) for x in a.alphas.split(",")]
    items = load()
    methods = sorted({c["method"] for it in items for c in it["cands"]} - {"original"})
    mean_tok = {m: np.mean([c["tok"] for it in items for c in it["cands"] if c["method"] == m]) for m in methods}
    fixed_order = ["original"] + sorted(methods, key=lambda m: -mean_tok[m])  # mildest first

    def fixed_pick(m):
        return lambda it: next((c for c in it["cands"] if c["method"] == m), it["cands"][0])

    gates = {}
    for g in ("rate", "sim", "learned"):
        vals = np.unique(np.quantile([c["s"][g] for it in items for c in it["cands"][1:]], np.linspace(0, 1, 81)))
        gates[g] = [-np.inf] + [v for v in vals if v > 0]  # -inf = original only
    rng = random.Random(a.seed)
    res = defaultdict(lambda: defaultdict(list))
    for _ in range(a.splits):
        for lang in LANGS:
            sub = [it for it in items if it["lang"] == lang]
            rng.shuffle(sub)
            cal, test = sub[: len(sub) // 2], sub[len(sub) // 2:]
            for alpha in alphas:
                d = a.delta / len(alphas)
                policies = {"fixed method": [fixed_pick(m) for m in fixed_order]}
                for g, grid in gates.items():
                    policies[f"gate:{g}"] = [(lambda it, g=g, lam=lam: choose(it, g, lam)) for lam in grid]
                for name, picks in policies.items():
                    i = certify(cal, picks, alpha, d)
                    pick = picks[i] if i >= 0 else (lambda it: it["cands"][0])
                    b, f, n, saved = stats(test, pick)
                    k = (lang, alpha, name)
                    res[k]["drop"].append((b - f) / n)
                    res[k]["violate"].append((b - f) / n > alpha)
                    res[k]["saved"].append(saved if i >= 0 else 0.0)
                    if name == "fixed method":
                        res[k]["chosen"].append(fixed_order[max(i, 0)])
    out = {}
    for k, v in sorted(res.items()):
        o = {"mean_drop_pts": round(100 * float(np.mean(v["drop"])), 2),
             "violation_rate": round(float(np.mean(v["violate"])), 4),
             "mean_tokens_saved": round(float(np.mean(v["saved"])), 4)}
        if v.get("chosen"):
            from collections import Counter
            o["chosen"] = dict(Counter(v["chosen"]).most_common(3))
        out[" | ".join(map(str, k))] = o
        print(f"{k[0]:8} a={k[1]:.2f} {k[2]:14} drop={o['mean_drop_pts']:+5.2f}pts viol={o['violation_rate']:.3f} "
              f"saved={o['mean_tokens_saved']:.3f} {o.get('chosen', '')}")
    # headroom: per prompt, the most compressed candidate that does not break the answer (oracle, not deployable)
    for lang in LANGS:
        sub = [it for it in items if it["lang"] == lang]
        sv = np.mean([1 - min((c for c in it["cands"] if c["correct"] >= it["orig"]), key=lambda c: c["tok"])["tok"] for it in sub])
        out[f"{lang} | oracle headroom"] = {"tokens_saved_no_accuracy_loss": round(float(sv), 4)}
        print(f"{lang:8} oracle (no loss) tokens saved = {sv:.3f}")
    (BENCH / "gated_compress_report.json").write_text(json.dumps({"delta": a.delta, "splits": a.splits, "results": out}, indent=2),
                                                      encoding="utf-8")


if __name__ == "__main__":
    main()
