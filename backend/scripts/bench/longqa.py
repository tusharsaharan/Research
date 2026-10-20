"""Out-of-domain check of the hybrid compressor with FROZEN settings (chosen on HotpotQA, see
PREREG.md 2026-10-21): MuSiQue, 2WikiMultiHopQA, SQuAD v2 (answerable), MeetingBank-QA.
Reuses hotpot.py (same prompt, F1 grading) with a per-dataset folder.

    python longqa.py build --ds musique --n 400
    python longqa.py compress --ds musique --shard 1/4
    python longqa.py export-kaggle --ds musique          # KAGGLE_TAG selects the queue
    python longqa.py grade --ds musique --answers <answers.jsonl>
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import sys
from pathlib import Path

import hotpot
from common import BENCH

FROZEN = ["heuristic", "llmlingua2@0.5", "llmlingua2@0.33", "llmlingua2@0.25", "llmlingua2@0.2", "guarded@0.5",
          "guarded@0.33", "sentsel@0.5", "sentsel@0.33", "hybrid-s0.7@0.5", "hybrid-t-heavy@0.33", "hybrid-s0.5@0.25",
          "hybrid-s0.45@0.2"]
SPECS = {"musique": ("bdsaglam/musique", "answerable", "validation", "mq"),
         "2wiki": ("framolfese/2WikiMultihopQA", "default", "validation", "2w"),
         "squad": ("rajpurkar/squad_v2", "squad_v2", "validation", "sq"),
         "meetingbank": ("microsoft/MeetingBank-QA-Summary", "default", "test", "mb")}


def lit(x):
    return ast.literal_eval(x) if isinstance(x, str) else x


def build(ds: str, n: int) -> None:
    from build_items import hf_rows

    from gateway.tokenizer import TokenCounter

    name, cfg, split, pre = SPECS[ds]
    rows = hf_rows(name, cfg, split)
    tc = TokenCounter()
    out = []
    for i, r in enumerate(rows):
        if ds == "musique":
            ps = lit(r["paragraphs"])
            ctx = "\n".join(f"{p['title']}: {p['paragraph_text']}" for p in ps)
            out.append({"id": f"{pre}-{r['id']}", "question": r["question"], "answer": r["answer"], "context": ctx})
        elif ds == "2wiki":
            c = lit(r["context"])
            ctx = "\n".join(f"{t}: {''.join(s)}" for t, s in zip(c["title"], c["sentences"]))
            out.append({"id": f"{pre}-{r['id']}", "question": r["question"], "answer": r["answer"], "context": ctx})
        elif ds == "squad":
            ans = lit(r["answers"])["text"]
            if ans:
                out.append({"id": f"{pre}-{r['id']}", "question": r["question"], "answer": ans[0], "context": r["context"]})
        elif ds == "meetingbank":
            if tc.count(r["prompt"]) > 2500:
                continue
            for j, qa in enumerate(lit(r["QA_pairs"])):
                out.append({"id": f"{pre}-{r['idx']}-{j}", "question": qa["question"], "answer": qa["answer"],
                            "context": r["prompt"]})
    random.Random(20261021).shuffle(out)
    d = BENCH / f"longqa_{ds}"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "items.jsonl").open("w", encoding="utf-8") as fh:
        for it in out[:n]:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(ds, len(out[:n]), "items ->", d)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "compress", "export-kaggle", "grade"])
    ap.add_argument("--ds", required=True, choices=list(SPECS))
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--shard", default=None)
    ap.add_argument("--answers", default=None)
    a = ap.parse_args()
    hotpot.OUT = BENCH / f"longqa_{a.ds}"
    hotpot.METHODS = FROZEN
    if a.cmd == "build":
        build(a.ds, a.n)
    elif a.cmd == "compress":
        hotpot.compress(a.shard, FROZEN, 0)
    elif a.cmd == "export-kaggle":
        hotpot.export_kaggle(0)
    else:
        hotpot.grade([str(Path(a.answers).resolve())])
