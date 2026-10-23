from __future__ import annotations

import pickle
import hashlib
import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from gateway.modules.m4_router.certified import load_certified
from gateway.modules.m4_router.router_v2 import EXTRA_NAMES, build_X, extra_matrix, lexical_features


def test_lexical_features_shape_and_values():
    f = lexical_features("If 3 apples plus 12 pears cost Rs. 50. How many? Total?")
    assert len(f) == len(EXTRA_NAMES)
    assert f[0] == 5 and f[1] == 3 and f[2] >= 2 and f[4] == 4


def test_build_X_widths():
    texts = ["what is 2 plus 2", "yaar 5 aam ka total kitna hai"]
    emb = np.zeros((2, 384))
    assert extra_matrix(texts).shape == (2, len(EXTRA_NAMES))
    assert build_X("prereg", texts, [False, True], emb).shape == (2, 3 + 384)
    assert build_X("lex", texts, [False, True], emb).shape == (2, 3 + len(EXTRA_NAMES) + 384)


def test_env_flag_default_prereg(tmp_path, monkeypatch):
    d = tmp_path / "router_artifacts"
    d.mkdir()
    X = np.array([[0.0] * 3, [1.0] * 3])
    clf = LogisticRegression().fit(X, [0, 1])
    (d / "certified_router.pkl").write_bytes(pickle.dumps({"clf": clf, "use_embeddings": False, "description": "p"}))
    (d / "certified_thresholds.json").write_text("{}")
    monkeypatch.delenv("ROUTER_SCORER", raising=False)
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"
    monkeypatch.setenv("ROUTER_SCORER", "v2")  # no router_v2.pkl -> still prereg
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"
    Xv = build_X("lex", ["a 1"], [False], np.zeros((1, 4)))
    m = LogisticRegression().fit(np.vstack([Xv, Xv + 1]), [0, 1])
    (d / "router_v2.pkl").write_bytes(pickle.dumps({"clf": m, "kind": "lex", "pca": None, "description": "v2"}))
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"  # uncalibrated v2 must not use prereg thresholds
    metadata = {"model_sha256": hashlib.sha256((d / "router_v2.pkl").read_bytes()).hexdigest(),
                "grades": "grades.jsonl", "thresholds": {"test": "v2-only"}}
    (d / "router_v2_thresholds.json").write_text(json.dumps(metadata))
    scorer, thresholds = load_certified(tmp_path)
    assert type(scorer).__name__ == "V2Scorer" and thresholds == metadata
    metadata["grades"] = "grades_pair2.jsonl"
    (d / "router_v2_thresholds.json").write_text(json.dumps(metadata))
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"
    metadata.update(grades="grades.jsonl", model_sha256="stale")
    (d / "router_v2_thresholds.json").write_text(json.dumps(metadata))
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"
    (d / "router_v2_thresholds.json").write_text("broken json")
    assert type(load_certified(tmp_path)[0]).__name__ == "CertifiedScorer"


def test_serving_keeps_certified_score_precision(monkeypatch):
    from gateway.modules.m4_router import certified

    class Classifier:
        def predict_proba(self, X):
            return np.array([[1 - 0.12345649, 0.12345649]])

    scorer = certified.CertifiedScorer({"clf": Classifier(), "use_embeddings": False, "description": "test"})
    assert scorer.score("test") == 0.12345649
    assert scorer.score("test") > 0.1234564  # rounding would change this routing decision
