"""Generate the weekly progress report from evidence, not memory.

Reads docs/progress/ROADMAP.md (weeks, dates, owners, ticked tasks), git
history for the week, the backend test suite, and benchmark progress, and
writes docs/progress/weekly/week-NN.md.

    python backend/scripts/weekly_report.py              # current week by date
    python backend/scripts/weekly_report.py --week 1
    python backend/scripts/weekly_report.py --skip-tests
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ROADMAP = ROOT / "docs" / "progress" / "ROADMAP.md"
OUT_DIR = ROOT / "docs" / "progress" / "weekly"

_WEEK = re.compile(r"^## Week (\d+) — (.+?) \((\d{4}-\d{2}-\d{2}) → (\d{4}-\d{2}-\d{2})\)")
_TASK = re.compile(r"^- \[( |x|X)\] \[([^\]]+)\] (.+)")


def parse_roadmap() -> list[dict]:
    weeks: list[dict] = []
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        m = _WEEK.match(line)
        if m:
            weeks.append({"n": int(m[1]), "title": m[2], "start": m[3], "end": m[4], "tasks": [], "demo": ""})
            continue
        if not weeks:
            continue
        t = _TASK.match(line)
        if t:
            weeks[-1]["tasks"].append({"done": t[1] != " ", "owner": t[2], "text": t[3]})
        elif line.startswith("Demo:"):
            weeks[-1]["demo"] = line[len("Demo:"):].strip()
    return weeks


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout


def commits(start: str, end: str) -> dict[str, list[str]]:
    until = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    out = git("log", f"--since={start}", f"--until={until}", "--no-merges", "--format=%an\x1f%h %s")
    by_author: dict[str, list[str]] = defaultdict(list)
    for line in out.splitlines():
        if "\x1f" in line:
            author, subject = line.split("\x1f", 1)
            by_author[author].append(subject)
    return by_author


def run_tests() -> str:
    env = {**os.environ, "GATEWAY_DRY_RUN": "true", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:warnings"], cwd=BACKEND,
                       capture_output=True, text=True, encoding="utf-8", env=env)
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    summary = lines[-1] if lines else "no output"
    failed = [ln for ln in lines if ln.startswith("FAILED")]
    return summary + ("".join(f"\n  - {f}" for f in failed) if failed else "")


def bench_status() -> dict:
    sys.path.insert(0, str(BACKEND / "scripts" / "bench"))
    try:
        from status import status

        st = status()
        summ = BACKEND / "data" / "bench" / "summary.json"
        st["summary"] = json.loads(summ.read_text()) if summ.exists() else {}
        return st
    except Exception as e:  # report never fails because data is missing
        return {"error": str(e)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()

    weeks = parse_roadmap()
    today = date.today().isoformat()
    week = next((w for w in weeks if w["n"] == args.week), None) if args.week else \
        next((w for w in weeks if w["start"] <= today <= w["end"]), weeks[-1])
    if week is None:
        raise SystemExit(f"week {args.week} not in {ROADMAP}")

    done = [t for t in week["tasks"] if t["done"]]
    open_ = [t for t in week["tasks"] if not t["done"]]
    per_owner: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for t in week["tasks"]:
        per_owner[t["owner"]][1] += 1
        per_owner[t["owner"]][0] += t["done"]
    cm = commits(week["start"], week["end"])
    # Roadmap owners are first names; git authors are full names.
    for author in list(cm):
        owner = next((o for o in per_owner if o != "All" and author.lower().startswith(o.lower())), None)
        if owner:
            cm[owner] = cm.get(owner, []) + cm.pop(author)
    tests = "skipped" if args.skip_tests else run_tests()
    bench = bench_status()
    nxt = next((w for w in weeks if w["n"] == week["n"] + 1), None)

    md = [f"# Week {week['n']} progress — {week['title']}",
          f"_{week['start']} → {week['end']} · generated {datetime.now():%Y-%m-%d %H:%M} by `backend/scripts/weekly_report.py`_", "",
          f"**Planned tasks done: {len(done)}/{len(week['tasks'])}**", "",
          "| Owner | Done | Commits this week |", "|---|---|---|"]
    owners = sorted(set(per_owner) | set(cm))
    for o in owners:
        d, n = per_owner.get(o, [0, 0])
        md.append(f"| {o} | {d}/{n} | {len(cm.get(o, []))} |")
    done_lines = [f"- [{t['owner']}] {t['text']}" for t in done] or ["- (none ticked yet)"]
    open_lines = [f"- [{t['owner']}] {t['text']}" for t in open_] or ["- (nothing)"]
    md += ["", "## Done", *done_lines, "", "## Still open", *open_lines, "", "## Evidence", "", "**Commits**"]
    for o in sorted(cm):
        md += [f"- {o}:"] + [f"  - {s}" for s in cm[o]]
    if not cm:
        md.append("- no commits in this date range (uncommitted work does not count as evidence)")
    md += ["", f"**Backend tests:** {tests}", "", "**Benchmark pipeline**", "```json",
           json.dumps(bench, indent=2, ensure_ascii=False), "```", "",
           f"**This week's demo:** {week['demo'] or '-'}"]
    if nxt:
        md += ["", f"## Next week — {nxt['title']}", *[f"- [{t['owner']}] {t['text']}" for t in nxt["tasks"]]]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"week-{week['n']:02d}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("report ->", out)


if __name__ == "__main__":
    main()
