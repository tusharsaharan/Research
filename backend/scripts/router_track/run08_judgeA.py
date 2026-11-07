"""run08: Judge A — task-consequence importance mining (parallel, cheap tier only).

For each of 400 frozen queries, answers 6 ablated variants with the cheap
model and measures fidelity delta vs the full-text answer. A word class is
important iff dropping it moves the answer.

Frozen: query IDs (seed 42), variant builders, worker count. Parallelism
changes speed, not science: 5 threads x 1 Groq key each, per-key cooldown.

Usage: GROQ_API_KEYS=k1,k2,k3,k4,k5 python run08_judgeA.py [--max-tasks 500]
Re-runnable; checkpoints every variant to judgeA_labels.jsonl.
"""

import argparse
import json
import queue
import random
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from common import CHEAP_MODEL, load_jsonl, track  # noqa: E402
from gateway.lexicons import _lexicons  # noqa: E402
from gateway.modules.m10_train.reward import reward  # noqa: E402
from gateway.modules.m2_compressor.safety_span import detect_spans  # noqa: E402

import httpx  # noqa: E402

SEED = 42
N_QUERIES = 400
N_WORKERS = 5
GROQ_BASE = "https://api.groq.com/openai/v1"
NEGATIONS = {"nahi", "nahin", "nah", "not", "no", "never", "n't", "na", "mat", "naa"}


