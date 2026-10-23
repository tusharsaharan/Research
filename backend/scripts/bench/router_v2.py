"""Router v2 (offline, exploratory): compare scorers by item-grouped 5-fold CV on
scorer_train ONLY. cert is never read for fitting or selection; pilot only for a final sanity print.

Selection rule (fixed before running): pick v2 only if its mean per-language MIN AUROC
(over folds) beats the prereg scorer's by >= MARGIN; otherwise keep prereg.

    python backend/scripts/bench/router_v2.py
"""
from __future__ import annotations

import json
import pickle

import numpy as np
from common import BENCH, latest_variants, read_jsonl

from gateway.modules.m4_router.certified import ENCODER, artifacts_dir
from gateway.modules.m4_router.router_v2 import EXTRA_NAMES, V2Scorer, build_X, lexical_features  # noqa: F401

LANGS = ("english", "hinglish")
MARGIN = 0.02
CHEAP_SHARE = 0.5
SEED = 20261015
def embeddings(texts):
    cache = {}
    if (BENCH / "adaptive_emb_cache.npz").exists():
        with np.load(BENCH / "adaptive_emb_cache.npz", allow_pickle=True) as z:
            cache.update(zip(map(str, z["keys"]), z["vecs"]))
    own = BENCH / "router_v2_emb_cache.npz"
    if own.exists():
        z = np.load(own, allow_pickle=True)
        cache.update(zip(map(str, z["keys"]), z["vecs"]))
    miss = sorted({t for t in texts if t not in cache})
    if miss:
        from sentence_transformers import SentenceTransformer
        v = SentenceTransformer(ENCODER).encode(miss, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        cache.update(zip(miss, v))
        np.savez(own, keys=np.array(list(cache), dtype=object), vecs=np.asarray(list(cache.values())))
    return np.array([cache[t] for t in texts]), len(miss)


def make_model(kind, X, y, groups):
    """Fit one candidate. lex_tuned picks C by inner grouped CV on the training folds."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold

    if kind in ("prereg", "lex"):
        return LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X, y)
    if kind == "gbm":
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=10,
                                              l2_regularization=1.0, class_weight="balanced", random_state=SEED).fit(X, y)
    best, bc = -1.0, 1.0
    for C in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0):
        aucs = []
        for tr, va in GroupKFold(n_splits=3).split(X, y, groups):
            if y[tr].min() == y[tr].max() or y[va].min() == y[va].max():
                continue
            m = LogisticRegression(max_iter=2000, C=C, class_weight="balanced").fit(X[tr], y[tr])
            aucs.append(roc_auc_score(y[va], m.predict_proba(X[va])[:, 1]))
        if aucs and np.mean(aucs) > best:
            best, bc = float(np.mean(aucs)), C
    m = LogisticRegression(max_iter=2000, C=bc, class_weight="balanced").fit(X, y)
    m.chosen_C = bc
    return m


def auroc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else float("nan")


def proxy(rows, s, share):
    """Route the `share` lowest-score rows cheap; risk, $ saving, premium completion tokens per cheap query."""
    k = int(round(share * len(s)))
    if k == 0:
        return {}
    idx = set(np.argsort(s, kind="stable")[:k].tolist())
    sub = [rows[i] for i in idx]
    base = sum(r["cost_premium_usd"] for r in rows)
    cost = sum(r["cost_cheap_usd"] if i in idx else r["cost_premium_usd"] for i, r in enumerate(rows))
    out = {"risk": float(sum(r["u"] for r in sub) / len(rows)),
           "conditional_cheap_risk": float(np.mean([r["u"] for r in sub])),
           "usd_saving": float(1 - cost / base) if base else 0.0}
    pt = [r["prem_ct"] for r in sub if r.get("prem_ct") is not None]
    nt = [r["prem_ct"] - r["cheap_ct"] for r in sub if r.get("prem_ct") is not None and r.get("cheap_ct") is not None]
    out["prem_completion_tokens_per_cheap_query"] = float(np.mean(pt)) if pt else None
    out["net_completion_tokens_saved_per_cheap_query"] = float(np.mean(nt)) if nt else None
    return out


def load_rows(grades="grades.jsonl", include_pilot=True):
    texts = {(r["item_id"], "english"): r["question_en"] for r in read_jsonl(BENCH / "items.jsonl")}
    texts |= {(v["item_id"], v["lang"]): v["text"] for v in latest_variants()}
    tok = {}
    for a in (read_jsonl(BENCH / "answers.jsonl") if grades == "grades.jsonl" else []):
        if a.get("status") == "ok" and a.get("usage"):
            tok[(a["item_id"], a["lang"], a["tier"])] = a["usage"].get("completion_tokens")  # includes reasoning tokens
    splits = ("scorer_train", "pilot") if include_pilot else ("scorer_train",)
    rows = [r for r in read_jsonl(BENCH / grades) if r["lang"] in LANGS and r["split"] in splits]
    for r in rows:  # cert rows are deliberately not loaded
        r["text"] = texts[(r["item_id"], r["lang"])]
        r["prem_ct"] = tok.get((r["item_id"], r["lang"], "premium"))
        r["cheap_ct"] = tok.get((r["item_id"], r["lang"], "cheap"))
    return rows


def main() -> None:
    from sklearn.decomposition import PCA
    from sklearn.model_selection import GroupKFold

    rows = load_rows()
    tr = [r for r in rows if r["split"] == "scorer_train"]
    pilot = [r for r in rows if r["split"] == "pilot"]
    E, n_new = embeddings([r["text"] for r in tr + pilot])
    Etr, Epi = E[: len(tr)], E[len(tr):]
    y = np.array([r["u"] for r in tr])
    lang = np.array([r["lang"] for r in tr])
    groups = np.array([r["item_id"] for r in tr])
    texts = [r["text"] for r in tr]
    flags = [r["lang"] == "hinglish" for r in tr]
    kinds = ["prereg", "lex", "lex_tuned", "gbm"]
    cv = {k: {"fold_auc": {lg: [] for lg in LANGS}, "oof": np.zeros(len(tr))} for k in kinds}
    for a, b in GroupKFold(n_splits=5).split(Etr, y, groups):
        assert not set(groups[a]) & set(groups[b])
        pca = PCA(n_components=16, random_state=SEED).fit(Etr[a])
        for k in kinds:
            X = build_X(k, texts, flags, Etr, pca if k == "gbm" else None)
            m = make_model(k, X[a], y[a], groups[a])
            s = m.predict_proba(X[b])[:, 1]
            cv[k]["oof"][b] = s
            for lg in LANGS:
                msk = lang[b] == lg
                cv[k]["fold_auc"][lg].append(auroc(y[b][msk], s[msk]))
    res = {}
    for k in kinds:
        d = {"auroc": {}}
        for lg in LANGS:
            v = np.array(cv[k]["fold_auc"][lg])
            d["auroc"][lg] = {"mean": round(float(np.nanmean(v)), 4), "sd": round(float(np.nanstd(v)), 4),
                              "n_folds_valid": int((~np.isnan(v)).sum())}
        mins = np.nanmin(np.array([cv[k]["fold_auc"][lg] for lg in LANGS]), axis=0)
        d["fold_min_auroc_mean"] = round(float(np.nanmean(mins)), 4)
        d["pooled_oof_auroc"] = {lg: round(auroc(y[lang == lg], cv[k]["oof"][lang == lg]), 4) for lg in LANGS}
        d["proxy_at_cheap_share"] = {}
        for lg in LANGS:
            idx = np.where(lang == lg)[0]
            d["proxy_at_cheap_share"][lg] = {kk: (round(vv, 4) if vv is not None else None)
                                             for kk, vv in proxy([tr[i] for i in idx], cv[k]["oof"][idx], CHEAP_SHARE).items()}
        res[k] = d
    best = max([k for k in kinds if k != "prereg"], key=lambda k: res[k]["fold_min_auroc_mean"])
    gain = round(res[best]["fold_min_auroc_mean"] - res["prereg"]["fold_min_auroc_mean"], 4)
    valid = all(res[k]["auroc"][lg]["n_folds_valid"] == 5 for k in ("prereg", best) for lg in LANGS)
    v2_wins = bool(valid and gain >= MARGIN)  # AUROC needs both classes in every test fold, else rule is undecidable -> keep prereg
    report = {"protocol": "item-grouped 5-fold CV on scorer_train only", "n_rows": len(tr), "n_items": len(set(groups)),
              "u_rate": {lg: round(float(y[lang == lg].mean()), 4) for lg in LANGS}, "cheap_share": CHEAP_SHARE,
              "rows_with_token_counts": sum(r["prem_ct"] is not None for r in tr), "new_embeddings_encoded": n_new,
              "selection_rule": f"v2 iff best candidate mean per-language-min AUROC - prereg >= {MARGIN}, and AUROC defined (both classes) in all 5 folds per language",
              "all_folds_valid": valid, "n_positives": {lg: int(y[lang == lg].sum()) for lg in LANGS}, "candidates": res, "best_candidate": best, "gain_vs_prereg": gain, "v2_selected": bool(v2_wins)}
    if v2_wins:
        pca = PCA(n_components=16, random_state=SEED).fit(Etr)
        X = build_X(best, texts, flags, Etr, pca if best == "gbm" else None)
        m = make_model(best, X, y, groups)
        bundle = {"clf": m, "kind": best, "pca": pca if best == "gbm" else None, "use_embeddings": True,
                  "description": f"router_v2 [{best}] {ENCODER} + lexical features, fit on scorer_train"}
        d = artifacts_dir(BENCH.parent)
        d.mkdir(parents=True, exist_ok=True)
        (d / "router_v2.pkl").write_bytes(pickle.dumps(bundle))
        Xp = build_X(best, [r["text"] for r in pilot], [r["lang"] == "hinglish" for r in pilot], Epi, bundle["pca"])
        sp = m.predict_proba(Xp)[:, 1]
        pl = np.array([r["lang"] for r in pilot])
        yp = np.array([r["u"] for r in pilot])
        report["pilot_sanity_auroc"] = {lg: round(auroc(yp[pl == lg], sp[pl == lg]), 4) for lg in LANGS}
    (BENCH / "router_v2_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("report ->", BENCH / "router_v2_report.json")


if __name__ == "__main__":
    main()
