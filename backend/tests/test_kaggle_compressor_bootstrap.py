"""Kaggle dataset layout/fingerprint checks without installs or model loading."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import zipfile
import time
from types import SimpleNamespace
from pathlib import Path

import pytest


FILES = {
    "src/gateway/__init__.py": b'"""Gateway."""\n',
    "src/gateway/modules/m2_compressor/budgeted.py": b"VERSION = 2\n",
    "scripts/bench/compressor_pilot.py": b"def gpu(): pass\n",
}


@pytest.mark.parametrize("failed", [False, True])
def test_workers_use_distinct_gpus_and_merge_before_reporting(bootstrap, monkeypatch, tmp_path, failed):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if "merge" in command:
            (tmp_path / "report.json").write_text(json.dumps({"complete": not failed}))
            return SimpleNamespace(returncode=0)
        index = int(kwargs["env"]["CUDA_VISIBLE_DEVICES"])
        assert command[command.index("--shard") + 1] == f"{index + 1}/2"
        assert command[command.index("--out") + 1].endswith(f"gpu_{index + 1}")
        return SimpleNamespace(returncode=int(failed and index == 0))

    monkeypatch.setattr(bootstrap.subprocess, "run", run)
    if failed:
        with pytest.raises(RuntimeError, match="Incomplete GPU pilot"):
            bootstrap.run_gpu_workers(tmp_path, tmp_path, tmp_path, 2, time.time() + 60)
    else:
        bootstrap.run_gpu_workers(tmp_path, tmp_path, tmp_path, 2, time.time() + 60)
    workers = [(command, kwargs) for command, kwargs in calls if "gpu" in command]
    assert {kwargs["env"]["CUDA_VISIBLE_DEVICES"] for _, kwargs in workers} == {"0", "1"}
    assert "merge" in calls[-1][0]
    assert calls[-1][1]["check"] is True


def test_worker_timeout_still_merges_partial_outputs(bootstrap, monkeypatch, tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "merge" in command:
            return SimpleNamespace(returncode=0)
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(bootstrap.subprocess, "run", run)
    with pytest.raises(subprocess.TimeoutExpired):
        bootstrap.run_gpu_workers(tmp_path, tmp_path, tmp_path, 1, time.time() + 60)
    assert "merge" in calls[-1]


@pytest.fixture
def bootstrap(monkeypatch):
    def reject_subprocess(*args, **kwargs):
        pytest.fail("Importing or locating source must not install dependencies or run jobs")

    monkeypatch.setattr(subprocess, "run", reject_subprocess)
    path = Path(__file__).resolve().parents[1] / "kaggle" / "compressor_pilot.py"
    spec = importlib.util.spec_from_file_location("test_kaggle_compressor_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.EXPECTED_SOURCE_FILES = {name: hashlib.sha256(content).hexdigest() for name, content in FILES.items()}
    return module


@pytest.fixture
def dataset(tmp_path):
    inputs = tmp_path / "input"
    data = inputs / "private-pilot"
    data.mkdir(parents=True)
    (data / "inputs.jsonl").write_text('{"uid":"example"}\n', encoding="utf-8")
    working = tmp_path / "working"
    return inputs, data, working


def write_manifest(data, archive_digest="a" * 64):
    (data / "manifest.json").write_text(json.dumps({"source_sha256": archive_digest}), encoding="utf-8")


def create_archive(data):
    archive = data / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, content in FILES.items():
            bundle.writestr(name, content)
    write_manifest(data, hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive


def create_extracted_source(data):
    root = data / "source"
    for name, content in FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    write_manifest(data)
    return root


def test_raw_archive_is_verified_and_extracted_to_working(bootstrap, dataset):
    inputs, data, working = dataset
    create_archive(data)
    actual_data, root = bootstrap.locate_source(inputs, working)
    assert actual_data == data
    assert root == working / "pilot_source"
    assert all((root / name).read_bytes() == content for name, content in FILES.items())


def test_raw_archive_hash_mismatch_rejected_before_extraction(bootstrap, dataset):
    inputs, data, working = dataset
    archive = create_archive(data)
    archive.write_bytes(archive.read_bytes() + b"changed")
    with pytest.raises(RuntimeError, match="Source bundle fingerprint mismatch"):
        bootstrap.locate_source(inputs, working)
    assert not (working / "pilot_source").exists()


def test_raw_archive_also_checks_injected_per_file_hashes(bootstrap, dataset):
    inputs, data, working = dataset
    create_archive(data)
    bootstrap.EXPECTED_SOURCE_FILES["scripts/bench/compressor_pilot.py"] = "f" * 64
    with pytest.raises(RuntimeError, match="Source file fingerprint mismatch"):
        bootstrap.locate_source(inputs, working)


def test_autoextracted_source_is_copied_to_writable_working_root(bootstrap, dataset):
    inputs, data, working = dataset
    dataset_root = create_extracted_source(data)
    actual_data, root = bootstrap.locate_source(inputs, working)
    assert actual_data == data
    assert root == working / "pilot_source"
    assert root.resolve().is_relative_to(working.resolve())
    assert root.resolve() != dataset_root.resolve()
    assert all((root / name).read_bytes() == content for name, content in FILES.items())
    # common.py initializes backend/data/bench at import time. The code root
    # must support that write even when /kaggle/input is mounted read-only.
    runtime_data = root / "data" / "bench"
    runtime_data.mkdir(parents=True)
    (runtime_data / "runtime.json").write_text("{}", encoding="utf-8")
    assert not (dataset_root / "data").exists()
    copied_script = root / "scripts" / "bench" / "compressor_pilot.py"
    copied_script.write_bytes(b"runtime change\n")
    assert (dataset_root / "scripts" / "bench" / "compressor_pilot.py").read_bytes() == FILES[
        "scripts/bench/compressor_pilot.py"
    ]


@pytest.mark.parametrize("name", list(FILES))
def test_modified_autoextracted_source_file_is_rejected(bootstrap, dataset, name):
    inputs, data, working = dataset
    root = create_extracted_source(data)
    (root / name).write_bytes(b"modified source\n")
    with pytest.raises(RuntimeError, match="Source file fingerprint mismatch"):
        bootstrap.locate_source(inputs, working)
    assert not working.exists()


def test_autoextracted_source_requires_injected_fingerprints(bootstrap, dataset):
    inputs, data, working = dataset
    create_extracted_source(data)
    bootstrap.EXPECTED_SOURCE_FILES = {}
    with pytest.raises(RuntimeError, match="Missing per-file fingerprints"):
        bootstrap.locate_source(inputs, working)


def test_no_pilot_inputs_are_rejected(bootstrap, tmp_path):
    with pytest.raises(RuntimeError, match="exactly one compressor pilot dataset"):
        bootstrap.locate_source(tmp_path / "empty-input", tmp_path / "working")


def test_multiple_pilot_datasets_are_rejected(bootstrap, dataset):
    inputs, data, working = dataset
    second = inputs / "another-pilot"
    second.mkdir()
    (second / "inputs.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="exactly one compressor pilot dataset"):
        bootstrap.locate_source(inputs, working)
