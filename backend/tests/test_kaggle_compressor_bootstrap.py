"""Kaggle dataset layout/fingerprint checks without installs or model loading."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest


FILES = {
    "src/gateway/__init__.py": b'"""Gateway."""\n',
    "src/gateway/modules/m2_compressor/budgeted.py": b"VERSION = 2\n",
    "scripts/bench/compressor_pilot.py": b"def gpu(): pass\n",
}


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
