"""Learned routing scorer (Phase 3, free-only track).

Wraps the Colab-trained artifacts (logreg.pkl / xgb.json / bandit_head.pt)
behind the same interface as DifficultyScorer. Falls back to heuristic when
artifacts are absent so gateway + tests keep passing offline.

Artifacts (gitignored, produced in Colab NB02/NB03):
  backend/data/router_artifacts/logreg.pkl
  backend/data/router_artifacts/xgb.json
  backend/data/router_artifacts/bandit_head.pt
  backend/data/thresholds.json        (frozen taus from NB04)
  backend/data/calibration_real.jsonl (frozen real labels from NB01)

Proxy disclosure: free track uses llama-3.3-70b as premium-proxy
(proxy=True). Do not claim gpt-4o numbers from these artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _artifacts_dir(data_dir: Path | str | None = None) -> Path:
    if data_dir is None:
        backend_root = Path(__file__).resolve().parents[4]
        return backend_root / "data" / "router_artifacts"
    return Path(data_dir) / "router_artifacts"


class LearnedScorer:
    """P(fail|x) predictor with heuristic fallback."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        from gateway.modules.m4_router.difficulty import DifficultyScorer

        self.heuristic = DifficultyScorer()
        self.data_dir = Path(data_dir) if data_dir else None
        self.artifacts = _artifacts_dir(data_dir)
        self._clf = None
        self._encoder = None  # lazy SentenceTransformer; False once known unavailable
        self._backend = "heuristic"
        try:
            import pickle

            p = self.artifacts / "logreg.pkl"
            if p.exists():
                self._clf = pickle.loads(p.read_bytes())
                self._backend = "logreg"
        except Exception:
            self._clf = None
            self._backend = "heuristic"

    @property
    def backend(self) -> str:
        return self._backend

    def _featurize_heuristic(self, text: str) -> list[float]:
        f = self.heuristic.features(text)
        return [
            f.code_mix_ratio,
            f.entity_density,
            min(1.0, f.math_marker_count / 3.0),
            min(1.0, f.char_count / 400.0),
            len(text.split()) / 50.0,
        ]

    def _embed(self, text: str) -> list[float] | None:
        """Same encoder and normalisation as training (run04_supervised.py)."""
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._encoder = SentenceTransformer(EMBEDDING_MODEL)
            except Exception:
                self._encoder = False
        if self._encoder is False:
            return None
        return [float(v) for v in self._encoder.encode([text], normalize_embeddings=True)[0]]

    def predict_proba_fail(self, text: str) -> float:
        """Return P(cheap fails|x) in [0,1].

        Scores must come from the exact features the thresholds were calibrated
        on. If the embedding encoder is unavailable we fall back to the
        heuristic scorer (and say so in ``backend``) instead of zero-padding,
        which would silently produce uncalibrated scores.
        """
        if self._clf is None:
            return float(self.heuristic.score(text))
        try:
            feats = self._featurize_heuristic(text)
            n_expected = int(self._clf.coef_.shape[1])
            if n_expected > len(feats):
                emb = self._embed(text)
                if emb is None or len(feats) + len(emb) != n_expected:
                    self._backend = "heuristic (encoder unavailable)"
                    return float(self.heuristic.score(text))
                feats = feats + emb
            elif n_expected < len(feats):
                return float(self.heuristic.score(text))
            p = float(self._clf.predict_proba([feats])[0, 1])
            return min(1.0, max(0.0, p))
        except Exception:
            return float(self.heuristic.score(text))

    def score(self, text: str) -> float:
        return round(self.predict_proba_fail(text), 6)

    def status(self) -> dict:
        return {"backend": self._backend, "proxy": True, "artifacts_dir": str(self.artifacts)}


def load_thresholds(data_dir: Path | str | None = None) -> dict:
    """Load frozen NB04 thresholds.json if present, else {}."""
    if data_dir is None:
        backend_root = Path(__file__).resolve().parents[4]
        p = backend_root / "data" / "thresholds.json"
    else:
        p = Path(data_dir) / "thresholds.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
