import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
import router_train as rt
from router_v2 import proxy


def test_routing_risk_uses_all_queries():
    rows = [{"u": u, "cost_premium_usd": 1, "cost_cheap_usd": 0} for u in (1, 0, 0, 0)]
    metrics = proxy(rows, np.arange(4), 0.5)
    assert metrics["risk"] == 0.25
    assert metrics["conditional_cheap_risk"] == 0.5


def test_single_class_language_folds_cannot_select():
    cs = {k: {"all_folds_valid": True, "fold_min_auroc_mean": 0.6} for k in rt.KINDS}
    cs["lex"].update(all_folds_valid=False, fold_min_auroc_mean=0.99)
    cs["gbm"]["fold_min_auroc_mean"] = 0.63
    assert rt.select(cs) == ("gbm", 0.030000000000000027, True)
    cs["prereg"]["all_folds_valid"] = False
    assert rt.select(cs) == (None, None, False)


def test_pair_filter_and_cert_exclusion(monkeypatch):
    rows = [{"item_id": "a", "lang": lg, "split": "scorer_train", "source": "gsm8k"} for lg in rt.LANGS]
    rows += [{"item_id": "b", "lang": "english", "split": "scorer_train", "source": "arc"}]
    def load(grades, include_pilot):
        assert include_pilot is False
        return rows
    monkeypatch.setattr(rt, "load_rows", load)
    assert len(rt.training_rows("grades_pair2.jsonl", paired=True)) == 2
    rows.append({"item_id": "c", "lang": "english", "split": "cert", "source": "gsm8k"})
    with pytest.raises(ValueError, match="only scorer_train"):
        rt.training_rows("grades_pair2.jsonl")


def test_grouped_folds_hold_both_language_variants_out(monkeypatch):
    rows = [{"item_id": str(i), "lang": lg, "u": i % 2, "text": f"query {i}"} for i in range(30) for lg in rt.LANGS]
    def fit(kind, X, y, groups):
        class Model:
            def predict_proba(self, val):
                # The first embedding column is the source item ID.
                assert not set(val[:, -2].astype(int)) & set(groups.astype(int))
                return np.tile([0.5, 0.5], (len(val), 1))
        return Model()
    monkeypatch.setattr(rt, "make_model", fit)
    emb = np.array([[int(r["item_id"]), 0] for r in rows])
    for fold in range(5):
        idx, scores = rt.fold_task(rows, emb, fold, "prereg")
        assert len(idx) == len(scores) == 12


def test_certification_rejects_cross_pair_or_changed_training(tmp_path, monkeypatch):
    import pickle
    from types import SimpleNamespace
    import certify

    candidate = tmp_path / "candidate.pkl"
    args = SimpleNamespace(candidate=candidate, grades="grades.jsonl")
    candidate.write_bytes(pickle.dumps({"grades": "grades_pair2.jsonl"}))
    with pytest.raises(ValueError, match="different model pair"):
        certify.score_v2([], {}, args)
    candidate.write_bytes(pickle.dumps({"grades": "grades.jsonl", "training_sha256": "stale"}))
    monkeypatch.setattr(rt, "training_rows", lambda *a: [])
    with pytest.raises(ValueError, match="training rows changed"):
        certify.score_v2([], {}, args)


def test_export_v2_binds_own_model_and_thresholds(tmp_path, monkeypatch):
    import hashlib
    import json
    from types import SimpleNamespace
    import certify

    monkeypatch.setattr(certify, "BENCH", tmp_path / "bench")
    args = SimpleNamespace(alphas="0.10", delta=0.1, serve_alpha=0.1, scorer="v2", grades="grades.jsonl")
    certify.export_router({"description": "test"}, [], {}, np.array([0.5]), args)
    out = tmp_path / "router_artifacts"
    meta = json.loads((out / "router_v2_thresholds.json").read_text())
    assert meta["model_sha256"] == hashlib.sha256((out / "router_v2.pkl").read_bytes()).hexdigest()
    assert meta["thresholds"]["0.10"]["per_language"]["hinglish"]["cheap_if_score_at_most"] is None
    assert not (out / "certified_router.pkl").exists()


def test_explicit_kaggle_token_overrides_default_account(tmp_path, monkeypatch):
    import os
    import router_kaggle

    (tmp_path / "access_token").write_text("test-only-token")
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("KAGGLE_API_TOKEN", "old-account-token")
    router_kaggle.bind_token()
    assert os.environ["KAGGLE_API_TOKEN"] == str(tmp_path / "access_token")
