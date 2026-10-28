"""Opt-in multilingual question-to-clause relevance; never rewrites evidence.

Model loading is lazy at the caller. Only passage units and the question enter
the scorer; answer choices, gold labels and previous model answers are absent.
"""
from __future__ import annotations

import math
from collections import OrderedDict

from gateway.modules.m2_compressor.hinglish_budget import character_scores

ENCODER_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ENCODER_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
WINDOW_TOKENS = 128
WINDOW_OVERLAP = 32
FUSION_K = 60


def reciprocal_ranks(scores):
    """Competition ranks keep tied scores tied, independent of source order."""
    return [1 / (FUSION_K + 1 + sum(other > score for other in scores)) for score in scores]


class SemanticRanker:
    def __init__(self, encoder, *, fused=False):
        self.encoder = encoder
        self.fused = fused

    def __call__(self, units, question):
        if not units:
            return []
        if not question.strip():
            return character_scores(units, question)
        semantic = list(self.encoder.scores(units, question))
        if len(semantic) != len(units) or any(not math.isfinite(s) for s in semantic):
            raise ValueError("Semantic scorer returned invalid scores")
        if not self.fused:
            return semantic
        lexical = character_scores(units, question)
        # Constant evidence supplies no ordering information.
        sem_ranks = reciprocal_ranks(semantic) if len(set(semantic)) > 1 else [0.0] * len(units)
        lex_ranks = reciprocal_ranks(lexical) if len(set(lexical)) > 1 else [0.0] * len(units)
        return [a + b for a, b in zip(sem_ranks, lex_ranks, strict=True)]


def window_max_scores(embeddings, owners, unit_count):
    """Max cosine over every source/query window, including long-unit tails.

    Embeddings must already be L2 normalized. Windows affect ranking only;
    the compressor still emits complete original units before its shared cap.
    """
    import torch

    if len(embeddings) != len(owners):
        raise ValueError("Missing window ownership")
    query = embeddings[owners == 0]
    if not len(query):
        raise ValueError("Missing question windows")
    scores = []
    for owner in range(1, unit_count + 1):
        windows = embeddings[owners == owner]
        if not len(windows):
            raise ValueError("Missing evidence windows")
        scores.append(float(torch.max(windows @ query.T)))
    return scores


class MultilingualWindowEncoder:
    """Pinned MiniLM mean pooling, with bounded batches and overlapping windows."""
    def __init__(self, *, device="cpu", local_files_only=False):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.device = device
        options = dict(revision=ENCODER_REVISION, local_files_only=local_files_only, trust_remote_code=False)
        self.tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL, **options)
        if not self.tokenizer.is_fast:
            raise ValueError("Window ownership requires a fast tokenizer")
        self.model = AutoModel.from_pretrained(ENCODER_MODEL, **options).to(device).eval()
        if device.startswith("cuda"):
            self.model = self.model.to(dtype=torch.float16)
        self.cache = OrderedDict()

    def scores(self, units, question):
        import torch
        from torch.nn.functional import normalize

        key = (question, tuple(units))
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        encoded = self.tokenizer(
            [question, *units], padding=True, truncation=True, max_length=WINDOW_TOKENS,
            stride=WINDOW_OVERLAP, return_overflowing_tokens=True, return_tensors="pt",
        )
        owners = encoded.pop("overflow_to_sample_mapping")
        pooled = []
        for start in range(0, len(owners), 16):
            batch = {name: tensor[start:start + 16].to(self.device) for name, tensor in encoded.items()}
            with torch.inference_mode():
                hidden = self.model(**batch).last_hidden_state.float()
                mask = batch["attention_mask"].unsqueeze(-1).float()
                mean = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                pooled.append(normalize(mean, p=2, dim=1).cpu())
        scores = tuple(window_max_scores(torch.cat(pooled), owners, len(units)))
        self.cache[key] = scores
        if len(self.cache) > 128:
            self.cache.popitem(last=False)
        return scores
