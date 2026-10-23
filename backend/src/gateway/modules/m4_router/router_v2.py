"""Router v2 features and serving wrapper (exploratory; see scripts/bench/router_v2.py).
Loaded only when ROUTER_SCORER=v2 and data/router_artifacts/router_v2.pkl exists."""
from __future__ import annotations

import re

import numpy as np

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio, language_group

EXTRA_NAMES = ["n_digits", "n_numbers", "n_operator_words", "n_chars", "n_sentences", "math_markers", "entity_density"]
_OPS = re.compile(r"\b(plus|minus|times|divided|multiply|sum|total|difference|product|ratio|percent|average|"
                  r"more than|less than|jod|ghata|guna|kul|pratishat|gunaa|baaki)\b", re.I)
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_SENT = re.compile(r"[.!?।]+")


def lexical_features(text: str) -> list[float]:
    """Cheap lexical/difficulty features (reuses difficulty.py's math/entity regexes)."""
    from gateway.modules.m4_router.difficulty import _ENTITY, _MATH

    n = max(len(text.split()), 1)
    return [float(sum(c.isdigit() for c in text)), float(len(_NUM.findall(text))), float(len(_OPS.findall(text))),
            float(len(text)), float(max(len([s for s in _SENT.split(text) if s.strip()]), 1)),
            float(len(_MATH.findall(text))), len(_ENTITY.findall(text)) / n]


def base_features(texts, flags):
    return np.array([[float(h), code_mix_ratio(t), np.log1p(len(t.split()))] for t, h in zip(texts, flags)]).reshape(len(texts), 3)


def extra_matrix(texts):
    X = np.array([lexical_features(t) for t in texts]).reshape(len(texts), len(EXTRA_NAMES))
    return np.log1p(X)  # no fitted scaler, so serving == training


def build_X(kind, texts, flags, emb, pca=None):
    b = base_features(texts, flags)
    if kind == "prereg":
        return np.hstack([b, emb])
    ex = extra_matrix(texts)
    if kind == "gbm":
        return np.hstack([b, ex, pca.transform(emb)])
    return np.hstack([b, ex, emb])  # lex, lex_tuned


class V2Scorer:
    """Serving wrapper around the router_v2.pkl bundle: .score(text) -> P(u=1)."""

    def __init__(self, bundle: dict) -> None:
        self.clf, self.description, self.kind = bundle["clf"], bundle["description"], bundle["kind"]
        self.pca = bundle.get("pca")
        self.use_embeddings = True

    def score(self, text: str) -> float:
        from gateway.modules.m4_router.certified import _encoder

        enc = _encoder()
        if enc is None:
            raise RuntimeError("sentence-transformers unavailable")
        emb = enc.encode([text], normalize_embeddings=True, show_progress_bar=False)
        X = build_X(self.kind, [text], [language_group(text) == "hinglish"], emb, self.pca)
        return float(self.clf.predict_proba(X)[0, 1])
