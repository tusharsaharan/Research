"""Stronger baselines for the hybrid claim (reviewer-proofing):
  llml2L@r    LLMLingua-2, XLM-RoBERTa-large checkpoint (the one Microsoft's papers report)
  longllml@r  LongLLMLingua: question-aware coarse-to-fine (llmlingua lib, Qwen2.5-0.5B as the small LM)
  bm25@r      question-aware BM25 sentence retrieval to the budget (classic extractive baseline)
Runs on Belebele (Hinglish + English) and on SQuAD / MeetingBank / HotpotQA contexts, budgets 0.5 and 0.33.

    python baselines2.py build --set belebele --shard 1/3
    python baselines2.py build --set squad|meetingbank|hotpot --shard 1/3
    python baselines2.py export --set ... [--tag=-hp]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter

from common import BENCH, in_shard, read_jsonl

RATES = (0.5, 0.33)
METHODS = [f"{m}@{r}" for r in RATES for m in ("llml2L", "longllml", "bm25")]
_SENT = re.compile(r"(?<=[.!?।])\s+")
_TOK = re.compile(r"[a-z0-9]+")


def bm25_select(text: str, question: str, rate: float, count) -> str:
    sents = [s for s in _SENT.split(text.strip()) if s] or [text]
    docs = [_TOK.findall(s.lower()) for s in sents]
    q = set(_TOK.findall(question.lower()))
    N, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = Counter(w for d in docs for w in set(d))
    def score(d):
        tf = Counter(d)
        return sum(math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(d) / avg))
                   for w in q if w in tf)
    order = sorted(range(N), key=lambda i: -score(docs[i]))
    budget, used, keep = rate * count(text), 0, []
    for i in order:
        c = count(sents[i])
        if used + c > budget and keep:
            continue
        keep.append(i)
        used += c
    return " ".join(sents[i] for i in sorted(keep))


class Compressors:
    def __init__(self):
        from llmlingua import PromptCompressor

        from gateway.tokenizer import TokenCounter
        self.count = TokenCounter().count
        self.large = PromptCompressor("microsoft/llmlingua-2-xlm-roberta-large-meetingbank", use_llmlingua2=True, device_map="cpu")
        self.long = PromptCompressor("Qwen/Qwen2.5-0.5B-Instruct", device_map="cpu")

    def run(self, text: str, question: str) -> dict:
        out = {}
        for r in RATES:
            try:
                out[f"llml2L@{r}"] = self.large.compress_prompt(text, rate=r, force_tokens=["\n", "?", "."])["compressed_prompt"]
            except Exception:
                out[f"llml2L@{r}"] = text
            try:
                ctx = [s for s in _SENT.split(text.strip()) if s] or [text]
                out[f"longllml@{r}"] = self.long.compress_prompt(
                    ctx, question=question, rate=r, rank_method="longllmlingua", condition_in_question="after",
                    condition_compare=True, reorder_context="original", dynamic_context_compression_ratio=0.3,
                    context_budget="+100")["compressed_prompt"]
            except Exception:
                out[f"longllml@{r}"] = text
            out[f"bm25@{r}"] = bm25_select(text, question, r, self.count)
        return out


def units(name: str):
    """(id, tag, text, question) per compression unit of a set."""
    if name == "belebele":
        for it in read_jsonl(BENCH / "belebele" / "items.jsonl"):
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                yield it["id"], tag, it[lang]["passage"], it[lang]["question"]
    else:
        d = BENCH / ("hotpot" if name == "hotpot" else f"longqa_{name}")
        for it in read_jsonl(d / "items.jsonl")[: 300 if name == "hotpot" else None]:
            yield it["id"], "", it["context"], it["question"]


def build(name: str, shard: str) -> None:
    import torch
    torch.set_num_threads(4)
    c = Compressors()
    path = BENCH / "baselines2" / f"{name}.{shard.replace('/', 'of')}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(x["id"], x["tag"]) for x in read_jsonl(path)} if path.exists() else set()
    with path.open("a", encoding="utf-8") as fh:
        for iid, tag, text, q in units(name):
            if (iid, tag) in done or not in_shard(iid, shard):
                continue
            v = c.run(text, q)
            fh.write(json.dumps({"id": iid, "tag": tag, "variants": v,
                                 "kept": {m: c.count(t) / max(1, c.count(text)) for m, t in v.items()}}, ensure_ascii=False) + "\n")
            fh.flush()
    print("done", name, shard, flush=True)


def export(name: str, tag_dir: str) -> None:
    from belebele_cm import mcq
    from collect import SYSTEM
    from hotpot import SYSTEM as HSYS

    kfile = BENCH / f"kaggle{tag_dir}" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    items = {}
    if name == "belebele":
        items = {r["id"]: r for r in read_jsonl(BENCH / "belebele" / "items.jsonl")}
    else:
        d = BENCH / ("hotpot" if name == "hotpot" else f"longqa_{name}")
        items = {r["id"]: r for r in read_jsonl(d / "items.jsonl")}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for f in sorted((BENCH / "baselines2").glob(f"{name}.*.jsonl")):
            for x in read_jsonl(f):
                it = items[x["id"]]
                for m, t in x["variants"].items():
                    if name == "belebele":
                        lang = "hinglish" if x["tag"] == "hi" else "english"
                        meth, key = f"{x['tag']}:{m}", f"{x['id']}|{lang}|{x['tag']}:{m}"
                        row = {"key": key, "item_id": x["id"], "lang": lang, "methods": [meth], "task": "mcq",
                               "system": SYSTEM["mcq"], "prompt": mcq(t, it[lang]["question"], it[lang]["options"])}
                    else:
                        key = f"{x['id']}|english|b2:{m}"
                        row = {"key": key, "item_id": x["id"], "lang": "english", "methods": [m], "task": "hotpot",
                               "system": HSYS, "prompt": f"Context:\n{t}\n\nQuestion: {it['question']}"}
                    if key not in have:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                        n += 1
    print(f"appended {n} -> {kfile}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "export"])
    ap.add_argument("--set", required=True, choices=["belebele", "squad", "meetingbank", "hotpot"])
    ap.add_argument("--shard", default="1/1")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    build(a.set, a.shard) if a.cmd == "build" else export(a.set, a.tag)
