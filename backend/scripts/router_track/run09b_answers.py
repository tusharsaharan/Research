"""run09b: answer-level rewrite-vs-drops verdict (the correct metric).

Text-vs-premium fidelity caps good compressions (~0.55 max) via brevity
penalty. Correct comparison: answer the COMPRESSED texts with the cheap
model and score those answers vs the premium answer.

+400 cheap calls (heuristic-compressed + best-rewrite per query).
Outputs rewrite_report.json (overwrites run09 text-level numbers).
"""

import argparse
import json
import queue
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from common import CHEAP_MODEL, load_jsonl, track  # noqa: E402
from gateway.modules.m10_train.reward import reward  # noqa: E402
from gateway.modules.m2_compressor.compressor import Compressor, REWRITE_BAR  # noqa: E402
from gateway.tokenizer import TokenCounter  # noqa: E402

import httpx  # noqa: E402

GROQ_BASE = "https://api.groq.com/openai/v1"
N_WORKERS = 5


class Pool:
    def __init__(self, keys):
        self.keys = keys
        self.cool: dict[str, float] = {}
        self.lock = threading.Lock()

    def call(self, text: str) -> str:
        for _ in range(12):
            with self.lock:
                order = sorted(self.keys, key=lambda k: self.cool.get(k, 0))
                key = order[0]
                wait = self.cool.get(key, 0) - time.time()
            if wait > 0:
                time.sleep(min(wait, 120))
                continue
            try:
                with httpx.Client(timeout=60) as c:
                    r = c.post(f"{GROQ_BASE}/chat/completions",
                               headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                               json={"model": CHEAP_MODEL, "messages": [{"role": "user", "content": text[:1500]}],
                                     "temperature": 0.0, "max_tokens": 160, "reasoning_effort": "low"})
                    if r.status_code == 429:
                        with self.lock:
                            self.cool[key] = time.time() + 120
                        continue
                    r.raise_for_status()
                    msg = r.json()["choices"][0]["message"]
                    return ((msg.get("content") or "").strip() or (msg.get("reasoning") or "").strip())
            except Exception:
                time.sleep(5)
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=6.0)
    ap.add_argument("--tag", type=str, default="")
    args = ap.parse_args()
    import os

    t = track()
    lab = {r["id"]: r for r in load_jsonl(t / "groq_labels.jsonl")}
    suffix = f"_{args.tag}" if args.tag else ""
    rw = {json.loads(l)["id"]: json.loads(l) for l in open(t / f"rewrite_labels{suffix}.jsonl", encoding="utf-8")}
    counter = TokenCounter()
    comp = Compressor(counter)
    out_path = t / f"rewrite_answers{suffix}.jsonl"
    done = {json.loads(l)["id"] for l in open(out_path, encoding="utf-8")} if out_path.exists() else set()
    todo = [i for i in rw if i not in done]
    print(f"todo={len(todo)} done={len(done)}")
    if todo:
        keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", "")).split(",") if k.strip()]
        pool = Pool(keys)
        tasks: queue.Queue = queue.Queue()
        for i in todo:
            q = lab[i]
            hc = comp.compress_heuristic(q["text"]).compressed
            tasks.put((i, "heu", hc))
            tasks.put((i, "rew", rw[i]["best"]))
        fh_lock = threading.Lock()
        fh = open(out_path, "a", encoding="utf-8")
        counter_n = {"n": 0}
        total = len(todo) * 2

        def worker():
            while True:
                try:
                    i, kind, text = tasks.get_nowait()
                except queue.Empty:
                    return
                ans = pool.call(text) if text.strip() else ""
                with fh_lock:
                    fh.write(json.dumps({"id": i, "kind": kind, "answer": ans[:800]}, ensure_ascii=False) + "\n")
                    fh.flush()
                    counter_n["n"] += 1
                    if counter_n["n"] % 50 == 0:
                        print(f"  +{counter_n['n']}/{total} ...", flush=True)
                time.sleep(args.sleep)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(N_WORKERS)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        fh.close()

    ans: dict = {}
    for l in open(out_path, encoding="utf-8"):
        r = json.loads(l)
        ans[(r["id"], r["kind"])] = r["answer"]
    heu_f, rew_f, heu_r, rew_r = [], [], [], []
    for i in rw:
        q = lab[i]
        ha = ans.get((i, "heu"), "")
        ra = ans.get((i, "rew"), "")
        heu_f.append(reward(q["text"], q["text"], q["premium"], ha))
        rew_f.append(reward(q["text"], q["text"], q["premium"], ra))
        hc = comp.compress_heuristic(q["text"])
        heu_r.append(hc.ratio)
        rew_r.append(counter.count(rw[i]["best"]) / max(1, counter.count(q["text"])))
    rep = {"n": len(rw), "metric": "answer-level fidelity vs premium (correct scale)",
           "heuristic": {"mean_answer_fidelity": round(statistics.mean(heu_f), 4),
                         "mean_ratio": round(statistics.mean(heu_r), 4)},
           "rewrite": {"mean_answer_fidelity": round(statistics.mean(rew_f), 4),
                       "mean_ratio": round(statistics.mean(rew_r), 4)},
           "win_rate_rewrite": round(sum(1 for a, b in zip(rew_f, heu_f) if a > b) / len(rw), 4)}
    (t / f"rewrite_report{suffix}.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
