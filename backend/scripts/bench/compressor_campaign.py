"""Bounded Kaggle campaign: advance once, persist state, never poll or retune.

Use scheduled invocations of advance. Only the prepared revisions may run;
each kernel can be submitted once and failed GPU runs are never auto-retried.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from common import BENCH

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = BENCH / "compressor_campaign_20261028"
TERMINAL = {"complete", "failed", "skipped"}


def save(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def init(out, revisions, hours=4):
    if (out / "campaign.json").exists():
        raise ValueError("Campaign already exists; use advance")
    if len(set(revisions)) != len(revisions) or not 0 < hours <= 4:
        raise ValueError("Distinct revisions and a maximum four-hour budget required")
    jobs = []
    for revision in revisions:
        data = BENCH / f"compressor_pilot_v{revision}"
        manifest = load(data / "manifest.json")
        for filename, key in (("source.zip", "source_sha256"), ("inputs.jsonl", "inputs_sha256")):
            if sha(data / filename) != manifest[key]:
                raise ValueError(f"Changed frozen artifact: {data / filename}")
        if (data / "launch.json").exists():
            raise ValueError("Campaign must not adopt a previously submitted run")
        jobs.append(dict(revision=revision, path=str(data), status="pending",
                         source_sha256=manifest["source_sha256"], inputs_sha256=manifest["inputs_sha256"],
                         manifest_sha256=sha(data / "manifest.json"),
                         model=manifest["answer_model"], max_seconds=manifest["max_seconds"],
                         expected_answers=manifest["units"] * (1 + len(manifest["methods"]) * len(manifest["rates"]))))
    total = sum(job["max_seconds"] for job in jobs)
    if total > hours * 3600:
        raise ValueError("Prepared run caps exceed the authorized budget")
    out.mkdir(parents=True, exist_ok=True)
    state = dict(created_at=time.time(), deadline=time.time() + hours * 3600,
                 total_runtime_cap_seconds=total, max_concurrent=2, jobs=jobs, finished=False)
    save(out / "campaign.json", state)
    return state


def command(args, log, env=None, timeout=650):
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", env=env, timeout=timeout)
        output = result.stdout + result.stderr
        with log.open("a", encoding="utf-8") as stream:
            stream.write(output + "\n")
        return result.returncode, output
    except subprocess.TimeoutExpired:
        with log.open("a", encoding="utf-8") as stream:
            stream.write("Command timed out; remote state must be reconciled before retry.\n")
        return 124, "Command timed out"


def account_env(account):
    return dict(os.environ, KAGGLE_CONFIG_DIR=str(account),
                KAGGLE_USERNAME=(account / "username").read_text().strip(),
                KAGGLE_API_TOKEN=(account / "access_token").read_text().strip(),
                PYTHONUTF8="1", PYTHONIOENCODING="utf-8")


def verify_download(data, remote):
    """Exact comparison before recovering an upload with an ambiguous response."""
    for name in ("manifest.json", "inputs.jsonl"):
        if (remote / name).read_bytes() != (data / name).read_bytes():
            raise ValueError("Remote pilot data differs from frozen input")
    with zipfile.ZipFile(data / "source.zip") as archive:
        for name in archive.namelist():
            if (remote / "source" / name).read_bytes() != archive.read(name):
                raise ValueError("Remote pilot source differs from frozen source")


def recover_upload(data, env):
    manifest = load(data / "manifest.json")
    identity = env["KAGGLE_USERNAME"] + "/tokenopt-compressor-pilot-v" + data.name.rsplit("v", 1)[1]
    remote = data / "remote_verified"
    remote.mkdir(exist_ok=True)
    code, _ = command(["kaggle", "datasets", "download", "-d", identity, "-p", str(remote), "--unzip", "-q", "--force"],
                      data / "campaign-recovery.log", env=env, timeout=120)
    if code:
        return False
    verify_download(data, remote)
    save(data / "dataset_created.json", dict(id=identity, source=manifest["source_sha256"], inputs=manifest["inputs_sha256"]))
    return True


def kernel_status(output):
    for name, state in (("COMPLETE", "done"), ("RUNNING", "running"), ("QUEUED", "queued"),
                        ("ERROR", "failed"), ("CANCELLED", "failed"), ("CANCELED", "failed")):
        if f"KernelWorkerStatus.{name}" in output:
            return state
    return "unknown"


def owned_kernels(env, out):
    code, output = command(["kaggle", "kernels", "list", "--mine", "--csv", "--search", "tokenopt-compressor-gpu-pilot"],
                           out / "owned-kernels.log", env, 60)
    if code:
        raise RuntimeError("Cannot verify owned kernels; refusing uncertain submission")
    if "Not found" in output:
        return set()
    lines = output.splitlines()
    header = next((i for i, line in enumerate(lines) if line.startswith("ref,")), None)
    if header is None:
        raise RuntimeError("Unrecognized owned-kernel listing")
    return {row["ref"] for row in csv.DictReader(io.StringIO("\n".join(lines[header:]))) if row.get("ref")}


def summarize(out, state):
    reports = []
    for job in state["jobs"]:
        data = Path(job["path"])
        report = dict(job)
        review = data / "kernel_output/review.json"
        if review.exists() and job["status"] == "complete":
            report["review"] = load(review)
        reports.append(report)
    save(out / "report.json", dict(finished=state["finished"], jobs=reports,
         note="Development evidence. Compare methods within each answer-model/tokenizer and dataset; do not pool raw scores."))


def advance(out, account):
    lock = out / "advance.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("Another campaign advance is active; no action.")
        return
    try:
        os.close(fd)
        state = load(out / "campaign.json")
        env = account_env(account)
        user = env["KAGGLE_USERNAME"]

        def persist():
            save(out / "campaign.json", state)

        def launch_command(job, action):
            data = Path(job["path"])
            return command([sys.executable, str(HERE / "kaggle_compressor.py"), action,
                            "--revision", str(job["revision"]), "--account-dir", str(account),
                            "--command-timeout", "300"], data / f"campaign-{action}.log")

        for job in state["jobs"]:
            data = Path(job["path"])
            if sha(data / "manifest.json") != job["manifest_sha256"]:
                raise ValueError("Campaign manifest changed after freeze")
            if job["status"] in TERMINAL:
                continue
            if (data / "launch.json").exists():
                code, output = launch_command(job, "status")
                status = kernel_status(output) if code == 0 else "unknown"
                job["status"] = status
                persist()
                if status in {"done", "failed"}:
                    code, _ = launch_command(job, "download")
                    if code == 0 and status == "done":
                        report = data / "kernel_output/report.json"
                        if report.exists() and load(report)["complete"]:
                            code, _ = command([sys.executable, str(HERE / "compressor_pilot_review.py"),
                                               "--data", str(data)], data / "campaign-review.log", timeout=120)
                            if code == 0:
                                job["status"] = "complete"
                    if status == "failed":
                        job["status"] = "failed"  # partial files retained, no GPU retry
                    persist()
        active = sum(job["status"] in {"queued", "running", "unknown", "done"} for job in state["jobs"])
        pending = [job for job in state["jobs"] if job["status"] in {"pending", "uploading"}]
        owned = owned_kernels(env, out) if pending and active < state["max_concurrent"] else set()
        for job in pending:
            if active >= state["max_concurrent"]:
                break
            if time.time() + job["max_seconds"] + 300 > state["deadline"]:
                job["status"] = "skipped"
                job["reason"] = "Insufficient time remaining inside campaign window"
                persist()
                continue
            identity = f"{user}/tokenopt-compressor-gpu-pilot-v{job['revision']}"
            if identity in owned:
                job["status"] = "unknown"
                job["reason"] = "Remote kernel exists without local launch marker; manual reconciliation required"
                active += 1
                persist()
                continue
            data = Path(job["path"])
            job["status"] = "uploading"
            persist()
            code, _ = launch_command(job, "push")
            if code and not (data / "launch.json").exists() and not (data / "dataset_created.json").exists():
                # A failed dataset response can still mean successful creation.
                # Verify every remote byte before retrying the kernel submission.
                if recover_upload(data, env):
                    code, _ = launch_command(job, "push")
            if (data / "launch.json").exists():
                job["status"] = "queued"
                job["submitted_at"] = time.time()
                active += 1
            elif code:
                job["status"] = "attention"
                job["reason"] = "Upload/submission failed; inspect campaign-push.log before taking action"
            else:
                active += 1  # dataset still processing; resume at next invocation
            persist()
        state["finished"] = all(job["status"] in TERMINAL | {"attention"} for job in state["jobs"])
        state["checked_at"] = time.time()
        persist()
        summarize(out, state)
        print(json.dumps(dict(finished=state["finished"], deadline=state["deadline"],
                              jobs=[dict(revision=j["revision"], status=j["status"]) for j in state["jobs"]])))
    finally:
        lock.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["init", "advance"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--account-dir", type=Path, default=Path.home() / ".kaggle_team")
    ap.add_argument("--revisions", nargs="+", type=int, default=[13, 14, 15, 16])
    args = ap.parse_args()
    if args.action == "init":
        print(json.dumps(init(args.out, args.revisions)))
    else:
        advance(args.out, args.account_dir)
