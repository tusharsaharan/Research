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

from gateway.modules.m4_router.certified import ENCODER, artifacts_dir, featurize

LANGS = ("english", "hinglish")


# ----------------------------------------------------------------- scorer

def train_scorer(rows: list[dict], texts: dict) -> tuple[dict, str, dict | None]:
    """Fit on scorer_train only; returns (scores for all rows, description, servable bundle)."""
    from sklearn.linear_model import LogisticRegression

    keys = [(r["item_id"], r["lang"]) for r in rows]
    flags = [k[1] == "hinglish" for k in keys]
    try:
        X = featurize([texts[k] for k in keys], flags, use_embeddings=True)
        use_emb, desc = True, f"{ENCODER} + lang/CMI/length"
    except RuntimeError as e:  # encoder unavailable -> say so in the report
        X = featurize([texts[k] for k in keys], flags, use_embeddings=False)
        use_emb, desc = False, f"lang/CMI/length only ({e})"
    y = np.array([r["u"] for r in rows])
    tr = np.array([r["split"] == "scorer_train" for r in rows])
    if y[tr].sum() < 5 or (1 - y[tr]).sum() < 5:
        # Too few positives to learn from: fall back to input length (documented in report).
        s = X[:, 2] / max(X[:, 2].max(), 1e-9)
        return dict(zip(keys, s)), desc + " | FALLBACK: length score (too few u=1 in scorer_train)", None
    clf = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X[tr], y[tr])
    desc += " | logistic regression (balanced)"
    return dict(zip(keys, clf.predict_proba(X)[:, 1])), desc, {"clf": clf, "use_embeddings": use_emb, "description": desc}


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
    ap.add_argument("--serve-alpha", type=float, default=0.10, help="alpha the gateway serves (must be in --alphas)")
    args = ap.parse_args()
    alphas = [float(a) for a in args.alphas.split(",")]

    grades = [r for r in read_jsonl(GRADES) if r["lang"] in LANGS]
    texts = {(v["item_id"], v["lang"]): v["text"] for v in latest_variants()}
    if not grades:
        raise SystemExit("no graded rows yet: run collect.py and grade.py first")
    scores, scorer_desc, bundle = train_scorer(grades, texts)

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
              "by_source": by_source(grades),
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
    export_router(bundle, cert, scores, grid, args)


def by_source(grades: list[dict]) -> dict:
    """Accuracy and u-rate per dataset and language (all splits)."""
    out: dict = {}
    for r in grades:
        key = f"{r.get('source', '?')}/{r['lang']}"
        o = out.setdefault(key, {"n": 0, "cheap_acc": 0.0, "premium_acc": 0.0, "u_rate": 0.0})
        o["n"] += 1
        o["cheap_acc"] += r["cheap_correct"]
        o["premium_acc"] += r["premium_correct"]
        o["u_rate"] += r["u"]
    for o in out.values():
        for k in ("cheap_acc", "premium_acc", "u_rate"):
            o[k] = round(o[k] / o["n"], 4)
    return dict(sorted(out.items()))


def export_router(bundle: dict | None, cert: list[dict], scores: dict, grid: np.ndarray, args) -> None:
    """Certify serving thresholds on the whole cert split and save them for the gateway."""
    import pickle
    from datetime import datetime, timezone

    if bundle is None:
        print("router not exported: scorer fell back (too few u=1 in scorer_train)")
        return
    alphas = [float(a) for a in args.alphas.split(",")]
    K, A = len(LANGS), len(alphas)

    def arrays(rs):
        return (np.array([scores[(r["item_id"], r["lang"])] for r in rs]), np.array([r["u"] for r in rs]))

    def lam_or_none(x: float) -> float | None:
        return None if x == -math.inf else float(x)

    per_alpha = {}
    for alpha in alphas:
        per_lang = {}
        for lg in LANGS:
            rows = [r for r in cert if r["lang"] == lg]
            s, u = arrays(rows)
            lam = fixed_sequence(s, u, grid, alpha, args.delta / (K * A))
            per_lang[lg] = {"cheap_if_score_at_most": lam_or_none(lam), "n": len(rows),
                            "cheap_share_on_cert": round(float((s <= lam).mean()), 4) if len(rows) else 0.0}
        s, u = arrays(cert)
        per_alpha[f"{alpha:.2f}"] = {"per_language": per_lang,
                                     "marginal": {"cheap_if_score_at_most": lam_or_none(
                                         fixed_sequence(s, u, grid, alpha, args.delta / A))}}
    d = artifacts_dir(BENCH.parent)
    d.mkdir(parents=True, exist_ok=True)
    (d / "certified_router.pkl").write_bytes(pickle.dumps(bundle))
    (d / "certified_thresholds.json").write_text(json.dumps({
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "delta": args.delta, "alphas": alphas, "serve_alpha": f"{args.serve_alpha:.2f}",
        "guarantee": "per language: P(quality lost vs always-premium > alpha) <= delta, "
                     "fixed-sequence Clopper-Pearson at delta/(K*|A|) on the cert split",
        "n_cert_rows": len(cert), "preliminary": len(cert) < 600,
        "scorer": bundle["description"], "thresholds": per_alpha}, indent=2), encoding="utf-8")
    print("router artifacts ->", d)


if __name__ == "__main__":
    main()
