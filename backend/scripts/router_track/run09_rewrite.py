"""run09: rewrite-vs-drops study. Heuristic vs reward-gated LLM rewrite (best of 3).

200 frozen queries (first 200 judgeA IDs). Per query: heuristic (local) +
3 rewrite candidates (temps 0.0/0.3/0.7, protected-term constraints).
Winner = max reward vs premium reference, served iff >= REWRITE_BAR.
~600 cheap calls, 5 parallel workers. Outputs rewrite_report.json.
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
from gateway.modules.m2_compressor.compressor import REWRITE_BAR  # noqa: E402
from gateway.modules.m2_compressor.prompts import rewrite_messages  # noqa: E402
from gateway.modules.m4_router.difficulty import DifficultyScorer  # noqa: E402
from gateway.modules.m2_compressor.safety_span import detect_spans  # noqa: E402

import httpx  # noqa: E402

GROQ_BASE = "https://api.groq.com/openai/v1"
NEGATIONS = {"nahi", "nahin", "nah", "not", "never", "n't", "mat"}
N_WORKERS = 5


def protected_terms(text: str) -> list[str]:
    terms = [sp.text for sp in detect_spans(text)]
    terms += [t for t in text.split() if t.lower().strip(",.!?") in NEGATIONS]
    seen, out = set(), []
    for w in terms:
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return out[:20]


class Pool:
    def __init__(self, keys):
        self.keys = keys
        self.cool: dict[str, float] = {}
        self.lock = threading.Lock()
        self.idx = 0

    def call(self, messages, temp: float) -> str:
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
                               json={"model": CHEAP_MODEL, "messages": messages, "temperature": temp,
                                     "max_tokens": 160, "reasoning_effort": "low"})
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
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=6.0)
    ap.add_argument("--tag", type=str, default="", help="v2 = length-capped + joint selection")
    ap.add_argument("--brevity-lambda", type=float, default=0.3)
    args = ap.parse_args()
    import os

    t = track()
    qids = json.loads((t / "judgeA_query_ids.json").read_text())[args.offset : args.offset + args.n]
    lab = {r["id"]: r for r in load_jsonl(t / "groq_labels.jsonl")}
    suffix = f"_{args.tag}" if args.tag else ""
    out_path = t / f"rewrite_labels{suffix}.jsonl"
    done = {json.loads(l)["id"] for l in open(out_path, encoding="utf-8")} if out_path.exists() else set()
    todo = [i for i in qids if i not in done]
    print(f"n={len(qids)} todo={len(todo)} done={len(done)} bar={REWRITE_BAR}")
    if not todo:
        print("REWRITE STUDY COMPLETE")
    else:
        keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", "")).split(",") if k.strip()]
        pool = Pool(keys)
        scorer = DifficultyScorer()
        tasks: queue.Queue = queue.Queue()
        for i in todo:
            tasks.put(i)
        fh_lock = threading.Lock()
        fh = open(out_path, "a", encoding="utf-8")
        counter = {"n": 0}

        def worker():
            while True:
                try:
                    i = tasks.get_nowait()
                except queue.Empty:
                    return
                r = lab[i]
                prot = protected_terms(r["text"])
                cands = []
                mw = max(5, int(len(r["text"].split()) * 0.6)) if args.tag else None
                for temp in (0.0, 0.3, 0.7):
                    cands.append(pool.call(rewrite_messages(r["text"], prot, mw) if args.tag else rewrite_messages(r["text"], prot), temp))
                    time.sleep(1.0)
                if args.tag:
                    from gateway.tokenizer import TokenCounter as _TC

                    _tc = _TC()
                    tok_o = max(1, _tc.count(r["text"]))
                    scored = [(c, reward(r["text"], c, r["premium"], c)) for c in cands if c.strip()]
                    joint = [(c, s - args.brevity_lambda * max(1, _tc.count(c)) / tok_o) for c, s in scored]
                    best, best_r = max(joint, key=lambda kv: kv[1]) if joint else ("", 0.0)
                    # recover raw reward of the joint winner for the report
                    best_r = next((s for c, s in scored if c == best), 0.0) if best else 0.0
                else:
                    scored = [(c, reward(r["text"], c, r["premium"], c)) for c in cands if c.strip()]
                    best, best_r = max(scored, key=lambda kv: kv[1]) if scored else ("", 0.0)
                row = {"id": i, "candidates": [c[:300] for c, _ in scored],
                       "best": best[:500], "best_reward": round(best_r, 4),
                       "accepted": bool(best_r >= REWRITE_BAR), "protected": prot}
                with fh_lock:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    counter["n"] += 1
                    if counter["n"] % 25 == 0:
                        print(f"  +{counter['n']}/{len(todo)} ...", flush=True)
                time.sleep(args.sleep)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(min(N_WORKERS, len(todo)))]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        fh.close()

    # report (over all completed rows)
    from gateway.tokenizer import TokenCounter  # noqa: E402

    counter = TokenCounter()
    rows = [json.loads(l) for l in open(out_path, encoding="utf-8")]
    heu_f, rew_f, heu_r, rew_r, acc = [], [], [], [], 0
    for r in rows:
        q = lab[r["id"]]
        hc = __import__("gateway.modules.m2_compressor.compressor", fromlist=["Compressor"]).Compressor(counter).compress_heuristic(q["text"])
        heu_f.append(reward(q["text"], hc.compressed, q["premium"], hc.compressed))
        heu_r.append(hc.ratio)
        if r["accepted"]:
            rew_f.append(reward(q["text"], r["best"], q["premium"], r["best"]))
            rew_r.append(counter.count(r["best"]) / max(1, counter.count(q["text"])))
            acc += 1
    rep = {"n": len(rows),
           "heuristic": {"mean_fidelity": round(statistics.mean(heu_f), 4), "mean_ratio": round(statistics.mean(heu_r), 4)},
           "rewrite_accepted": {"n": acc, "rate": round(acc / max(1, len(rows)), 4),
                                "mean_fidelity": round(statistics.mean(rew_f), 4) if rew_f else 0.0,
                                "mean_ratio": round(statistics.mean(rew_r), 4) if rew_r else 0.0},
           "bar": REWRITE_BAR, "bar_note": "PROVISIONAL — final bar fit to human_check.csv"}
    (t / f"rewrite_report{suffix}.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
