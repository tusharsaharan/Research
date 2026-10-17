"""Detached waiter: start kaggle_run.py as soon as (a) the Kaggle API token exists
and (b) the guarded2 compression rows are complete. Logs to kaggle/auto.log.

    Start-Process python -ArgumentList "kaggle_auto.py" -WindowStyle Hidden
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys
import time
from pathlib import Path

from common import BENCH

NEED = 8000 * 5  # guarded2 @ 0.4, 0.5, 0.6, 0.7, 0.8
LOG = BENCH / "kaggle" / "auto.log"


def guarded2_rows() -> int:
    seen = set()
    for f in glob.glob(str(BENCH / "compress_rows.guarded2.shard*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
                seen.add((r["pid"], r["method"]))
            except json.JSONDecodeError:
                pass
    return len(seen)


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M ") + msg + "\n")


def main() -> None:
    from kaggle_run import token_ready

    kdir = Path.home() / ".kaggle"
    while True:
        rows = guarded2_rows()
        ready = token_ready() and ((kdir / "kaggle.json").exists() or (kdir / "username").exists())
        if ready and rows >= NEED:
            break
        log(f"waiting: credentials={'yes' if ready else 'no'} guarded2={rows}/{NEED}")
        time.sleep(300)
    log("starting kaggle_run.py")
    here = Path(__file__).resolve().parent
    with LOG.open("a", encoding="utf-8") as fh:
        r = subprocess.run([sys.executable, str(here / "kaggle_run.py")], stdout=fh, stderr=subprocess.STDOUT)
    log(f"kaggle_run.py exited {r.returncode}")
    (BENCH / "kaggle" / ("run.done" if r.returncode == 0 else "run.failed")).write_text(time.strftime("%Y-%m-%d %H:%M"))


if __name__ == "__main__":
    main()
