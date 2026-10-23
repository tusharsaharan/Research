"""Submit/check/download the private, bounded compressor pilot (no polling loop)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import BACKEND
from compressor_pilot import OUT, grade

SLUG = "tokenopt-compressor-pilot-v2"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("push", "status", "download"))
    ap.add_argument("--account-dir", type=Path, default=Path.home() / ".kaggle_team")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    env = dict(os.environ, KAGGLE_CONFIG_DIR=str(args.account_dir), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    user = (args.account_dir / "username").read_text().strip()
    env["KAGGLE_USERNAME"] = user
    env["KAGGLE_API_TOKEN"] = (args.account_dir / "access_token").read_text().strip()
    identity = f"{user}/{SLUG}"

    def kaggle(*parts, check=True):
        result = subprocess.run(["kaggle", *parts], env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180)
        output = result.stdout + result.stderr
        print(output[-1800:], flush=True)
        if check and result.returncode:
            raise RuntimeError(f"Kaggle command failed: {parts[0]} {parts[1]}")
        return result.returncode, output

    if args.cmd == "status":
        kaggle("kernels", "status", identity)
        return
    if args.cmd == "download":
        result = args.out / "kernel_output"
        kaggle("kernels", "output", identity, "-p", str(result))
        grade(args.out, result)
        return
    manifest = json.loads((args.out / "manifest.json").read_text(encoding="utf-8"))
    for filename, field in (("source.zip", "source_sha256"), ("inputs.jsonl", "inputs_sha256")):
        if hashlib.sha256((args.out / filename).read_bytes()).hexdigest() != manifest[field]:
            raise ValueError(f"Changed pilot artifact: {filename}")
    if (args.out / "launch.json").exists():
        raise ValueError("Pilot was already submitted; check/download it instead of launching duplicate compute")
    dataset = args.out / "dataset"
    kernel = args.out / "kernel"
    dataset.mkdir(parents=True, exist_ok=True)
    kernel.mkdir(parents=True, exist_ok=True)
    for filename in ("source.zip", "inputs.jsonl", "manifest.json"):
        shutil.copy2(args.out / filename, dataset / filename)
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "title": "TokenOpt compressor pilot v2", "id": identity, "licenses": [{"name": "other"}],
    }), encoding="utf-8")
    uploaded = args.out / "dataset_created.json"
    if uploaded.exists():
        previous = json.loads(uploaded.read_text(encoding="utf-8"))
        if previous != {"id": identity, "source": manifest["source_sha256"], "inputs": manifest["inputs_sha256"]}:
            raise ValueError("Existing uploaded dataset belongs to another pilot configuration/account")
    else:
        code, output = kaggle("datasets", "create", "-p", str(dataset), "--dir-mode", "zip", check=False)
        if "already" in output.lower() or "exists" in output.lower():
            raise RuntimeError("Dataset already exists; refusing to overwrite another pilot")
        if code or any(word in output.lower() for word in ("error", "forbidden", "denied")):
            raise RuntimeError("Private pilot dataset creation failed")
        uploaded.write_text(json.dumps({"id": identity, "source": manifest["source_sha256"],
                                         "inputs": manifest["inputs_sha256"]}), encoding="utf-8")
    _, status = kaggle("datasets", "status", identity)
    if "ready" not in status.lower():
        print("Dataset is processing. Rerun push after processing; no GPU has been launched.", flush=True)
        return
    shutil.copy2(BACKEND / "kaggle" / "compressor_pilot.py", kernel / "compressor_pilot.py")
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": identity, "title": "TokenOpt compressor pilot v2", "code_file": "compressor_pilot.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaP100",
        "dataset_sources": [identity], "competition_sources": [], "kernel_sources": [],
    }), encoding="utf-8")
    kaggle("kernels", "push", "-p", str(kernel))
    launch = dict(kernel=identity, url=f"https://www.kaggle.com/code/{identity}",
                  source_sha256=manifest["source_sha256"], inputs_sha256=manifest["inputs_sha256"],
                  budget_seconds=manifest["max_seconds"])
    (args.out / "launch.json").write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(json.dumps(launch), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
