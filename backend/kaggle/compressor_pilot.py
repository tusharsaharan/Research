"""Kaggle entry point; handles Kaggle's automatic archive extraction."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import zipfile

# Filled by the launcher from the already fingerprinted source.zip.
EXPECTED_SOURCE_FILES = {}


def locate_source(input_root, working):
    inputs = list(pathlib.Path(input_root).rglob("inputs.jsonl"))
    if len(inputs) != 1:
        raise RuntimeError("Attach exactly one compressor pilot dataset")
    data = inputs[0].parent
    manifest = json.loads((data / "manifest.json").read_text())
    archive = data / "source.zip"
    if archive.exists():
        if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise RuntimeError("Source bundle fingerprint mismatch")
        root = pathlib.Path(working) / "pilot_source"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root)
    else:
        # Kaggle expands source.zip into source/ when processing the dataset.
        root = data / "source"
        if not EXPECTED_SOURCE_FILES:
            raise RuntimeError("Missing per-file fingerprints for extracted source")
    for name, digest in EXPECTED_SOURCE_FILES.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Source file fingerprint mismatch: {name}")
    return data, root


def main():
    deadline = time.time() + 3300
    os.environ["COMPRESSOR_DEADLINE"] = str(deadline)
    data, root = locate_source("/kaggle/input", "/kaggle/working")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "llmlingua==0.2.2", "transformers==4.57.1",
                    "accelerate>=0.34,<2", "tiktoken", "pydantic>=2", "scipy", "sentencepiece"], check=True, timeout=300)
    os.environ["PYTHONPATH"] = str(root / "src")
    script = str(root / "scripts/bench/compressor_pilot.py")
    try:
        subprocess.run([sys.executable, "-u", script, "gpu", "--data", str(data),
                        "--out", "/kaggle/working"], check=True, timeout=max(1, deadline - time.time()))
    finally:
        subprocess.run([sys.executable, script, "grade", "--data", str(data), "--out", "/kaggle/working"],
                       check=False, timeout=30)


if __name__ == "__main__":
    main()
