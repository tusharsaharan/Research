"""Kaggle entry point; handles Kaggle's automatic archive extraction."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

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
    destination = pathlib.Path(working) / "pilot_source"
    if root != destination:
        shutil.copytree(root, destination, dirs_exist_ok=True)
    return data, destination


def run_gpu_workers(data, root, working, workers, deadline):
    """One independent item shard per GPU; keep finalization time in reserve."""
    script = str(root / "scripts/bench/compressor_pilot.py")
    working = pathlib.Path(working)
    outputs = [working / f"gpu_{i + 1}" for i in range(workers)]

    def run(index):
        outputs[index].mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(index),
                   OMP_NUM_THREADS=str(max(1, (os.cpu_count() or 1) // workers)),
                   MKL_NUM_THREADS=str(max(1, (os.cpu_count() or 1) // workers)), TOKENIZERS_PARALLELISM="false")
        with (working / f"worker_{index + 1}.log").open("w") as log:
            result = subprocess.run([sys.executable, "-u", script, "gpu", "--data", str(data),
                                     "--out", str(outputs[index]), "--shard", f"{index + 1}/{workers}"],
                                    env=env, stdout=log, stderr=subprocess.STDOUT,
                                    check=False, timeout=max(1, deadline - time.time()))
        print(f"GPU worker {index + 1}/{workers} exited {result.returncode}", flush=True)
        return result.returncode

    codes = []
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            codes = list(pool.map(run, range(workers)))
    finally:
        subprocess.run([sys.executable, script, "merge", "--data", str(data), "--out", str(working),
                        "--workers", *map(str, outputs)], check=True, timeout=45)
    report = json.loads((working / "report.json").read_text())
    if any(codes) or not report["complete"]:
        raise RuntimeError("Incomplete GPU pilot; partial outputs and coverage report retained")


def main():
    deadline = time.time() + 3240  # server cap is 3300s; reserve a minute to merge
    os.environ["COMPRESSOR_DEADLINE"] = str(deadline)
    data, root = locate_source("/kaggle/input", "/kaggle/working")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "llmlingua==0.2.2", "transformers==4.57.1",
                    "accelerate>=0.34,<2", "tiktoken", "pydantic>=2", "scipy", "sentencepiece"], check=True, timeout=300)
    os.environ["PYTHONPATH"] = str(root / "src")
    import torch
    workers = torch.cuda.device_count()
    if not workers:
        raise RuntimeError("GPU required")
    try:
        import psutil
        workers = min(workers, max(1, psutil.virtual_memory().available // (4 * 1024**3)))
    except ImportError:
        pass
    print(f"Available GPUs: {torch.cuda.device_count()}, parallel workers: {workers}", flush=True)
    run_gpu_workers(data, root, "/kaggle/working", workers, deadline)


if __name__ == "__main__":
    main()