def build_queries(track_dir: Path) -> list[dict]:
    q = load_jsonl(track_dir / "queries.jsonl")
    labeled = {r["id"] for r in load_jsonl(track_dir / "groq_labels.jsonl")}
    q = [x for x in q if x["id"] in labeled]
    real = [x for x in q if x["src"] in ("bench", "seed", "human")]
    aug = [x for x in q if x["src"] == "aug"]
    rng = random.Random(SEED)
    # stratify aug by length tercile for a fair mix
    aug_sorted = sorted(aug, key=lambda x: len(x["text"].split()))
    n = len(aug_sorted)
    thirds = [aug_sorted[: n // 3], aug_sorted[n // 3 : 2 * n // 3], aug_sorted[2 * n // 3 :]]
    need = N_QUERIES - len(real)
    per = need // 3
    picked = real + thirds[0][:per] + thirds[1][:per] + thirds[2][: need - 2 * per]
    ids = sorted({x["id"] for x in picked})[:N_QUERIES]
    by_id = {x["id"]: x for x in q}
    return [by_id[i] for i in ids]


def variants(query: str) -> dict[str, str | None]:
    """Return {variant_name: ablated_text}. None = not applicable (skip)."""
    lex = _lexicons()
    toks = query.split()
    low = [t.lower().strip(",.!?") for t in toks]
    out: dict[str, str | None] = {}
    # V_heu: canonical lexicon prune (no masking here; spans tested separately)
    keep = [t for t in toks if t.lower().strip(",.!?") not in lex["fillers_unconditional"]]
    out["V_heu"] = " ".join(keep) if keep else None
    # V_voc: drop vocatives + greetings only
    vg = set(lex["vocatives"]) | set(g for g in lex["greetings"])
    novoc = [t for t in toks if t.lower().strip(",.!?;:") not in vg]
    out["V_voc"] = " ".join(novoc) if novoc and len(novoc) < len(toks) else None
    # V_ent: delete protected spans entirely (control: expect big delta)
    spans = detect_spans(query)
    if spans:
        cut = query
        for sp in sorted(spans, key=lambda s: -s.start):
            cut = cut[: sp.start] + " " + cut[sp.end :]
        out["V_ent"] = " ".join(cut.split()) or None
    else:
        out["V_ent"] = None
    # V_neg: drop negation tokens (control: expect meaning flip)
    noneg = [t for t in toks if t.lower().strip(",.!?") not in NEGATIONS]
    out["V_neg"] = " ".join(noneg) if len(noneg) < len(toks) and noneg else None
    # V_trunc: first 60% (position control)
    k = max(3, int(0.6 * len(toks)))
    out["V_trunc"] = " ".join(toks[:k]) if k < len(toks) else None
    # V_aggr: drop everything lexicon-droppable ignoring guards
    drop_all = set(lex["fillers_unconditional"]) | set(lex["fillers_non_initial"]) | set(lex["vocatives"])
    aggr = [t for t in toks if t.lower().strip(",.!?") not in drop_all]
    out["V_aggr"] = " ".join(aggr) if aggr and len(aggr) < len(toks) else None
    return out


class Pool:
    def __init__(self, keys: list[str]):
        import os

        self.keys = keys or [os.environ.get("GROQ_API_KEY", "")]
        assert any(self.keys), "Set GROQ_API_KEYS env var"
        self.cool: dict[str, float] = {}
        self.lock = threading.Lock()
        self.idx = 0

    def call(self, text: str) -> str:
        for _ in range(12):
            with self.lock:
                now = time.time()
                order = sorted(self.keys, key=lambda k: self.cool.get(k, 0))
                key = order[0]
                wait = self.cool.get(key, 0) - now
            if wait > 0:
                time.sleep(min(wait, 120))
                continue
            try:
                with httpx.Client(timeout=60) as c:
                    r = c.post(
                        f"{GROQ_BASE}/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"model": CHEAP_MODEL,
                              "messages": [{"role": "user", "content": text[:1500]}],
                              "temperature": 0.0, "max_tokens": 160, "reasoning_effort": "low"},
                    )
                    if r.status_code == 429:
                        with self.lock:
                            self.cool[key] = time.time() + 120
                        continue
                    r.raise_for_status()
                    msg = r.json()["choices"][0]["message"]
                    content = (msg.get("content") or "").strip() or (msg.get("reasoning") or "").strip()
                    return content
            except Exception:
                time.sleep(5)
        return "[ERROR judgeA]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-tasks", type=int, default=10_000)
    ap.add_argument("--sleep", type=float, default=6.0)
    args = ap.parse_args()
    import os

    t = track()
    queries = build_queries(t)
    (t / "judgeA_query_ids.json").write_text(json.dumps([q["id"] for q in queries]), encoding="utf-8")
    lab = {r["id"]: r for r in load_jsonl(t / "groq_labels.jsonl")}
    out_path = t / "judgeA_labels.jsonl"
    done = {(json.loads(l)["id"], json.loads(l)["variant"]) for l in open(out_path, encoding="utf-8")} if out_path.exists() else set()

    tasks: queue.Queue = queue.Queue()
    n_queued = 0
    for q in queries:
        full_ans = lab[q["id"]]["cheap"]
        for vname, vtext in variants(q["text"]).items():
            if vtext is None or (q["id"], vname) in done:
                continue
            if n_queued >= args.max_tasks:
                break
            tasks.put((q, vname, vtext, full_ans))
            n_queued += 1
    print(f"queries={len(queries)} queued_tasks={n_queued} already_done={len(done)}")
    if n_queued == 0:
        print("JUDGEA COMPLETE")
        return

    keys = [k.strip() for k in os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API_KEY", "")).split(",") if k.strip()]
    pool = Pool(keys)
    fh_lock = threading.Lock()
    fh = open(out_path, "a", encoding="utf-8")
    counter = {"n": 0}

    def worker():
        while True:
            try:
                q, vname, vtext, full_ans = tasks.get_nowait()
            except queue.Empty:
                return
            ans = pool.call(vtext)
            f = reward(q["text"], vtext, full_ans, ans)
            row = {"id": q["id"], "variant": vname, "ablated": vtext[:500], "answer": ans[:800],
                   "full_answer": full_ans[:800], "fidelity": round(f, 4), "delta": round(1 - f, 4),
                   "len_ratio": round(len(vtext.split()) / max(1, len(q["text"].split())), 4)}
            with fh_lock:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                counter["n"] += 1
                if counter["n"] % 50 == 0:
                    print(f"  +{counter['n']}/{n_queued} ...", flush=True)
            time.sleep(args.sleep)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(min(N_WORKERS, n_queued))]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    fh.close()
    print(f"chunk done. completed_this_run={counter['n']}")


if __name__ == "__main__":
    main()
