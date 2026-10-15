"""Main experiment: marginal vs per-language certified routing on real data.

1. Scorer: predicts u (cheap wrong AND premium right) from the query alone,
   trained only on the `scorer_train` split.
2. Threshold grid: quantiles of scorer_train scores (fixed before calibration).
3. On the `cert` split, B random calibration/test re-splits (by item, so both
   language versions of an item fall on the same side). In each:
   - marginal: one threshold, fixed-sequence test with Clopper-Pearson
     p-values at delta/|A| (valid for post-hoc choice of alpha in A);
   - per-language: one threshold per language at delta/(K*|A|).
   Route cheap iff score <= threshold.
4. Report, per method and language: violation rate P(test risk > alpha)
   (should be <= delta for a valid guarantee), mean risk, cheap share and real
   cost saving vs all-premium. Plus a language-mix-shift stress test.

    python backend/scripts/bench/certify.py --splits 1000
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict

import numpy as np
from common import BENCH, GRADES, latest_variants, read_jsonl
from scipy.stats import binom

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio

LANGS = ("english", "hinglish")


# ----------------------------------------------------------------- scorer

def featurize(texts: list[str], langs: list[str]) -> tuple[np.ndarray, str]:
    base = np.array([[float(lg == "hinglish"), code_mix_ratio(t), math.log1p(len(t.split()))] for t, lg in zip(texts, langs)])
    try:
        from sentence_transformers import SentenceTransformer

        enc = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        emb = enc.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        return np.hstack([base, emb]), "multilingual-MiniLM + lang/CMI/length"
    except Exception as e:  # encoder unavailable -> say so in the report
        return base, f"lang/CMI/length only ({type(e).__name__})"


def train_scorer(rows: list[dict], texts: dict) -> tuple[dict, str]:
    from sklearn.linear_model import LogisticRegression

    keys = [(r["item_id"], r["lang"]) for r in rows]
    X, feat_desc = featurize([texts[k] for k in keys], [k[1] for k in keys])
    y = np.array([r["u"] for r in rows])
    tr = np.array([r["split"] == "scorer_train" for r in rows])
    if y[tr].sum() < 5 or (1 - y[tr]).sum() < 5:
        # Too few positives to learn from: fall back to input length (documented in report).
        s = X[:, 2] / max(X[:, 2].max(), 1e-9)
        return dict(zip(keys, s)), feat_desc + " | FALLBACK: length score (too few u=1 in scorer_train)"
    clf = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
    return dict(zip(keys, clf.predict_proba(X)[:, 1])), feat_desc + " | logistic regression"


# ------------------------------------------------------- certification

def fixed_sequence(scores: np.ndarray, u: np.ndarray, grid: np.ndarray, alpha: float, delta: float) -> float:
    """Largest grid threshold certified by fixed-sequence CP testing; -inf = all premium."""
    n = len(u)
    lam = -math.inf
    if n == 0:
        return lam
    for g in grid:
        k = int(u[scores <= g].sum())
        # p-value for H0: risk >= alpha  is  P[Bin(n, alpha) <= k]
        if binom.cdf(k, n, alpha) <= delta:
            lam = g
        else:
            break
    return lam


def evaluate(rows: list[dict], scores: dict, lam_of) -> dict:
    out = {}
    for lg in LANGS:
        sub = [r for r in rows if r["lang"] == lg]
        if not sub:
            continue
        lam = lam_of(lg)
        cheap = np.array([scores[(r["item_id"], lg)] <= lam for r in sub])
        u = np.array([r["u"] for r in sub])
        cost = sum(r["cost_cheap_usd"] if c else r["cost_premium_usd"] for r, c in zip(sub, cheap))
        base = sum(r["cost_premium_usd"] for r in sub)
        out[lg] = {"risk": float((cheap * u).mean()), "cheap_share": float(cheap.mean()),
                   "saving": float(1 - cost / base) if base else 0.0}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=1000)
    ap.add_argument("--alphas", default="0.05,0.10,0.20")
    ap.add_argument("--delta", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=20261015)
    args = ap.parse_args()
    alphas = [float(a) for a in args.alphas.split(",")]

    grades = [r for r in read_jsonl(GRADES) if r["lang"] in LANGS]
    texts = {(v["item_id"], v["lang"]): v["text"] for v in latest_variants()}
    if not grades:
        raise SystemExit("no graded rows yet: run collect.py and grade.py first")
    scores, scorer_desc = train_scorer(grades, texts)

    train_scores = np.array([scores[(r["item_id"], r["lang"])] for r in grades if r["split"] == "scorer_train"])
    grid = np.unique(np.quantile(train_scores, np.linspace(0, 1, 101))) if len(train_scores) else np.linspace(0, 1, 101)

    cert = [r for r in grades if r["split"] == "cert"]
    items = sorted({r["item_id"] for r in cert})
    rng = random.Random(args.seed)
    K, A = len(LANGS), len(alphas)
    acc: dict = defaultdict(lambda: defaultdict(list))
    shares = np.linspace(0.1, 0.9, 9)

    for _ in range(args.splits):
        rng.shuffle(items)
        cal_items = set(items[: len(items) // 2])
        cal = [r for r in cert if r["item_id"] in cal_items]
        test = [r for r in cert if r["item_id"] not in cal_items]

        def arrays(rs):
            return (np.array([scores[(r["item_id"], r["lang"])] for r in rs]), np.array([r["u"] for r in rs]))

        for alpha in alphas:
            s_all, u_all = arrays(cal)
            lam_m = fixed_sequence(s_all, u_all, grid, alpha, args.delta / A)
            lam_g = {lg: fixed_sequence(*arrays([r for r in cal if r["lang"] == lg]), grid, alpha, args.delta / (K * A))
                     for lg in LANGS}
            for method, lam_of in (("marginal", lambda lg: lam_m), ("per_language", lambda lg: lam_g[lg])):
                ev = evaluate(test, scores, lam_of)
                for lg, m in ev.items():
                    for key, val in m.items():
                        acc[(method, alpha, lg)][key].append(val)
                    acc[(method, alpha, lg)]["violated"].append(float(m["risk"] > alpha))
                if set(ev) == set(LANGS):
                    for p in shares:  # test-time language mix: share p of Hinglish
                        mixed = (1 - p) * ev["english"]["risk"] + p * ev["hinglish"]["risk"]
                        acc[(method, alpha, "mix")][f"{p:.1f}"].append(float(mixed > alpha))

    report = {"scorer": scorer_desc, "n_cert_items": len(items), "n_cert_rows": len(cert),
              "n_scorer_train_rows": int(len(train_scores)), "delta": args.delta, "splits": args.splits,
              "u_rate_by_lang": {lg: float(np.mean([r["u"] for r in grades if r["lang"] == lg] or [0])) for lg in LANGS},
              "results": []}
    for (method, alpha, lg), m in sorted(acc.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        if lg == "mix":
            report["results"].append({"method": method, "alpha": alpha, "lang": "mix-shift",
                                      "violation_rate_by_hinglish_share": {k: round(float(np.mean(v)), 3) for k, v in m.items()}})
            continue
        report["results"].append({"method": method, "alpha": alpha, "lang": lg,
                                  "violation_rate": round(float(np.mean(m["violated"])), 3),
                                  "mean_risk": round(float(np.mean(m["risk"])), 4),
                                  "cheap_share": round(float(np.mean(m["cheap_share"])), 3),
                                  "cost_saving": round(float(np.mean(m["saving"])), 3)})
    (BENCH / "certify_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"scorer: {scorer_desc}\ncert items: {len(items)}  rows: {len(cert)}  delta={args.delta}  splits={args.splits}")
    print("u rate (cheap wrong & premium right):", {k: round(v, 3) for k, v in report["u_rate_by_lang"].items()})
    print(f"{'alpha':>5} {'method':>12} {'lang':>9} {'viol':>6} {'risk':>7} {'cheap':>6} {'save':>6}")
    for r in report["results"]:
        if r["lang"] == "mix-shift":
            continue
        print(f"{r['alpha']:>5} {r['method']:>12} {r['lang']:>9} {r['violation_rate']:>6} {r['mean_risk']:>7} "
              f"{r['cheap_share']:>6} {r['cost_saving']:>6}")
    print("report ->", BENCH / "certify_report.json")


if __name__ == "__main__":
    main()
