"""Submit/check/download the private, bounded compressor pilot (no polling loop)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from common import BACKEND
from compressor_pilot import OUT, grade


def dataset_creation_succeeded(code, output, identity):
    """Recovered upload errors can precede the CLI's successful creation receipt."""
    receipt = f"Dataset is being created. Please check progress at https://www.kaggle.com/datasets/{identity}"
    return code == 0 and receipt in output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("push", "status", "download", "quota", "logs", "files", "watch"))
    ap.add_argument("--account-dir", type=Path, default=Path.home() / ".kaggle_team")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--revision", type=int, default=2)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--command-timeout", type=int, default=180,
                    help="Bound for each Kaggle CLI call, including resumable dataset uploads")
    args = ap.parse_args()
    if not 30 <= args.command_timeout <= 900:
        raise ValueError("command-timeout must be between 30 and 900 seconds")
    if args.out is None:
        args.out = OUT.parent / f"compressor_pilot_v{args.revision}"
    env = dict(os.environ, KAGGLE_CONFIG_DIR=str(args.account_dir), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    user = (args.account_dir / "username").read_text().strip()
    env["KAGGLE_USERNAME"] = user
    env["KAGGLE_API_TOKEN"] = (args.account_dir / "access_token").read_text().strip()
    if args.revision < 2:
        raise ValueError("revision must be at least 2")
    identity = f"{user}/tokenopt-compressor-gpu-pilot-v{args.revision}"
    dataset_identity = f"{user}/tokenopt-compressor-pilot-v{args.revision}"

    def kaggle(*parts, check=True):
        command = ([sys.executable, str(Path(__file__).with_name('kaggle_upload_bounded.py')), *parts]
                   if parts[:2] == ('datasets', 'create') else ["kaggle", *parts])
        result = subprocess.run(command, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=args.command_timeout)
        output = result.stdout + result.stderr
        print(output[-1800:], flush=True)
        if check and result.returncode:
            raise RuntimeError(f"Kaggle command failed: {parts[0]} {parts[1]}")
        return result.returncode, output

    if args.cmd == "quota":
        kaggle("quota")
        return
    if args.cmd == "status":
        kaggle("kernels", "status", identity)
        return
    if args.cmd == "watch":
        os.environ.update(env)
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        with (args.out / "live.log").open("a", encoding="utf-8") as log:
            for event in api.kernels_logs_stream(identity):
                data = event.get("data", "")
                log.write(data)
                log.flush()
                if any(word in data for word in ("Traceback", "Error", "compression finished", "answers ", "report")):
                    print(data[-1800:], flush=True)
        return
    if args.cmd == "files":
        kaggle("datasets", "files", dataset_identity)
        return
    if args.cmd == "logs":
        _, output = kaggle("kernels", "logs", identity)
        (args.out / "server.log").write_text(output, encoding="utf-8")
        return
    if args.cmd == "download":
        result = args.out / "kernel_output"
        kaggle("kernels", "output", identity, "-p", str(result), "-q", "--file-pattern",
               r"^(?!pilot_source/).*(?:\.jsonl|\.json|\.log)$")
        grade(args.out, result)
        return
    manifest = json.loads((args.out / "manifest.json").read_text(encoding="utf-8"))
    for filename, field in (("source.zip", "source_sha256"), ("inputs.jsonl", "inputs_sha256")):
        if hashlib.sha256((args.out / filename).read_bytes()).hexdigest() != manifest[field]:
            raise ValueError(f"Changed pilot artifact: {filename}")
    if (args.out / "launch.json").exists():
        if not args.retry_failed:
            raise ValueError("Pilot already submitted; use status/download or --retry-failed")
        _, status = kaggle("kernels", "status", identity)
        if not any(word in status.lower() for word in ("error", "cancel")):
            raise ValueError("Only a failed/cancelled pilot can be retried; refusing duplicate compute")
        if (args.out / "server.log").exists():
            shutil.copy2(args.out / "server.log", args.out / "server.failed.log")
    dataset = args.out / "dataset"
    kernel = args.out / "kernel"
    dataset.mkdir(parents=True, exist_ok=True)
    kernel.mkdir(parents=True, exist_ok=True)
    for filename in ("source.zip", "inputs.jsonl", "manifest.json"):
        shutil.copy2(args.out / filename, dataset / filename)
    (dataset / "dataset-metadata.json").write_text(json.dumps({
        "title": f"TokenOpt compressor pilot v{args.revision}", "id": dataset_identity, "licenses": [{"name": "other"}],
    }), encoding="utf-8")
    uploaded = args.out / "dataset_created.json"
    if uploaded.exists():
        previous = json.loads(uploaded.read_text(encoding="utf-8"))
        if previous != {"id": dataset_identity, "source": manifest["source_sha256"], "inputs": manifest["inputs_sha256"]}:
            raise ValueError("Existing uploaded dataset belongs to another pilot configuration/account")
    else:
        code, output = kaggle("datasets", "create", "-p", str(dataset), "--dir-mode", "zip", check=False)
        if not dataset_creation_succeeded(code, output, dataset_identity):
            if "already" in output.lower() or "exists" in output.lower():
                raise RuntimeError("Dataset already exists; refusing to overwrite another pilot")
            raise RuntimeError("Private pilot dataset creation failed")
        uploaded.write_text(json.dumps({"id": dataset_identity, "source": manifest["source_sha256"],
                                         "inputs": manifest["inputs_sha256"]}), encoding="utf-8")
    _, status = kaggle("datasets", "status", dataset_identity)
    if "ready" not in status.lower():
        print("Dataset is processing. Rerun push after processing; no GPU has been launched.", flush=True)
        return
    bootstrap = (BACKEND / "kaggle" / "compressor_pilot.py").read_text(encoding="utf-8-sig")
    with zipfile.ZipFile(args.out / "source.zip") as archive:
        fingerprints = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    bootstrap = bootstrap.replace("EXPECTED_SOURCE_FILES = {}", "EXPECTED_SOURCE_FILES = " + repr(fingerprints))
    (kernel / "compressor_pilot.py").write_text(bootstrap, encoding="utf-8")
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": identity, "title": f"TokenOpt compressor GPU pilot v{args.revision}", "code_file": "compressor_pilot.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [dataset_identity], "competition_sources": [], "kernel_sources": [],
    }), encoding="utf-8")
    # CLI hides the response body on SaveKernel conflicts. The SDK preserves
    # the useful quota/accelerator validation error without printing tokens.
    os.environ.update(env)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    try:
        response = api.kernels_push(str(kernel), timeout=str(manifest["max_seconds"]))
        print(response, flush=True)
        if response.error:
            raise RuntimeError(f"Kaggle rejected submission: {response.error}")
    except Exception as exc:
        response = getattr(exc, "response", None)
        if response is not None:
            print(response.text[:1800], flush=True)
        raise
    launch = dict(kernel=identity, url=f"https://www.kaggle.com/code/{identity}",
                  source_sha256=manifest["source_sha256"], inputs_sha256=manifest["inputs_sha256"],
                  budget_seconds=manifest["max_seconds"], bootstrap_sha256=hashlib.sha256(bootstrap.encode()).hexdigest())
    (args.out / "launch.json").write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(json.dumps(launch), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
