"""Offline regression tests for resumable baseline build/export/grading."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def bench(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
    module = importlib.import_module("baselines2")
    monkeypatch.setattr(module, "BENCH", tmp_path)
    monkeypatch.setitem(sys.modules, "gateway.tokenizer", SimpleNamespace(
        TokenCounter=lambda: SimpleNamespace(count=lambda text: len(text.split()))))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(set_num_threads=lambda _: None))
    monkeypatch.setitem(sys.modules, "llmlingua", None)
    return module


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_bm25_only_needs_no_model_and_emits_no_fake_llml(bench):
    variants = bench.Compressors(["bm25"]).run("First answer here. Other things elsewhere.", "answer")
    assert set(variants) == {"bm25@0.5", "bm25@0.33"}


@pytest.mark.parametrize("family", ["longllml", "longllml2"])
def test_longllml_new_outputs_remain_versioned(bench, monkeypatch, family):
    calls = []
    def compress(*args, **kwargs):
        calls.append(kwargs)
        return {"compressed_prompt": "answer"}
    monkeypatch.setitem(sys.modules, "llmlingua", SimpleNamespace(
        PromptCompressor=lambda *args, **kwargs: SimpleNamespace(compress_prompt=compress)))
    variants = bench.Compressors([family]).run("First answer here. Other things elsewhere.", "answer")
    assert set(variants) == {"longllml2@0.5", "longllml2@0.33"}
    assert len(calls) == 2
    assert all(call["rank_method"] == "longllmlingua" for call in calls)


def test_failed_model_is_not_saved_as_unchanged_success(bench, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("offline model failure")
    monkeypatch.setitem(sys.modules, "llmlingua", SimpleNamespace(
        PromptCompressor=lambda *args, **kwargs: SimpleNamespace(compress_prompt=fail)))
    assert bench.Compressors(["llml2L"]).run("First answer here.", "answer") == {}


def test_resume_adds_only_missing_method_rates_and_then_skips(bench, monkeypatch):
    path = bench.BENCH / "round3" / "hotpot.1of1.jsonl"
    write_rows(path, [{"id": "one", "tag": "", "variants": {"bm25@0.5": "old"}, "kept": {}}])
    calls = []
    class FakeCompressors:
        def __init__(self, methods):
            self.count = lambda text: len(text.split())
        def run(self, text, question, variants=None):
            calls.append(set(variants))
            return {variant: "new" for variant in variants}
    monkeypatch.setattr(bench, "Compressors", FakeCompressors)
    monkeypatch.setattr(bench, "units", lambda _: iter([("one", "", "some input text", "question")]))
    bench.build("hotpot", "1/1", ["bm25", "bhybrid"], "round3")
    assert calls == [{"bm25@0.33", "bhybrid@0.5", "bhybrid@0.33"}]
    rows = bench.read_jsonl(path)
    assert len(rows) == 2
    assert set(rows[1]["variants"]) == calls[0]
    bench.build("hotpot", "1/1", ["bm25", "bhybrid"], "round3")
    assert len(calls) == 1
    assert len(bench.read_jsonl(path)) == 2


def test_run_only_computes_requested_missing_rate(bench, monkeypatch):
    calls = []
    monkeypatch.setattr(bench, "bm25_select", lambda text, question, rate, count: calls.append(rate) or "answer")
    assert bench.Compressors(["bm25"]).run("some context", "q", variants={"bm25@0.33"}) == {"bm25@0.33": "answer"}
    assert calls == [0.33]


def stub_export_modules(monkeypatch):
    monkeypatch.setitem(sys.modules, "belebele_cm", SimpleNamespace(mcq=lambda *args: "mcq"))
    monkeypatch.setitem(sys.modules, "collect", SimpleNamespace(SYSTEM={"mcq": "mcq system"}))
    monkeypatch.setitem(sys.modules, "hotpot", SimpleNamespace(SYSTEM="qa system", clean=lambda text: text,
        f1=lambda text, gold: float(text == gold)))


def test_export_creates_destination_and_deduplicates_input_rows(bench, monkeypatch):
    stub_export_modules(monkeypatch)
    write_rows(bench.BENCH / "hotpot" / "items.jsonl", [{"id": "one", "question": "q"}])
    row = {"id": "one", "tag": "", "variants": {"bm25@0.5": "answer"}, "kept": {}}
    write_rows(bench.BENCH / "round3" / "hotpot.1of1.jsonl", [row, row])
    bench.export("hotpot", "-pilot", "round3")
    path = bench.BENCH / "kaggle-pilot" / "prompts.jsonl"
    assert len(bench.read_jsonl(path)) == 1
    bench.export("hotpot", "-pilot", "round3")
    assert len(bench.read_jsonl(path)) == 1


def test_grade_respects_custom_methods_and_output_folder(bench, monkeypatch):
    stub_export_modules(monkeypatch)
    write_rows(bench.BENCH / "hotpot" / "items.jsonl", [{"id": "one", "answer": "answer"}])
    write_rows(bench.BENCH / "round3" / "hotpot.1of1.jsonl", [{"id": "one", "tag": "",
        "variants": {"bhybrid@0.5": "answer", "bgraded@0.33": "answer"},
        "kept": {"bhybrid@0.5": 0.5, "bgraded@0.33": 0.33}}])
    answers = bench.BENCH / "kaggle-pilot" / "answers.jsonl"
    write_rows(answers, [{"item_id": "one", "key": "one|english|b2:" + method,
        "model": "Qwen/Qwen2.5-3B-Instruct", "methods": [method], "content": "answer"} for method in
        ("original", "bhybrid@0.5", "bgraded@0.33", "bm25@0.5")])
    bench.grade("hotpot", str(answers), methods=["bhybrid", "bgraded"], outdir="round3")
    report = json.loads((bench.BENCH / "round3" / "hotpot_report.json").read_text(encoding="utf-8"))
    assert set(report["methods"]) == {"bhybrid@0.5", "bgraded@0.33"}
    assert report["methods"]["bgraded@0.33"]["context_tokens_kept"] == 0.33
    assert not (bench.BENCH / "baselines2" / "hotpot_report.json").exists()


def test_default_grade_keeps_historical_and_new_longllml_distinct(bench, monkeypatch):
    stub_export_modules(monkeypatch)
    write_rows(bench.BENCH / "hotpot" / "items.jsonl", [{"id": "one", "answer": "answer"}])
    write_rows(bench.BENCH / "baselines2" / "hotpot.1of1.jsonl", [{"id": "one", "tag": "",
        "variants": {}, "kept": {"longllml@0.5": 0.9, "longllml2@0.5": 0.5}}])
    answers = bench.BENCH / "answers.jsonl"
    write_rows(answers, [{"item_id": "one", "key": "one|english|b2:" + method,
        "model": "Qwen/Qwen2.5-3B-Instruct", "methods": [method], "content": "answer"} for method in
        ("original", "longllml@0.5", "longllml2@0.5")])
    bench.grade("hotpot", str(answers))
    report = json.loads((bench.BENCH / "baselines2" / "hotpot_report.json").read_text(encoding="utf-8"))
    assert report["methods"]["longllml@0.5"]["context_tokens_kept"] == 0.9
    assert report["methods"]["longllml2@0.5"]["context_tokens_kept"] == 0.5


def test_grade_ignores_other_models_and_marks_missing_kept_metadata(bench, monkeypatch):
    stub_export_modules(monkeypatch)
    write_rows(bench.BENCH / "hotpot" / "items.jsonl", [{"id": "one", "answer": "answer"}])
    answers = bench.BENCH / "answers.jsonl"
    rows = [{"item_id": "one", "key": "one|english|b2:" + method,
        "model": "Qwen/Qwen2.5-3B-Instruct", "methods": [method], "content": "answer"}
        for method in ("original", "bgraded@0.5")]
    rows.append(dict(rows[-1], model="other/model", content="incorrect"))
    write_rows(answers, rows)
    bench.grade("hotpot", str(answers), methods=["bgraded"], outdir="round3")
    report = json.loads((bench.BENCH / "round3" / "hotpot_report.json").read_text(encoding="utf-8"))
    method = report["methods"]["bgraded@0.5"]
    assert method["f1"] == 1.0
    assert method["context_tokens_kept"] is None
    assert method["n_with_kept_metadata"] == 0
