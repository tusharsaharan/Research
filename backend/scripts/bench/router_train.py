"""Train-only router evaluation, with resumable CPU shards and Kaggle GPU parity.

No certification labels or pilot rows enter this program. Candidate family,
five item-grouped folds and selection margin remain those of router_v2.py.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import pickle
from pathlib import Path

import numpy as np

from common import BENCH
from router_v2 import LANGS, MARGIN, SEED, auroc, embeddings, load_rows, make_model, proxy
from gateway.modules.m4_router.router_v2 import base_features, build_X, extra_matrix, lexical_features

KINDS = ("prereg", "lex", "lex_tuned", "gbm")


def training_rows(grades, paired=False):
    rows = load_rows(grades, include_pilot=False)
    if paired:
        ids = {r["item_id"] for r in rows if r["lang"] == "hinglish" and r["source"] == "gsm8k"}
        rows = [r for r in rows if r["item_id"] in ids and r["source"] == "gsm8k"]
        counts = {i: {r["lang"] for r in rows if r["item_id"] == i} for i in ids}
        rows = [r for r in rows if counts[r["item_id"]] == set(LANGS)]
    rows = sorted(rows, key=lambda r: (r["item_id"], r["lang"]))
    if any(r["split"] != "scorer_train" for r in rows):
        raise ValueError("only scorer_train rows are permitted")
    if len({(r["item_id"], r["lang"]) for r in rows}) != len(rows):
        raise ValueError("duplicate training item/language")
    return rows


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def eligible(rows):
    # Every language needs both classes in each of five validation folds.
    return len({r["item_id"] for r in rows}) >= 5 and all(
        sum(r["lang"] == lg and r["u"] == label for r in rows) >= 5
        for lg in LANGS for label in (0, 1))


def fold_task(rows, emb, fold, kind):
    from sklearn.decomposition import PCA
    from sklearn.model_selection import GroupKFold

    y = np.array([r["u"] for r in rows])
    groups = np.array([r["item_id"] for r in rows])
    tr, va = list(GroupKFold(n_splits=5).split(emb, y, groups))[fold]
    assert not set(groups[tr]) & set(groups[va])
    if len(np.unique(y[tr])) < 2:
        raise ValueError("training fold has one class")
    pca = PCA(n_components=min(16, len(tr), emb.shape[1]), random_state=SEED).fit(emb[tr]) if kind == "gbm" else None
    X = build_X(kind, [r["text"] for r in rows], [r["lang"] == "hinglish" for r in rows], emb, pca)
    m = make_model(kind, X[tr], y[tr], groups[tr])
    return va, m.predict_proba(X[va])[:, 1]


def summarize(rows, results):
    y = np.array([r["u"] for r in rows])
    lang = np.array([r["lang"] for r in rows])
    out = {}
    for kind in KINDS:
        oof = np.full(len(rows), np.nan)
        folds = []
        for fold in range(5):
            idx, scores = results[(fold, kind)]
            if np.isfinite(oof[idx]).any():
                raise ValueError("overlapping validation rows")
            oof[idx] = scores
            folds.append([auroc(y[idx][lang[idx] == lg], scores[lang[idx] == lg]) for lg in LANGS])
        if not np.isfinite(oof).all():
            raise ValueError("incomplete out-of-fold predictions")
        a = np.array(folds)
        valid = bool(np.isfinite(a).all())
        out[kind] = {
            "fold_auroc": {lg: [float(v) if np.isfinite(v) else None for v in a[:, j]] for j, lg in enumerate(LANGS)},
            "all_folds_valid": valid,
            "fold_min_auroc_mean": float(a.min(axis=1).mean()) if valid else None,
            "pooled_oof_auroc": {lg: auroc(y[lang == lg], oof[lang == lg]) for lg in LANGS},
            "proxy_at_cheap_share_0.5": {lg: proxy([r for r in rows if r["lang"] == lg], oof[lang == lg], 0.5) for lg in LANGS},
        }
    return out


def select(candidates):
    valid = [k for k in KINDS[1:] if candidates[k]["all_folds_valid"]]
    if not candidates["prereg"]["all_folds_valid"] or not valid:
        return None, None, False
    best = max(valid, key=lambda k: candidates[k]["fold_min_auroc_mean"])
    gain = candidates[best]["fold_min_auroc_mean"] - candidates["prereg"]["fold_min_auroc_mean"]
    return best, gain, bool(gain >= MARGIN)


def algorithm_fingerprint():
    source = "\n".join(inspect.getsource(f) for f in
                       (make_model, fold_task, build_X, base_features, extra_matrix, lexical_features))
    return hashlib.sha256(source.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", default="grades.jsonl")
    ap.add_argument("--paired-gsm8k", action="store_true")
    ap.add_argument("--prepare", action="store_true", help="write train-only JSON and small embedding cache")
    ap.add_argument("--input", type=Path, help="prepared train-only JSON")
    ap.add_argument("--embedding-cache", type=Path)
    ap.add_argument("--shard", help="1-based i/n over the 20 candidate/fold tasks")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--output-dir", type=Path, default=BENCH / "router_training")
    args = ap.parse_args()
    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        rows, name, grades = data["rows"], data["name"], data["grades"]
        if any(r["split"] != "scorer_train" for r in rows):
            raise ValueError("prepared input contains non-training rows")
    else:
        rows = training_rows(args.grades, args.paired_gsm8k)
        grades = Path(args.grades).name
        name = Path(grades).stem + ("_paired_gsm8k" if args.paired_gsm8k else "")
    digest = fingerprint(rows)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    report = {"protocol": "exploratory, item-grouped 5-fold CV on scorer_train only; no certification",
              "grades": grades, "training_sha256": digest, "n_rows": len(rows),
              "n_items": len({r["item_id"] for r in rows}), "selection_margin": MARGIN,
              "n_positives": {lg: sum(r["lang"] == lg and r["u"] == 1 for r in rows) for lg in LANGS},
              "v2_selected": False}
    if not eligible(rows):
        report["status"] = "insufficient training classes for five folds per language"
        (out / f"{name}_report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
        print(report["status"], report["n_positives"])
        return
    cache = args.embedding_cache
    if cache:
        with np.load(cache, allow_pickle=True) as z:
            lookup = dict(zip(map(str, z["keys"]), z["vecs"]))
            emb = np.array([lookup[r["text"]] for r in rows])
    else:
        emb, _ = embeddings([r["text"] for r in rows])
    # Cache identity prevents mixing shards from different encoder runs.
    feature_digest = hashlib.sha256(np.ascontiguousarray(emb).tobytes()).hexdigest()
    report["embedding_sha256"] = feature_digest
    report["algorithm_sha256"] = algorithm_fingerprint()
    import sklearn
    report["versions"] = {"numpy": np.__version__, "scikit_learn": sklearn.__version__}
    run_id = digest[:16] + "_" + feature_digest[:16] + "_" + report["algorithm_sha256"][:16]
    if args.prepare:
        path = out / f"{name}_input.json"
        path.write_text(json.dumps({"rows": rows, "name": name, "grades": grades}, ensure_ascii=False), encoding="utf-8")
        np.savez(out / f"{name}_emb.npz", keys=np.array([r["text"] for r in rows]), vecs=emb)
        print("prepared", len(rows), "training rows ->", path)
        return
    tasks = [(fold, kind) for fold in range(5) for kind in KINDS]
    shard_i, shard_n = (map(int, args.shard.split("/")) if args.shard else (1, 1))
    if not 1 <= shard_i <= shard_n:
        raise ValueError("shard must satisfy 1 <= i <= n")
    results = {}
    for i, (fold, kind) in enumerate(tasks):
        path = out / f"{name}_{run_id}_{fold}_{kind}.npz"
        if args.merge:
            with np.load(path) as z:
                results[(fold, kind)] = (z["idx"], z["scores"])
        elif i % shard_n == shard_i - 1:
            idx, scores = fold_task(rows, emb, fold, kind)
            np.savez(path, idx=idx, scores=scores)
            results[(fold, kind)] = (idx, scores)
    if args.shard:
        print("finished shard", args.shard, name)
        return
    candidates = summarize(rows, results)
    best, gain, selected = select(candidates)
    report.update(candidates=candidates, best_candidate=best, gain_vs_prereg=gain, v2_selected=selected, status="complete")
    if selected:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=min(16, len(rows), emb.shape[1]), random_state=SEED).fit(emb) if best == "gbm" else None
        X = build_X(best, [r["text"] for r in rows], [r["lang"] == "hinglish" for r in rows], emb, pca)
        model = make_model(best, X, np.array([r["u"] for r in rows]), np.array([r["item_id"] for r in rows]))
        bundle = {"clf": model, "kind": best, "pca": pca, "use_embeddings": True,
                  "description": f"router_v2 [{best}], train-only grouped CV, {name}",
                  "grades": grades, "training_sha256": digest, "paired_gsm8k": "_paired_gsm8k" in name}
        # Candidate only: certify.py must bind it to new thresholds before serving.
        (out / f"{name}_candidate.pkl").write_bytes(pickle.dumps(bundle))
    else:
        (out / f"{name}_candidate.pkl").unlink(missing_ok=True)
    (out / f"{name}_report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(name, "best:", best, "gain:", gain, "selected:", selected)


if __name__ == "__main__":
    main()
