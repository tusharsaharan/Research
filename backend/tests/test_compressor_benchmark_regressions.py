"""Failures found by the 8,000-prompt compression benchmark (scripts/bench/compress_eval.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m2_compressor.safety_span import detect_spans
from gateway.tokenizer import TokenCounter

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def comp():
    return Compressor(counter=TokenCounter(), use_crf=True, crf_model_path=DATA / "models" / "crf_compressor.pkl",
                      tfidf_path=DATA / "tfidf" / "hinglish_idf.json")


@pytest.mark.parametrize(
    "text, must_keep",
    [
        ("Ek algorithm likho jo array se duplicates remove kar de. arr = [1, 2, 2, 3, 4, 4, 5]", "[1, 2, 2, 3, 4, 4, 5]"),
        ("Do lists ko combine karke ek list banao. List 1: [1, 2, 3], List 2: [4, 5, 6]", "[1, 2, 3]"),
        ("valid intervals? (III) [2, 2] U [3, 3] yaar batao", "[2, 2] U [3, 3]"),
        ('The answer is: "No, no, no." bhai isko classify karo', '"No, no, no."'),
        ("yaar 2x + 3 = 7 solve karo please", "2x + 3 = 7"),
    ],
)
@pytest.mark.parametrize("method", ["compress_crf", "compress_heuristic"])
def test_compressors_keep_numeric_groups_quotes_and_math(comp, text, must_keep, method):
    out = getattr(comp, method)(text).compressed
    assert must_keep in out


def test_new_span_kinds_detected():
    kinds = {s.kind for s in detect_spans('x = [1, 2] and "quoted" and 3 + 4 = 7')}
    assert {"numeric_group", "quoted", "math"} <= kinds
