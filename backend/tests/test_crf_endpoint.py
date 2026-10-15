"""API wiring tests: the CRF compressor must be reachable from the gateway.

Regression for the demo showing only heuristic-grade compression: the
/v1/compress dispatcher had no "crf" branch and Gateway never passed
use_crf, so explicit or auto requests could never hit the CRF path.
"""

from fastapi.testclient import TestClient

from gateway.modules.m5_gateway.main import app

USER_SENTENCE = (
    "yaar mera hostel ka wifi slow hai, complaint kahan karun? "
    "kal se assignment submit karna hai"
)


def test_compress_methods_lists_crf():
    with TestClient(app) as client:
        r = client.get("/v1/compress/methods")
    assert r.status_code == 200
    assert "crf" in r.json()["methods"]


def test_compress_endpoint_crf_beats_heuristic():
    with TestClient(app) as client:
        r_crf = client.post("/v1/compress", json={"text": USER_SENTENCE, "method": "crf"})
        r_heu = client.post("/v1/compress", json={"text": USER_SENTENCE, "method": "heuristic"})
    assert r_crf.status_code == 200
    assert r_crf.json()["method"] == "crf"
    assert r_heu.status_code == 200
    # CRF drops auxiliaries (hai) that the lexicon path keeps.
    assert r_crf.json()["ratio"] < r_heu.json()["ratio"]
    assert "kahan" in r_crf.json()["compressed"]  # question word survives


def test_compress_endpoint_auto_uses_crf():
    with TestClient(app) as client:
        r = client.post("/v1/compress", json={"text": USER_SENTENCE, "method": "auto"})
    assert r.status_code == 200
    assert r.json()["method"] == "crf"


def test_redteam_endpoint_crf():
    with TestClient(app) as client:
        r = client.post("/v1/compress/redteam", json={"text": USER_SENTENCE, "method": "crf"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "safe"
