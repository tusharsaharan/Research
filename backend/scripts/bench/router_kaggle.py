"""Prepare/launch a private GPU validation of the train-only router on Kaggle.

Uploads only selected scorer_train rows, source code and CPU reference embeddings.
Does not upload API credentials, raw provider answers, pilot or certification data.
Run prepare, then push; download is a separate one-shot action after completion.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from common import BACKEND, BENCH
from kaggle_run import sh

ROOT = BENCH / "router_gpu"
SLUG = "tokenopt-router-gpu-validation"
DATASET_SLUG = "tokenopt-router-validation"
NAME = "grades_pair2_paired_gsm8k"


def bind_token():
    # The SDK ignores KAGGLE_CONFIG_DIR for access_token files and otherwise
    # reads ~/.kaggle/access_token. Explicitly bind the chosen private token.
    if os.environ.get("KAGGLE_CONFIG_DIR"):
        token = Path(os.environ["KAGGLE_CONFIG_DIR"]) / "access_token"
        if token.exists():
            os.environ["KAGGLE_API_TOKEN"] = str(token)


def username():
    # Resolve the token's owner through Kaggle; a stale local username may belong
    # to another teammate. Never guess an account or change their global config.
    bind_token()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    user = api.config_values[api.CONFIG_NAME_USER]
    expected = os.environ.get("ROUTER_KAGGLE_USER")
    if expected and expected != user:
        raise SystemExit(f"Token belongs to {user}, expected {expected}; no upload or run performed")
    return user

def stage_inputs(input_root, root):
    """Kaggle may mount uploaded ZIPs as already extracted directories."""
    inputs = list(Path(input_root).rglob("router_input.json"))
    if len(inputs) != 1:
        raise ValueError(f"Expected one router input, found {len(inputs)}")
    source = inputs[0].parent
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    archives = list(source.rglob("router_source.zip"))
    if archives:
        with zipfile.ZipFile(archives[0]) as archive:
            archive.extractall(root)
    else:
        scripts = list(source.rglob("backend/scripts/bench/router_train.py"))
        if len(scripts) != 1:
            raise ValueError(f"Expected router source archive or extracted tree; found {len(scripts)} trees")
        shutil.copytree(scripts[0].parents[2], root / "backend", dirs_exist_ok=True)
    return source


GPU_CODE = r'''
import json, os, pathlib, shutil, subprocess, sys, time, zipfile
from pathlib import Path
# STAGE_INPUTS
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'sentence-transformers', 'scikit-learn', 'pydantic-settings'], check=True)
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
assert torch.cuda.is_available(), 'GPU required for this validation'
root = pathlib.Path('/kaggle/working/router_validation')
source = stage_inputs('/kaggle/input', root)
bench = root / 'backend/data/bench'
bench.mkdir(parents=True, exist_ok=True)
data = json.loads((source / 'router_input.json').read_text())
assert all(r['split'] == 'scorer_train' for r in data['rows'])
texts = [r['text'] for r in data['rows']]
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cuda')
torch.cuda.synchronize()
start = time.perf_counter()
vecs = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
torch.cuda.synchronize()
elapsed = time.perf_counter() - start
cache = bench / 'gpu_embeddings.npz'
np.savez(cache, keys=np.array(texts), vecs=vecs)
with np.load(source / 'reference_emb.npz') as z:
    assert list(z['keys']) == texts
    ref = z['vecs']
cos = (ref * vecs).sum(axis=1) / (np.linalg.norm(ref, axis=1) * np.linalg.norm(vecs, axis=1))
parity = {'device': torch.cuda.get_device_name(0), 'n_rows': len(texts),
          'embedding_seconds': elapsed, 'min_cpu_gpu_cosine': float(cos.min()),
          'max_embedding_abs_diff': float(np.abs(ref - vecs).max()),
          'torch': torch.__version__, 'encoder': 'paraphrase-multilingual-MiniLM-L12-v2'}
assert parity['min_cpu_gpu_cosine'] > 0.999, parity
out = pathlib.Path('/kaggle/working/results')
out.mkdir(exist_ok=True)
env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
script = root / 'backend/scripts/bench/router_train.py'
base = [sys.executable, str(script), '--input', str(source / 'router_input.json'), '--embedding-cache', str(cache), '--output-dir', str(out)]
workers = min(os.cpu_count() or 1, 4)
jobs, logs = [], []
for i in range(1, workers + 1):
    log = (out / f'worker-{i}.log').open('w')
    logs.append(log)
    jobs.append(subprocess.Popen(base + ['--shard', f'{i}/{workers}'], env=env, stdout=log, stderr=subprocess.STDOUT))
codes = [p.wait() for p in jobs]
for log in logs: log.close()
assert all(c == 0 for c in codes), codes
subprocess.run(base + ['--merge'], env=env, check=True)
(out / 'gpu_validation.json').write_text(json.dumps(parity, indent=2))
print(json.dumps(parity, indent=2))
'''


def prepare():
    src = BENCH / "router_training"
    ds = ROOT / "dataset"
    kernel = ROOT / "kernel"
    ds.mkdir(parents=True, exist_ok=True)
    kernel.mkdir(parents=True, exist_ok=True)
    data = json.loads((src / f"{NAME}_input.json").read_text(encoding="utf-8"))
    if not data["rows"] or any(r["split"] != "scorer_train" for r in data["rows"]):
        raise ValueError("only nonempty scorer_train input may be uploaded")
    shutil.copy(src / f"{NAME}_input.json", ds / "router_input.json")
    shutil.copy(src / f"{NAME}_emb.npz", ds / "reference_emb.npz")
    with zipfile.ZipFile(ds / "router_source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((BACKEND / "src" / "gateway").rglob("*.py")):
            z.write(p, p.relative_to(BACKEND.parent).as_posix())
        for f in ("common.py", "router_v2.py", "router_train.py"):
            p = BACKEND / "scripts" / "bench" / f
            z.write(p, p.relative_to(BACKEND.parent).as_posix())
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": {
        "display_name": "Python 3", "language": "python", "name": "python3"}}, "cells": [{
        "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
        "source": GPU_CODE.replace("# STAGE_INPUTS", inspect.getsource(stage_inputs)).splitlines(True)}]}
    (kernel / "router_validation.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    print("prepared private GPU validation:", len(data["rows"]), "training rows")


def push():
    user = username()
    ds, kernel = ROOT / "dataset", ROOT / "kernel"
    (ds / "dataset-metadata.json").write_text(json.dumps({"title": "TokenOpt router training validation",
        "id": f"{user}/{DATASET_SLUG}", "licenses": [{"name": "other"}]}))
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    quota = api.quota_view().gpu_quota
    if quota is not None and quota.time_used >= quota.total_time_allowed:
        raise SystemExit(f"No GPU quota remaining for {user}; validation package saved locally")
    # Kaggle's CLI reports creation errors via return code; never mask auth/quota errors.
    try:
        result = sh("datasets", "create", "-p", str(ds), "--dir-mode", "zip")
    except SystemExit as e:
        if "already" not in str(e).lower() and "exists" not in str(e).lower():
            raise
        result = str(e)
    if "already" in result.lower() or "exists" in result.lower():
        print(sh("datasets", "version", "-p", str(ds), "-m", "Router GPU validation", "--dir-mode", "zip")[-600:])
    elif "error" in result.lower() or "forbidden" in result.lower():
        raise SystemExit(result[-1000:])
    else:
        print(result[-600:])
    (kernel / "kernel-metadata.json").write_text(json.dumps({"id": f"{user}/{SLUG}",
        "title": "TokenOpt router GPU validation", "code_file": "router_validation.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": True,
        "enable_internet": True, "machine_shape": "NvidiaTeslaT4", "dataset_sources": [f"{user}/{DATASET_SLUG}"],
        "competition_sources": [], "kernel_sources": []}))
    print(sh("kernels", "push", "-p", str(kernel)))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("prepare", "push", "status", "download", "account", "retry"))
    args = ap.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "push":
        push()
    elif args.action == "retry":
        user = username()
        status = sh("kernels", "status", f"{user}/{SLUG}")
        if not any(word in status for word in ("KernelWorkerStatus.ERROR", "KernelWorkerStatus.CANCEL")):
            raise SystemExit("Only a failed/cancelled validation may be retried")
        meta_path = ROOT / "kernel" / "kernel-metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update(id=f"{user}/{SLUG}", title="TokenOpt router GPU validation")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        print(sh("kernels", "push", "-p", str(ROOT / "kernel")))
    elif args.action == "account":
        print("Authenticated Kaggle account:", username())
        print(sh("quota"))
    elif args.action == "status":
        print(sh("kernels", "status", f"{username()}/{SLUG}"))
    else:
        print(sh("kernels", "output", f"{username()}/{SLUG}", "-p", str(ROOT / "output"))[-1000:])


if __name__ == "__main__":
    main()
