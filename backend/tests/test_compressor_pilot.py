"""Pilot packaging, prompt integrity and paired grading without model inference."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def pilot(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
    return importlib.import_module("compressor_pilot")


def dump_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def mcq_input(uid, gold="A"):
    return dict(uid=uid, item_id=uid, dataset="belebele", lang="english", task="mcq",
                context="The entire original context.", question="Which option is correct?",
                options=["first", "second", "third", "fourth"], gold=gold)


@pytest.fixture
def grading_files(pilot, monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "METHODS", ("bhybrid_v2", "bm25"))
    monkeypatch.setattr(pilot, "RATES", (0.5,))
    rows = [mcq_input("first", "A"), mcq_input("second", "B")]
    data, out = tmp_path / "data", tmp_path / "out"
    dump_rows(data / "inputs.jsonl", rows)
    manifest = dict(study="deterministic test", source_sha256="a" * 64,
                    inputs_sha256=hashlib.sha256((data / "inputs.jsonl").read_bytes()).hexdigest())
    (data / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    config = manifest["source_sha256"] + ":" + manifest["inputs_sha256"]
    variants, answers = [], []
    for row in rows:
        for method in ("original", "bhybrid_v2@0.5", "bm25@0.5"):
            key = row["uid"] + "|" + method
            variants.append(dict(key=key, uid=row["uid"], method=method, text=row["context"],
                                 original_tokens=10, actual_tokens=10 if method == "original" else 5,
                                 target_tokens=10 if method == "original" else 5,
                                 kept_ratio=1.0 if method == "original" else 0.5, budget_met=True, config=config))
            content = "B" if method == "bhybrid_v2@0.5" else "A"
            answers.append(dict(key=key, uid=row["uid"], method=method,
                                model=pilot.MODEL, content=content, config=config))
    dump_rows(out / "variants.jsonl", variants)
    dump_rows(out / "answers.jsonl", answers)
    return data, out, variants, answers


def test_prepare_preserves_paired_languages_and_dev_split(pilot, monkeypatch, tmp_path):
    bench = tmp_path / "bench"
    belebele = []
    for i in range(30):
        language = dict(passage=f"Passage {i}.", question=f"Question {i}?", options=["a", "b", "c", "d"])
        belebele.append(dict(id=f"bb-{i}", gold="B", english=language, hinglish=language))
    dump_rows(bench / "belebele" / "items.jsonl", belebele)
    for name, folder in (("squad", "longqa_squad"), ("meetingbank", "longqa_meetingbank"), ("hotpot", "hotpot")):
        dump_rows(bench / folder / "items.jsonl", [dict(id=f"{name}-{i}", context=f"Context {i}.",
                                                     question=f"Question {i}?", answer="answer") for i in range(4)])
    monkeypatch.setattr(pilot, "BENCH", bench)
    monkeypatch.setattr(pilot.subprocess, "check_output", lambda *args, **kwargs: "a" * 40)
    first, second = tmp_path / "first", tmp_path / "second"
    pilot.prepare(2, first)
    pilot.prepare(2, second, methods=("bbridge_doc", "bm25"))
    assert json.loads((second / "manifest.json").read_text())["methods"] == ["bbridge_doc", "bm25"]
    assert (first / "inputs.jsonl").read_bytes() == (second / "inputs.jsonl").read_bytes()
    rows = pilot.read_jsonl(first / "inputs.jsonl")
    assert len(rows) == 10
    paired = {}
    for row in rows:
        if row["dataset"] == "belebele":
            paired.setdefault(row["item_id"], set()).add(row["lang"])
            assert int(hashlib.sha256(f"hybrid-dev|{row['item_id']}".encode()).hexdigest(), 16) % 3 == 0
    assert len(paired) == 2
    assert all(languages == {"english", "hinglish"} for languages in paired.values())
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_sha256"] == hashlib.sha256((first / "source.zip").read_bytes()).hexdigest()
    assert manifest["inputs_sha256"] == hashlib.sha256((first / "inputs.jsonl").read_bytes()).hexdigest()
    with zipfile.ZipFile(first / "source.zip") as bundle:
        expected = {f"scripts/bench/{name}.py" for name in
                    ("common", "compressor_pilot", "baselines2", "hybrid", "belebele_extra", "belebele_cm", "hotpot", "grade")}
        expected |= {f"src/gateway/{name}.py" for name in ("__init__", "schemas", "tokenizer", "pricing", "modules/__init__")}
        expected |= {f"src/gateway/modules/m2_compressor/{name}.py" for name in
                     ("__init__", "budgeted", "document", "guarded", "llmlingua2", "safety_span")}
        assert set(bundle.namelist()) == expected
        extracted = tmp_path / "extracted"
        bundle.extractall(extracted)
    code = (
        "import sys; sys.path[:0] = sys.argv[1:]; "
        "import compressor_pilot, baselines2, hybrid, grade, hotpot; "
        "from gateway.modules.m2_compressor import budgeted; "
        "assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules"
    )
    smoke = subprocess.run([sys.executable, "-I", "-c", code, str(extracted / "scripts" / "bench"),
                            str(extracted / "src")], capture_output=True, text=True, timeout=30)
    assert smoke.returncode == 0, smoke.stderr
    with pytest.raises(ValueError, match="immutable"):
        pilot.prepare(2, first)


def test_mcq_prompt_preserves_question_and_every_option(pilot):
    row = mcq_input("first")
    context = "Shortened passage."
    system, prompt = pilot._prompt(row, context)
    assert "option letter" in system
    assert prompt.startswith("Passage: " + context)
    assert "Question: " + row["question"] in prompt
    for label, option in zip("ABCD", row["options"]):
        assert f"{label}) {option}" in prompt


def test_method_subset_is_validated(pilot):
    assert pilot.selected_methods(['bbridge_doc', 'bm25']) == ('bbridge_doc', 'bm25')
    for invalid in ([], ['bm25', 'bm25'], ['unknown']):
        with pytest.raises(ValueError):
            pilot.selected_methods(invalid)


def test_qa_prompt_preserves_entire_context_and_question(pilot):
    row = dict(task="qa", question="What is the full original question?")
    context = "Title:\nFirst context paragraph.\nSecond context paragraph."
    _, prompt = pilot._prompt(row, context)
    assert prompt == f"Context:\n{context}\n\nQuestion: {row['question']}"


def test_partial_grade_uses_method_matched_originals_and_complete_pairs(pilot, grading_files):
    data, out, _, answers = grading_files
    answers = [row for row in answers if row["key"] != "second|bm25@0.5"]
    dump_rows(out / "answers.jsonl", answers)
    report = pilot.grade(data, out)
    assert report["expected_answers"] == 6
    assert report["answered"] == 5
    assert not report["complete"]
    group = report["groups"]["belebele|english"]
    assert group["n_complete_paired"] == 1
    hybrid = group["methods"]["bhybrid_v2@0.5"]
    assert hybrid["n_paired_original"] == 2
    assert hybrid["score"] == hybrid["score_original_paired"] == 0.5
    assert hybrid["score_all_methods_paired"] == 0
    assert hybrid["mean_kept_ratio"] == 0.5
    bm25 = group["methods"]["bm25@0.5"]
    assert bm25["n_paired_original"] == 1
    assert bm25["score"] == bm25["score_original_paired"] == bm25["score_all_methods_paired"] == 1


def test_grade_reports_complete_only_for_full_expected_coverage(pilot, grading_files):
    data, out, _, _ = grading_files
    report = pilot.grade(data, out)
    assert report["complete"]
    assert report["groups"]["belebele|english"]["n_complete_paired"] == 2


def test_fair_comparison_excludes_budget_misses_and_extra_context(pilot, grading_files):
    data, out, variants, _ = grading_files
    for record in variants:
        if record["method"] == "bhybrid_v2@0.5" and record["uid"] == "first":
            record.update(actual_tokens=6, kept_ratio=0.6, budget_met=False)
    dump_rows(out / "variants.jsonl", variants)
    result = pilot.grade(data, out)["groups"]["belebele|english"]["methods"]["bhybrid_v2@0.5"]
    assert result["comparisons_at_no_more_context_tokens"]["bm25@0.5"]["n"] == 1
    for record in variants:
        if record["method"] == "bm25@0.5" and record["uid"] == "second":
            record.update(actual_tokens=4, kept_ratio=0.4)
    dump_rows(out / "variants.jsonl", variants)
    result = pilot.grade(data, out)["groups"]["belebele|english"]["methods"]["bhybrid_v2@0.5"]
    assert result["comparisons_at_no_more_context_tokens"]["bm25@0.5"]["n"] == 0


def test_grade_uses_frozen_manifest_methods_for_old_pilots(pilot, grading_files, monkeypatch):
    data, out, _, _ = grading_files
    manifest = json.loads((data / "manifest.json").read_text())
    manifest.update(methods=list(pilot.METHODS), rates=list(pilot.RATES))
    (data / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(pilot, "METHODS", (*pilot.METHODS, "new_experimental_method"))
    assert pilot.grade(data, out)["complete"]


def test_merge_disjoint_gpu_workers_keeps_full_paired_coverage(pilot, grading_files, tmp_path):
    data, out, variants, answers = grading_files
    workers = [tmp_path / "gpu_1", tmp_path / "gpu_2"]
    for index, uid in enumerate(("first", "second")):
        dump_rows(workers[index] / "variants.jsonl", [v for v in variants if v["uid"] == uid])
        dump_rows(workers[index] / "answers.jsonl", [v for v in answers if v["uid"] == uid])
        (workers[index] / "run_metadata.json").write_text(
            json.dumps(dict(gpu="fake", shard=f"{index + 1}/2", worker_inputs=1)), encoding="utf-8")
    report = pilot.merge_workers(data, out, workers)
    assert report["complete"] and report["answered"] == 6
    metadata = json.loads((out / "run_metadata.json").read_text())
    assert metadata["gpu_count"] == 2 and metadata["worker_inputs"] == 2
    assert metadata["worker_shards"] == ["1/2", "2/2"]


def test_merge_rejects_overlapping_worker_keys(pilot, grading_files, tmp_path):
    data, out, variants, answers = grading_files
    worker = tmp_path / "gpu_1"
    dump_rows(worker / "variants.jsonl", variants)
    dump_rows(worker / "answers.jsonl", answers)
    with pytest.raises(ValueError, match="Overlapping GPU shards"):
        pilot.merge_workers(data, out, [worker, worker])


def test_merge_partial_worker_cannot_report_complete(pilot, grading_files, tmp_path):
    data, out, variants, answers = grading_files
    worker = tmp_path / "gpu_1"
    dump_rows(worker / "variants.jsonl", [v for v in variants if v["uid"] == "first"])
    dump_rows(worker / "answers.jsonl", [v for v in answers if v["uid"] == "first"])
    report = pilot.merge_workers(data, out, [worker, tmp_path / "failed_worker"])
    assert not report["complete"] and report["answered"] == 3


def test_qa_grade_uses_cleaned_token_f1_with_matched_original(pilot, grading_files):
    data, out, variants, answers = grading_files
    rows = pilot.read_jsonl(data / "inputs.jsonl")
    rows[0].update(dataset="squad", task="qa", gold="New Delhi")
    dump_rows(data / "inputs.jsonl", rows)
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    manifest["inputs_sha256"] = hashlib.sha256((data / "inputs.jsonl").read_bytes()).hexdigest()
    (data / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    config = manifest["source_sha256"] + ":" + manifest["inputs_sha256"]
    for record in [*variants, *answers]:
        record["config"] = config
    for answer in answers:
        if answer["uid"] == "first":
            answer["content"] = "The answer is: Delhi." if answer["method"] == "bhybrid_v2@0.5" else "New Delhi"
    dump_rows(out / "variants.jsonl", variants)
    dump_rows(out / "answers.jsonl", answers)
    result = pilot.grade(data, out)["groups"]["squad|english"]["methods"]["bhybrid_v2@0.5"]
    assert result["score"] == pytest.approx(2 / 3)
    assert result["score_original_paired"] == 1
    assert result["n_paired_original"] == 1


def test_grade_rejects_unknown_key_in_place_of_missing_expected_answer(pilot, grading_files):
    data, out, _, answers = grading_files
    answers[-1] = dict(answers[-1], key="unknown|bm25@0.5", uid="unknown")
    dump_rows(out / "answers.jsonl", answers)
    with pytest.raises(ValueError):
        pilot.grade(data, out)


def test_grade_rejects_answer_without_matching_compression_variant(pilot, grading_files):
    data, out, variants, _ = grading_files
    dump_rows(out / "variants.jsonl", variants[:-1])
    with pytest.raises(ValueError):
        pilot.grade(data, out)


@pytest.mark.parametrize("field, value", [("config", "different"), ("model", "another-model")])
def test_grade_rejects_mixed_answer_configuration_or_models(pilot, grading_files, field, value):
    data, out, _, answers = grading_files
    answers[0][field] = value
    dump_rows(out / "answers.jsonl", answers)
    with pytest.raises(ValueError):
        pilot.grade(data, out)


def test_empty_partial_answers_produce_explicit_pending_metrics(pilot, grading_files):
    data, out, _, _ = grading_files
    dump_rows(out / "answers.jsonl", [])
    report = pilot.grade(data, out)
    assert report["answered"] == 0
    assert not report["complete"]
    for result in report["groups"]["belebele|english"]["methods"].values():
        assert result["n_paired_original"] == 0
        assert result["score"] is None
        assert result["mean_kept_ratio"] is None
