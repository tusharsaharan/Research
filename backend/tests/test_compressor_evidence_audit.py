import importlib
from pathlib import Path


def test_retention_checks_every_line_and_whole_normalized_tokens(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
    audit = importlib.import_module("compressor_evidence_audit")
    assert audit.contains_answer("First unrelated record.\nTerry Riley was born June 24, 1935.", "June 24, 1935")
    assert not audit.contains_answer("A trained worker.", "train")
    assert not audit.contains_answer("Any context.", "the")
