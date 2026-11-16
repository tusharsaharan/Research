"""Exact text token counts for a fingerprinted tokenizer artifact, with no fallback.

An artifact being exact does not establish parity with an Ollama/GGUF serving
tokenizer or its chat template. Callers must record and verify that separately.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


class ArtifactTokenCounter:
    def __init__(self, path: Path, expected_sha256: str, *, model_id: str, scope: str):
        from tokenizers import Tokenizer
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected_sha256:
            raise ValueError('Tokenizer artifact hash mismatch')
        if scope not in {'native_text_verified','reference_text_transfer'}:
            raise ValueError('Declare verified native text or reference text transfer scope')
        self._tokenizer=Tokenizer.from_file(str(path))
        self.receipt=dict(model_id=model_id,sha256=actual,scope=scope,chat_template_parity='unverified')

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text,add_special_tokens=False).ids)
