"""Route research prompts with local Laya (D:/laya) into Yes/No cheap-model labels.

Reads  D:\\Programming\\Research\\prompts.csv   (single column: prompt)
Writes D:\\Programming\\Research\\prompts_routed.csv
       (prompt, cheap_ok, prob_yes, prob_no, answer_confidence, model)

- cheap_ok: "Yes" (cheap model suffices) or "No" (needs premium model)
- prob_yes / prob_no: calibrated option probabilities (sum to 1)
- answer_confidence: max(prob_yes, prob_no) — the calibrated confidence that
  temperature scaling fits and ECE is measured on. NOTE: laya's plain
  `confidence` field is entropy-based (1 - H/log k) and NOT comparable to a
  probability threshold, so it is deliberately not recorded.

- Uses the local English checkpoint only (all prompts are Latin-script; the
  Router would send them all to `english` anyway).
- Full max_len (no truncation of long prompts), batched with sort_by_length.
- Resumable: already-written rows whose prompt matches the source prefix are kept.
- Logs progress + ETA to route_progress.log
"""
import csv
import time
import traceback
from pathlib import Path

import laya

BASE = Path(r"D:\Programming\Projects\code-mixed-gateway\backend\experiments\cascade_routing")
SRC = BASE / "data" / "prompts.csv"
DST = BASE / "data" / "prompts_routed.csv"
LOG = BASE / "scratch" / "route_progress.log"

CHUNK = 160   # states per predict_batch call
BATCH = 16    # states per forward pass

QUESTIONS = {
    "cheap": {
        "type": "choice",
        "instructions": (
            "Can a small cheap language model handle this request correctly "
            "on its own, or does it need an expensive premium model?"
        ),
        "criteria": {
            "Yes": "simple routine request a small model handles well",
            "No": (
                "needs a premium model: hard reasoning, code, "
                "expert advice, or high-stakes accuracy"
            ),
        },
    }
}


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def matching_prefix(source: list, written: list) -> int:
    n = 0
    for a, b in zip(source, written):
        if a != b:
            break
        n += 1
    return n


def main() -> None:
    with open(SRC, encoding="utf-8-sig") as f:
        prompts = [r["prompt"] for r in csv.DictReader(f)]
    n = len(prompts)

    done = 0
    if DST.exists():
        with open(DST, encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            written = [row["prompt"] for row in r]
        done = matching_prefix(prompts, written)
        if done != len(written):
            log(f"WARN: output had {len(written)} rows but only {done} match source prefix; truncating")
            with open(DST, encoding="utf-8", newline="") as f:
                lines = f.readlines()
            with open(DST, "w", encoding="utf-8", newline="") as f:
                f.writelines(lines[: done + 1])
    log(f"total={n} already_done={done}")

    agent = laya.load("D:/laya")
    log("agent ready (english, D:/laya)")

    t0 = time.time()
    with open(DST, "a", encoding="utf-8", newline="") as out:
        w = csv.writer(out)
        if done == 0:
            w.writerow(["prompt", "cheap_ok", "prob_yes", "prob_no", "answer_confidence", "model"])
        for start in range(done, n, CHUNK):
            chunk = prompts[start : start + CHUNK]
            try:
                res = agent.predict_batch(chunk, QUESTIONS, batch_size=BATCH, sort_by_length=True)
            except Exception:
                log(f"chunk@{start}: batched call failed, falling back to serial")
                traceback.print_exc()
                res = []
                for s in chunk:
                    try:
                        res.append(agent.predict(s, QUESTIONS))
                    except Exception:
                        traceback.print_exc()
                        res.append(None)
            for s, r in zip(chunk, res):
                if r is None:
                    w.writerow([s, "", "", "", "", "english"])
                else:
                    a = r["answers"]["cheap"]
                    probs = a.get("probabilities", {})
                    w.writerow([
                        s,
                        a["choice"],
                        probs.get("Yes", ""),
                        probs.get("No", ""),
                        a.get("answer_confidence", ""),
                        "english",
                    ])
            out.flush()
            ndone = min(start + CHUNK, n)
            dt = time.time() - t0
            rate = (ndone - done) / dt if dt > 0 else 0
            eta = (n - ndone) / rate / 60 if rate > 0 else -1
            log(f"progress {ndone}/{n} ({ndone / n:.1%}) elapsed={dt / 60:.1f}m eta={eta:.1f}m")
    log("ALL DONE")


if __name__ == "__main__":
    main()
