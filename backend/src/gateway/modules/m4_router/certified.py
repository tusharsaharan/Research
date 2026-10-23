"""Learned router + per-language certified thresholds, fitted by
backend/scripts/bench/certify.py on real benchmark data.

The same ``featurize`` is used for training and serving so served scores are
exactly the scores the thresholds were certified on.

Artifacts (written by certify.py, git-ignored):
  data/router_artifacts/certified_router.pkl   scikit-learn classifier + metadata
  data/router_artifacts/certified_thresholds.json
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import pickle
from pathlib import Path

import numpy as np

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio, language_group

ENCODER = "paraphrase-multilingual-MiniLM-L12-v2"
_encoder_cache: dict[str, object] = {}


def _encoder():
    if ENCODER not in _encoder_cache:
        try:
            from sentence_transformers import SentenceTransformer

            _encoder_cache[ENCODER] = SentenceTransformer(ENCODER)
        except Exception:
            _encoder_cache[ENCODER] = None
    return _encoder_cache[ENCODER]


def featurize(texts: list[str], hinglish_flags: list[bool], use_embeddings: bool = True) -> np.ndarray:
    base = np.array(
        [[float(h), code_mix_ratio(t), math.log1p(len(t.split()))] for t, h in zip(texts, hinglish_flags)]
    ).reshape(len(texts), 3)
    if not use_embeddings:
        return base
    enc = _encoder()
    if enc is None:
        raise RuntimeError(f"sentence-transformers / {ENCODER} unavailable")
    emb = enc.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    return np.hstack([base, emb])


def artifacts_dir(data_dir: Path | str) -> Path:
    return Path(data_dir) / "router_artifacts"


class CertifiedScorer:
    """P(cheap answer loses quality | query), from the certified router artifact."""

    def __init__(self, bundle: dict) -> None:
        self.clf = bundle["clf"]
        self.use_embeddings = bundle["use_embeddings"]
        self.description = bundle["description"]

    def score(self, text: str) -> float:
        x = featurize([text], [language_group(text) == "hinglish"], self.use_embeddings)
        return float(self.clf.predict_proba(x)[0, 1])


def load_certified(data_dir: Path | str) -> tuple[CertifiedScorer, dict] | None:
    """Return (scorer, thresholds) if certify.py has produced artifacts, else None."""
    d = artifacts_dir(data_dir)
    model, thr = d / "certified_router.pkl", d / "certified_thresholds.json"
    v2_model, v2_thr = d / "router_v2.pkl", d / "router_v2_thresholds.json"
    if os.environ.get("ROUTER_SCORER", "").lower() == "v2" and v2_model.exists() and v2_thr.exists():
        try:
            from gateway.modules.m4_router.router_v2 import V2Scorer

            model_bytes = v2_model.read_bytes()
            thresholds = json.loads(v2_thr.read_text(encoding="utf-8"))
            # A changed ranking needs its own calibration for the gateway's model pair.
            if (thresholds.get("model_sha256") == hashlib.sha256(model_bytes).hexdigest()
                    and thresholds.get("grades") == "grades.jsonl"):
                return V2Scorer(pickle.loads(model_bytes)), thresholds
        except Exception:
            pass  # Invalid/incomplete experimental artifacts leave the prereg router active.
    if not (model.exists() and thr.exists()):
        return None
    try:
        model_bytes = model.read_bytes()
        thresholds = json.loads(thr.read_text(encoding="utf-8"))
        if thresholds.get("model_sha256", hashlib.sha256(model_bytes).hexdigest()) != hashlib.sha256(model_bytes).hexdigest():
            return None
        return CertifiedScorer(pickle.loads(model_bytes)), thresholds
    except Exception:
        return None


def premium_threshold(cheap_max: float | None) -> float:
    """certify.py routes cheap iff score <= lam; the calibrator routes premium iff
    score >= threshold. lam = None means nothing was certifiable -> all premium."""
    if cheap_max is None:
        return 0.0
    return math.nextafter(float(cheap_max), math.inf)
