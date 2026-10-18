"""One command per day: translate -> answers -> compression check -> grade -> certify -> compression benchmark -> report.

Each step stops by itself at the day's token budget and resumes tomorrow, so
running this once a day (by hand or from Windows Task Scheduler) finishes the
whole benchmark without anyone babysitting it.

    python backend/scripts/bench/run_daily.py                 # whole benchmark
    python backend/scripts/bench/run_daily.py --shard 2/3     # teammate 2 of 3, own key

Budgets: the 20b model is shared by translation and cheap answers; give
translation the larger share until all items are translated.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def step(name: str, *args: str) -> None:
    print(f"\n=== {name} ===", flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    r = subprocess.run([sys.executable, *args], cwd=ROOT, env=env)
    if r.returncode:
        print(f"[{name}] exited {r.returncode}; continuing with the next step")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default=None)
    ap.add_argument("--translate-budget", type=int, default=130_000, help="20b tokens/day for translation")
    ap.add_argument("--compress-budget", type=int, default=170_000,
                    help="20b tokens/day total cap for the compression answer check (after translation)")
    ap.add_argument("--cheap-budget", type=int, default=195_000, help="20b tokens/day total (translation + compression check + cheap answers)")
    ap.add_argument("--premium-budget", type=int, default=190_000, help="120b tokens/day")
    ap.add_argument("--splits", type=int, default=1000)
    args = ap.parse_args()
    shard = ["--shard", args.shard] if args.shard else []
    b = str(HERE)
    step("translate", f"{b}/translate.py", "--daily-token-budget", str(args.translate_budget), *shard)
    step("premium answers", f"{b}/collect.py", "--tiers", "premium", "--daily-token-budget", str(args.premium_budget), *shard)
    step("compression answer check", f"{b}/compress_answers.py", "--daily-token-budget", str(args.compress_budget))
    step("cheap answers", f"{b}/collect.py", "--tiers", "cheap", "--daily-token-budget", str(args.cheap_budget), *shard)
    # CondaQA negation test on an open-weight API model (free tier; stops at the daily quota, resumes next day)
    step("condaqa answers (gemma)", f"{b}/api_answer.py", "--provider", "gemini", "--model", "gemma-4-26b-a4b-it",
         "--task", "condaqa", "--workers", "8", "--max-out", "4096")
    step("grade", f"{b}/grade.py")
    step("certify", f"{b}/certify.py", "--splits", str(args.splits))
    step("compression benchmark (offline, 8,000 prompts)", f"{b}/compress_eval.py", "--n", "8000")
    step("verification sheet", f"{b}/translate.py", "--export-sheet")
    step("weekly report", str(ROOT / "backend" / "scripts" / "weekly_report.py"), "--skip-tests")
    step("status", f"{b}/status.py")


if __name__ == "__main__":
    main()
