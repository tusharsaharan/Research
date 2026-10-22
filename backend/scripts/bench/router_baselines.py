"""Router baselines for the paper: certified per-language LTT vs literature baselines.

Offline. Reuses certify.py (scorer, fixed-sequence CP-LTT) and cached MiniLM embeddings.
Same item-grouped 50/50 cert re-splits (seed 20261015) as certify.py.
  python scripts/bench/router_baselines.py [--splits 1000]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

import certify as C
from common import BENCH, latest_variants, read_jsonl
from gateway.modules.m4_router.certified import ENCODER, featurize as _featurize

LANGS = C.LANGS
METHODS = ["always_premium", "always_cheap", "random_matched", "emp_marginal", "emp_perlang",
           "crc_marginal", "crc_perlang", "ltt_marginal", "ltt_perlang", "ltt_marginal_worstgroup",
           "knn_ltt_perlang"]


# --------------------------------------------------------- threshold rules
def _risk_curve(scores, u, grid):
    n = len(u)
    if n == 0:
        return np.zeros(len(grid)), 0
    return ((scores[:, None] <= grid[None, :]) * u[:, None]).sum(0) / n, n


def thr_empirical(scores, u, grid, alpha):
    """Largest grid lambda with empirical risk <= alpha (no finite-sample correction)."""
    R, n = _risk_curve(scores, u, grid)
    ok = np.where(R <= alpha)[0]
    return grid[ok.max()] if n and len(ok) else -np.inf


def thr_crc(scores, u, grid, alpha):
    """Conformal risk control (Angelopoulos et al. 2024): (n R + 1)/(n+1) <= alpha."""
    R, n = _risk_curve(scores, u, grid)
    ok = np.where((n * R + 1) / (n + 1) <= alpha)[0]
    return grid[ok.max()] if n and len(ok) else -np.inf


# --------------------------------------------------------------- scorers
def _embedder(texts):
    cache = {}
    for f in ("adaptive_emb_cache.npz", "router_v2_emb_cache.npz"):
        if (BENCH / f).exists():
            z = np.load(BENCH / f, allow_pickle=True)
            cache.update(zip(map(str, z["keys"]), z["vecs"]))
    miss = sorted({t for t in texts if t not in cache})
    if miss:
        from sentence_transformers import SentenceTransformer
        v = SentenceTransformer(ENCODER).encode(miss, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        cache.update(zip(miss, v))
    return np.array([cache[t] for t in texts]), len(miss)


def cached_featurize(texts, flags, use_embeddings=True):
    """Identical to gateway featurize(), but embeddings come from the local caches."""
    base = _featurize(texts, flags, use_embeddings=False)
    if not use_embeddings:
        return base
    emb, _ = _embedder(texts)
    return np.hstack([base, emb])


def knn_scores(rows, texts, k=20):
    """RouteLLM SW-ranking style: similarity-weighted mean of u over k nearest scorer_train items."""
    keys = [(r["item_id"], r["lang"]) for r in rows]
    E, _ = _embedder([texts[kk] for kk in keys])
    y = np.array([r["u"] for r in rows], float)
    tr = np.array([r["split"] == "scorer_train" for r in rows])
    tr_idx = np.where(tr)[0]
    S = E @ E[tr].T
    ytr = y[tr]
    out = np.zeros(len(rows))
    for i in range(len(rows)):
        s = S[i].copy()
        if tr[i]:  # leave self out for train rows
            s[np.where(tr_idx == i)[0]] = -np.inf
        idx = np.argsort(-s)[:k]
        w = np.clip(s[idx], 1e-6, None)
        out[i] = float((w * ytr[idx]).sum() / w.sum())
    return dict(zip(keys, out))


# ------------------------------------------------------------- evaluation
def metrics(sub, cheap_mask):
    u, cc, pc, cc_usd, pc_usd = sub["u"], sub["cc"], sub["pc"], sub["cu"], sub["pu"]
    risk = float((cheap_mask * u).mean())
    base = pc_usd.sum()
    cost = np.where(cheap_mask, cc_usd, pc_usd).sum()
    acc = float(np.where(cheap_mask, cc, pc).mean())
    a_c, a_p = float(cc.mean()), float(pc.mean())
    apgr = (acc - a_c) / (a_p - a_c) if a_p - a_c > 1e-9 else np.nan
    return {"risk": risk, "cheap_share": float(cheap_mask.mean()),
            "saving": float(1 - cost / base) if base else 0.0, "apgr": apgr}


def random_metrics(sub, p):
    """Expected metrics of routing each query cheap w.p. p (analytic)."""
    u, cc, pc, cc_usd, pc_usd = sub["u"], sub["cc"], sub["pc"], sub["cu"], sub["pu"]
    base = pc_usd.sum()
    acc = p * cc.mean() + (1 - p) * pc.mean()
    a_c, a_p = float(cc.mean()), float(pc.mean())
    return {"risk": float(p * u.mean()), "cheap_share": float(p),
            "saving": float(1 - (p * cc_usd.sum() + (1 - p) * base) / base) if base else 0.0,
            "apgr": float((acc - a_c) / (a_p - a_c)) if a_p - a_c > 1e-9 else np.nan}


def run(grades_name, splits, alphas, delta, seed, paired_gsm8k=False):
    grades = [r for r in read_jsonl(BENCH / grades_name) if r["lang"] in LANGS]
    if paired_gsm8k:  # same GSM8K items in both languages: removes the task/language confound
        grades = [r for r in grades if r["source"] == "gsm8k"]
        langs_of = {}
        for r in grades:
            langs_of.setdefault(r["item_id"], set()).add(r["lang"])
        grades = [r for r in grades if langs_of[r["item_id"]] >= set(LANGS)]
    texts = {(r["item_id"], "english"): r["question_en"] for r in read_jsonl(BENCH / "items.jsonl")}
    texts |= {(v["item_id"], v["lang"]): v["text"] for v in latest_variants()}
    C.featurize = cached_featurize  # same features, cached embeddings
    lr, desc, _ = C.train_scorer(grades, texts)
    knn = knn_scores(grades, texts)
    grids = {}
    for name, sc in (("lr", lr), ("knn", knn)):
        tr = np.array([sc[(r["item_id"], r["lang"])] for r in grades if r["split"] == "scorer_train"])
        grids[name] = np.unique(np.quantile(tr, np.linspace(0, 1, 101)))
    cert = [r for r in grades if r["split"] == "cert"]
    items = sorted({r["item_id"] for r in cert})
    from sklearn.metrics import roc_auc_score
    auroc = {}
    for lg in LANGS:
        rs = [r for r in cert if r["lang"] == lg]
        y = [r["u"] for r in rs]
        auroc[lg] = {n: (float(roc_auc_score(y, [sc[(r["item_id"], lg)] for r in rs])) if 0 < sum(y) < len(y) else None)
                     for n, sc in (("lr", lr), ("knn", knn))} | {"n": len(rs), "n_u1": int(sum(y))}

    def arr(rs, sc):
        return {"s": np.array([sc[(r["item_id"], r["lang"])] for r in rs]),
                "u": np.array([r["u"] for r in rs], float), "lang": np.array([r["lang"] for r in rs]),
                "cc": np.array([r["cheap_correct"] for r in rs], float), "pc": np.array([r["premium_correct"] for r in rs], float),
                "cu": np.array([r["cost_cheap_usd"] for r in rs]), "pu": np.array([r["cost_premium_usd"] for r in rs])}

    def sel(d, m):
        return {k: v[m] for k, v in d.items()}

    ids_cert = np.array([r["item_id"] for r in cert])
    D = {n: arr(cert, sc) for n, sc in (("lr", lr), ("knn", knn))}
    rng = random.Random(seed)
    K, A = len(LANGS), len(alphas)
    acc = defaultdict(lambda: defaultdict(list))
    mix = defaultdict(list)
    for _ in range(splits):
        rng.shuffle(items)
        cal_set = set(items[: len(items) // 2])
        in_cal = np.array([i in cal_set for i in ids_cert])
        for alpha in alphas:
            lam = {}
            for scorer in ("lr", "knn"):
                d = D[scorer]
                cal, grid = sel(d, in_cal), grids[scorer]
                pooled = {"emp": thr_empirical(cal["s"], cal["u"], grid, alpha),
                          "crc": thr_crc(cal["s"], cal["u"], grid, alpha),
                          "ltt": C.fixed_sequence(cal["s"], cal["u"], grid, alpha, delta / A)}
                per = {n: {} for n in ("emp", "crc", "ltt")}
                for lg in LANGS:
                    g = sel(cal, cal["lang"] == lg)
                    per["emp"][lg] = thr_empirical(g["s"], g["u"], grid, alpha)
                    per["crc"][lg] = thr_crc(g["s"], g["u"], grid, alpha)
                    per["ltt"][lg] = C.fixed_sequence(g["s"], g["u"], grid, alpha, delta / (K * A))
                if scorer == "lr":
                    lam["emp_marginal"] = {lg: pooled["emp"] for lg in LANGS}
                    lam["emp_perlang"] = per["emp"]
                    lam["crc_marginal"] = {lg: pooled["crc"] for lg in LANGS}
                    lam["crc_perlang"] = per["crc"]
                    lam["ltt_marginal"] = {lg: pooled["ltt"] for lg in LANGS}
                    lam["ltt_perlang"] = per["ltt"]
                    amin = alpha * min(float((cal["lang"] == lg).mean()) for lg in LANGS)
                    lw = C.fixed_sequence(cal["s"], cal["u"], grid, amin, delta / A)
                    lam["ltt_marginal_worstgroup"] = {lg: lw for lg in LANGS}
                else:
                    lam["knn_ltt_perlang"] = per["ltt"]
            lam["always_premium"] = {lg: -np.inf for lg in LANGS}
            lam["always_cheap"] = {lg: np.inf for lg in LANGS}
            test = {n: sel(d, ~in_cal) for n, d in D.items()}
            risks = {}
            for method in METHODS:
                if method == "random_matched":
                    continue
                t = test["knn" if method.startswith("knn") else "lr"]
                ms = {}
                for lg in LANGS:
                    sub = sel(t, t["lang"] == lg)
                    if len(sub["u"]) == 0:
                        continue
                    ms[lg] = metrics(sub, sub["s"] <= lam[method][lg])
                    for k, v in ms[lg].items():
                        acc[(method, alpha, lg)][k].append(v)
                    acc[(method, alpha, lg)]["violated"].append(float(ms[lg]["risk"] > alpha))
                    if method == "ltt_perlang":  # random routing at matched cheap share
                        rm = random_metrics(sub, ms[lg]["cheap_share"])
                        for k, v in rm.items():
                            acc[("random_matched", alpha, lg)][k].append(v)
                        acc[("random_matched", alpha, lg)]["violated"].append(float(rm["risk"] > alpha))
                if set(ms) == set(LANGS):
                    risks[method] = ms
            for method, ms in risks.items():
                for p in (0.1, 0.9):
                    mix[(method, alpha, p)].append(float((1 - p) * ms["english"]["risk"] + p * ms["hinglish"]["risk"] > alpha))
    out = {"scorer": desc, "n_cert_items": len(items), "n_cert_rows": len(cert), "splits": splits, "delta": delta,
           "auroc_cert": auroc, "results": [], "mix_shift_violation": []}
    for (method, alpha, lg), m in sorted(acc.items(), key=lambda kv: (kv[0][1], METHODS.index(kv[0][0]), kv[0][2])):
        ap = m["apgr"]
        out["results"].append({"method": method, "alpha": alpha, "lang": lg,
                               "violation_rate": round(float(np.mean(m["violated"])), 3),
                               "mean_risk": round(float(np.mean(m["risk"])), 4),
                               "cheap_share": round(float(np.mean(m["cheap_share"])), 3),
                               "cost_saving": round(float(np.mean(m["saving"])), 3),
                               "apgr": None if np.all(np.isnan(ap)) else round(float(np.nanmean(ap)), 3)})
    for (method, alpha, p), v in sorted(mix.items(), key=lambda kv: (kv[0][1], METHODS.index(kv[0][0]), kv[0][2])):
        out["mix_shift_violation"].append({"method": method, "alpha": alpha, "hinglish_share": p,
                                           "violation_rate": round(float(np.mean(v)), 3)})
    return out


def table(rep, alphas):
    def get(res, m, a, lg):
        return next(r for r in res if r["method"] == m and r["alpha"] == a and r["lang"] == lg)

    def f(x):
        return "n/a" if x is None else x
    lines = []
    for name, r in rep.items():
        flag = " (UNDERPOWERED: few u=1 rows)" if name == "grades" else ""
        res = r["results"]
        au = "; ".join(f"{lg} {f(v['lr'] and round(v['lr'], 3))} / {f(v['knn'] and round(v['knn'], 3))} (n_u1={v['n_u1']})"
                       for lg, v in r["auroc_cert"].items())
        lines += [f"## {name}{flag}: cert items {r['n_cert_items']}, rows {r['n_cert_rows']}, {r['splits']} re-splits, delta={r['delta']}",
                  "", f"AUROC on cert (LR / kNN): {au}", ""]
        for a in [0.10] + [x for x in alphas if x != 0.10]:
            lines += [f"### alpha = {a}", "",
                      "| method | EN viol | EN risk | EN cheap | EN saving | EN APGR | HI viol | HI risk | HI cheap | HI saving | HI APGR |",
                      "|---|---|---|---|---|---|---|---|---|---|---|"]
            for m in METHODS:
                try:
                    e, h = get(res, m, a, "english"), get(res, m, a, "hinglish")
                except StopIteration:
                    continue
                lines.append(f"| {m} | {e['violation_rate']} | {e['mean_risk']} | {e['cheap_share']} | {e['cost_saving']} | {f(e['apgr'])} "
                             f"| {h['violation_rate']} | {h['mean_risk']} | {h['cheap_share']} | {h['cost_saving']} | {f(h['apgr'])} |")
            lines.append("")
        lines += ["### Mix shift (H3): violation rate of Hinglish-share-resampled test risk > alpha", "",
                  "| method | alpha | HI share 0.1 | HI share 0.9 |", "|---|---|---|---|"]
        for m in ("ltt_marginal", "ltt_perlang", "emp_marginal", "crc_marginal", "emp_perlang", "crc_perlang"):
            for a in alphas:
                v = {x["hinglish_share"]: x["violation_rate"] for x in r["mix_shift_violation"]
                     if x["method"] == m and x["alpha"] == a}
                lines.append(f"| {m} | {a} | {v.get(0.1)} | {v.get(0.9)} |")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=1000)
    ap.add_argument("--alphas", default="0.05,0.10,0.20")
    ap.add_argument("--delta", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--out-suffix", default="")
    ap.add_argument("--paired-gsm8k", action="store_true", help="pair 2 only, GSM8K items present in both languages")
    a = ap.parse_args()
    alphas = [float(x) for x in a.alphas.split(",")]
    names = ("grades_pair2.jsonl",) if a.paired_gsm8k else ("grades_pair2.jsonl", "grades.jsonl")
    rep = {Path(g).stem: run(g, a.splits, alphas, a.delta, a.seed, a.paired_gsm8k) for g in names}
    if "grades" in rep:
        rep["grades"]["note"] = "pair 1 is underpowered (very few u=1 rows)"
    (BENCH / f"router_baselines_report{a.out_suffix}.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    (BENCH / f"router_baselines_table{a.out_suffix}.md").write_text(table(rep, alphas), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
