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
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import BACKEND, BENCH

K = BENCH / "kaggle"
NB = BACKEND / "kaggle" / "local_answers_t4.ipynb"
DS_SLUG = "tokenopt-hinglish-prompts"
KERNEL_SLUG = "tokenopt-local-answers"


def sh(*args: str, check: bool = True) -> str:
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        raise SystemExit(f"kaggle {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def username() -> str:
    tok = Path.home() / ".kaggle" / "kaggle.json"
    if not tok.exists():
        raise SystemExit(f"missing {tok}: Kaggle -> Settings -> API -> Create New Token, save it there")
    return json.loads(tok.read_text())["username"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-prepare", action="store_true")
    ap.add_argument("--poll-min", type=int, default=10)
    args = ap.parse_args()
    user = username()
    here = Path(__file__).resolve().parent

    if not args.skip_prepare:
        subprocess.run([sys.executable, str(here / "kaggle_prepare.py")], check=True)

    # 2. private dataset with prompts.jsonl (+ previous answers so a re-run resumes)
    ds_dir = K / "dataset"
    ds_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(K / "prompts.jsonl", ds_dir / "prompts.jsonl")
    if (K / "answers.jsonl").exists():  # earlier run's answers -> notebook resumes from them
        shutil.copy(K / "answers.jsonl", ds_dir / "prev_answers.jsonl")
    (ds_dir / "dataset-metadata.json").write_text(json.dumps(
        {"title": "TokenOpt Hinglish prompts", "id": f"{user}/{DS_SLUG}", "licenses": [{"name": "other"}]}))
    exists = "404" not in sh("datasets", "status", f"{user}/{DS_SLUG}", check=False)
    if exists:
        sh("datasets", "version", "-p", str(ds_dir), "-m", time.strftime("update %Y-%m-%d %H:%M"), "--dir-mode", "zip")
    else:
        sh("datasets", "create", "-p", str(ds_dir), "--dir-mode", "zip")  # private by default
    print("dataset ready:", f"{user}/{DS_SLUG}")
    time.sleep(60)  # let Kaggle finish processing the dataset version

    # 3. push notebook (GPU + internet), it starts running immediately
    kdir = K / "kernel"
    kdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(NB, kdir / NB.name)
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{KERNEL_SLUG}", "title": "TokenOpt local answers", "code_file": NB.name,
        "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [f"{user}/{DS_SLUG}"], "competition_sources": [], "kernel_sources": []}))
    print(sh("kernels", "push", "-p", str(kdir)))

    # 4. wait
    while True:
        st = sh("kernels", "status", f"{user}/{KERNEL_SLUG}", check=False)
        print(time.strftime("%H:%M"), st.strip().splitlines()[-1] if st.strip() else st)
        if any(s in st for s in ('"complete"', "COMPLETE", "error", "ERROR", "cancel")):
            break
        time.sleep(60 * args.poll_min)

    # 5. download output, 6. analyse
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
