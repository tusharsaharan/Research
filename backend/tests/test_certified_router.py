from __future__ import annotations

import json
import math
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression

from gateway.config import Settings
from gateway.modules.m4_router.certified import featurize, load_certified, premium_threshold
from gateway.service import Gateway


def _write_artifacts(data_dir, hinglish_cheap_max, english_cheap_max):
    texts = ["what is two plus two", "yaar mera wifi slow hai kya karun", "explain binary search please",
             "bhai ye sawal samjha do na", "capital of france", "mujhe python sikhna hai"]
    flags = [False, True, False, True, False, True]
    X = featurize(texts, flags, use_embeddings=False)
    clf = LogisticRegression().fit(X, [0, 1, 0, 1, 0, 1])
    d = data_dir / "router_artifacts"
    d.mkdir(parents=True)
    (d / "certified_router.pkl").write_bytes(pickle.dumps({"clf": clf, "use_embeddings": False, "description": "test"}))
    (d / "certified_thresholds.json").write_text(json.dumps({
        "serve_alpha": "0.10", "delta": 0.1, "n_cert_rows": 6, "preliminary": True,
        "thresholds": {"0.10": {
            "per_language": {"english": {"cheap_if_score_at_most": english_cheap_max},
                             "hinglish": {"cheap_if_score_at_most": hinglish_cheap_max}},
            "marginal": {"cheap_if_score_at_most": None}}}}))


def test_premium_threshold_conversion():
    assert premium_threshold(None) == 0.0  # nothing certified -> everything premium
    lam = 0.42
    t = premium_threshold(lam)
    assert lam < t and not (lam >= t)  # score == lam is still routed cheap


def test_gateway_serves_certified_per_language_thresholds(tmp_path):
    _write_artifacts(tmp_path, hinglish_cheap_max=None, english_cheap_max=1.0)
    assert load_certified(tmp_path) is not None
    gw = Gateway(Settings(dry_run=True, data_dir=tmp_path, use_certified_router=True))
    assert gw.router_source.startswith("certified")
    cal = gw.calibrator
    assert cal.route_premium(0.99, "hinglish") is True  # Hinglish not certifiable -> premium
    assert cal.route_premium(0.99, "english") is False  # English certified up to 1.0 -> cheap
    assert cal.route_premium(0.0, "mixed_script") is True  # uncertified group -> marginal (all premium)
    assert math.isclose(cal.alpha, 0.10)


def test_gateway_without_artifacts_uses_heuristic(tmp_path):
    gw = Gateway(Settings(dry_run=True, data_dir=tmp_path, use_certified_router=True))
    assert gw.router_source.startswith("heuristic")


def test_research_summary_endpoint():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.get("/v1/research/summary")
    assert r.status_code == 200
    body = r.json()
    assert {"router_source", "progress", "summary", "certification"} <= set(body)


def test_research_page_served():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.get("/research")
    assert r.status_code == 200
    assert "/v1/research/summary" in r.text
