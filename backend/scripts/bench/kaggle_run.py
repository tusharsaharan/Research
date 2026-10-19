"""End-to-end Kaggle GPU run, no manual steps after the API token exists.

1. export prompts (kaggle_prepare.py)          4. wait for the run to finish (polls every 10 min)
2. create/update a PRIVATE Kaggle dataset      5. download answers.jsonl
3. push + run the notebook on a GPU            6. grade + analyse (kaggle_import.py)

Needs C:\\Users\\<you>\\.kaggle\\kaggle.json (Kaggle -> Settings -> API -> Create New Token).
Resumable: re-running after a Kaggle timeout re-pushes the notebook, which skips
prompts already answered in the previous run's output (downloaded first).

    python backend/scripts/bench/kaggle_run.py
    python backend/scripts/bench/kaggle_run.py --skip-prepare --poll-min 10
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import BACKEND, BENCH

TAG = os.environ.get("KAGGLE_TAG", "")  # e.g. "-7b": separate prompts/answers folder, dataset and notebook
K = BENCH / f"kaggle{TAG}"
NB = BACKEND / "kaggle" / f"local_answers_t4{TAG}.ipynb"
DS_SLUG = f"tokenopt-hinglish-prompts{TAG}"
KERNEL_SLUG = f"tokenopt-local-answers{TAG}"


def sh(*args: str, check: bool = True) -> str:
    import os

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}  # Windows charmap crash on download
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if check and r.returncode:
        raise SystemExit(f"kaggle {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def username() -> str:
    """Kaggle username: kaggle.json (legacy token), KAGGLE_USERNAME, or ~/.kaggle/username."""
    import os

    kdir = Path(os.environ.get("KAGGLE_CONFIG_DIR") or Path.home() / ".kaggle")
    if (kdir / "kaggle.json").exists():
        return json.loads((kdir / "kaggle.json").read_text())["username"]
    if os.environ.get("KAGGLE_USERNAME"):
        return os.environ["KAGGLE_USERNAME"]
    if (kdir / "username").exists():
        return (kdir / "username").read_text().strip()
    raise SystemExit("put your Kaggle username in ~/.kaggle/username (one line)")


def token_ready() -> bool:
    import os

    kdir = Path(os.environ.get("KAGGLE_CONFIG_DIR") or Path.home() / ".kaggle")
    return (kdir / "kaggle.json").exists() or (kdir / "access_token").exists() or bool(os.environ.get("KAGGLE_API_TOKEN"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-prepare", action="store_true")
    ap.add_argument("--poll-min", type=int, default=10)
    ap.add_argument("--until-complete", action="store_true",
                    help="loop: (wait for current run if --wait-only) -> download -> re-push until every prompt is answered")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--push-only", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--wait-only", action="store_true",
                    help="don't upload or push; wait for the current run, then download + analyse")
    ap.add_argument("--download-only", action="store_true",
                    help="only fetch the last run's output + log (no upload, no new run)")
    args = ap.parse_args()
    user = username()
    here = Path(__file__).resolve().parent

    if args.download_only:
        return download_and_import(user, here)
    if args.until_complete:
        return until_complete(user, here, args.poll_min, args.rounds, first_wait=args.wait_only)
    if args.wait_only:
        return wait_and_finish(user, here, args.poll_min)
    # Carry over answers from an earlier (possibly failed) run so nothing is redone.
    prev_dir = K / "kernel_output"
    prev_dir.mkdir(parents=True, exist_ok=True)
    print(sh("kernels", "output", f"{user}/{KERNEL_SLUG}", "-p", str(prev_dir), check=False)[-300:])
    if (prev_dir / "answers.jsonl").exists():
        old = {json.loads(x)["key"]: x for x in open(prev_dir / "answers.jsonl", encoding="utf-8") if x.strip()}
        if (K / "answers.jsonl").exists():
            old |= {json.loads(x)["key"]: x for x in open(K / "answers.jsonl", encoding="utf-8") if x.strip()}
        (K / "answers.jsonl").write_text("".join(v if v.endswith("\n") else v + "\n" for v in old.values()), encoding="utf-8")
        print(f"carried over {len(old)} answers from the previous run")
    for f in prev_dir.glob("*.log"):
        print("previous run log tail:\n", f.read_text(encoding="utf-8", errors="replace")[-1500:])
    if not args.skip_prepare:
        subprocess.run([sys.executable, str(here / "kaggle_prepare.py")], check=True)

    # 2. private dataset with prompts.jsonl (+ previous answers so a re-run resumes)
    ds_dir = K / "dataset"
    ds_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(K / "prompts.jsonl", ds_dir / "prompts.jsonl")
    if (K / "answers.jsonl").exists():  # earlier run's answers -> notebook resumes from them
        shutil.copy(K / "answers.jsonl", ds_dir / "prev_answers.jsonl")
    (ds_dir / "dataset-metadata.json").write_text(json.dumps(
        {"title": f"TokenOpt Hinglish prompts{TAG}", "id": f"{user}/{DS_SLUG}", "licenses": [{"name": "other"}]}))
    # Create first; only if Kaggle says it already exists, add a new version.
    # (A 'status' pre-check misreported a missing dataset as existing -> 403 on version.)
    out = sh("datasets", "create", "-p", str(ds_dir), "--dir-mode", "zip", check=False)  # private by default
    print(out[-400:])
    if "already" in out.lower() or "exists" in out.lower():
        sh("datasets", "version", "-p", str(ds_dir), "-m", time.strftime("update %Y-%m-%d %H:%M"), "--dir-mode", "zip")
    elif "error" in out.lower() or "forbidden" in out.lower() or "denied" in out.lower():
        raise SystemExit("dataset create failed:\n" + out[-800:])
    print("dataset ready:", f"{user}/{DS_SLUG}")
    time.sleep(60)  # let Kaggle finish processing the dataset version

    # 3. push notebook (GPU + internet), it starts running immediately
    kdir = K / "kernel"
    kdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(NB, kdir / NB.name)
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{KERNEL_SLUG}", "title": f"TokenOpt local answers{TAG}", "code_file": NB.name,
        "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": os.environ.get("KAGGLE_GPU", "NvidiaTeslaT4"),  # e.g. NvidiaTeslaP100 when T4 queues are long
        "dataset_sources": [f"{user}/{DS_SLUG}"], "competition_sources": [], "kernel_sources": []}))
    print(sh("kernels", "push", "-p", str(kdir)))

    if args.push_only:
        return
    wait_and_finish(user, here, args.poll_min)


def n_answered() -> tuple[int, int]:
    total = sum(1 for _ in open(K / "prompts.jsonl", encoding="utf-8"))
    got = 0
    if (K / "answers.jsonl").exists():
        got = len({json.loads(x)["key"] for x in open(K / "answers.jsonl", encoding="utf-8") if x.strip()})
    return got, total


def until_complete(user: str, here: Path, poll_min: int, rounds: int, first_wait: bool) -> None:
    for rnd in range(rounds):
        if rnd > 0 or not first_wait:
            subprocess.run([sys.executable, str(Path(__file__)), "--skip-prepare", "--push-only"], check=True)
        try:
            wait_and_finish(user, here, poll_min)
        except SystemExit as e:
            print("round", rnd, "ended without answers:", str(e)[:200], flush=True)
        got, total = n_answered()
        print(f"round {rnd}: {got}/{total} prompts answered", flush=True)
        if got >= total:
            break


def wait_and_finish(user: str, here: Path, poll_min: int) -> None:
    """Poll until the kernel finishes. Network errors (DNS, timeouts) are logged and
    retried, never mistaken for the kernel's own status."""
    while True:
        st = sh("kernels", "status", f"{user}/{KERNEL_SLUG}", check=False)
        line = st.strip().splitlines()[-1] if st.strip() else ""
        if "KernelWorkerStatus." in st:
            print(time.strftime("%H:%M"), line, flush=True)
            if any(k in st for k in ("KernelWorkerStatus.COMPLETE", "KernelWorkerStatus.ERROR",
                                     "KernelWorkerStatus.CANCEL")):
                break
        else:
            print(time.strftime("%H:%M"), "status check failed (network?), retrying:", line[:160], flush=True)
        time.sleep(60 * poll_min)
    for attempt in range(6):  # downloads can hit the same network blips
        try:
            return download_and_import(user, here)
        except SystemExit as e:
            if "no answers.jsonl" in str(e) or attempt == 5:
                raise
            print("download failed, retrying in 2 min:", str(e)[:200], flush=True)
            time.sleep(120)


def download_and_import(user: str, here: Path) -> None:
    out = K / "kernel_output"
    out.mkdir(exist_ok=True)
    sh("kernels", "output", f"{user}/{KERNEL_SLUG}", "-p", str(out))
    got = out / "answers.jsonl"
    if not got.exists():
        raise SystemExit(f"no answers.jsonl in kernel output ({out}); check the notebook log on Kaggle")
    shutil.copy(got, K / "answers.jsonl")
    n = sum(1 for _ in got.open(encoding="utf-8"))
    print(f"{n} answers downloaded")
    subprocess.run([sys.executable, str(here / "kaggle_import.py")], check=True)


if __name__ == "__main__":
    main()
