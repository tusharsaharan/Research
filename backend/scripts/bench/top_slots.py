"""Meaning beyond negation: slot retention on human code-mixed commands (Hinglish-TOP).

WillHeld/hinglish_top pairs each English task-oriented query (TOP) with a human
Hinglish version and gold semantic parses, e.g.
  cs_query "Kya hawaii me raining ho rahi hai?"  [IN:GET_WEATHER Kya [SL:LOCATION hawaii] me
  [SL:WEATHER_ATTRIBUTE raining] ho rahi hai?]
Every slot value is a meaning unit the compressed prompt must keep. For each compressor we
report, per language: tokens kept (o200k), share of slots fully kept, share of queries
with every slot kept. The English side is the parallel human query, so EN vs HI is a
controlled comparison on the same meanings. Also reported: the translation token ratio
(English / Hinglish tokens) per tokenizer = the saving available to "translate, then send".

    python top_slots.py build --n 2000
    python top_slots.py run
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict

from common import BENCH, read_jsonl

OUT = BENCH / "top"


def slots(parse: str) -> list[list[str]]:
    """Word lists of every [SL:...] span (nested intents inside a slot keep their words)."""
    toks = parse.replace("[", " [ ").replace("]", " ] ").split()
    out, stack = [], []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "[":
            label = toks[i + 1]
            stack.append((label, []))
            i += 2
            continue
        if t == "]":
            label, ws = stack.pop()
            if label.startswith("SL:") and ws:
                out.append(ws)
            if stack:
                stack[-1][1].extend(ws)
            i += 1
            continue
        if stack:
            stack[-1][1].append(t)
        i += 1
    return out


def build(n: int) -> None:
    from build_items import hf_rows

    rows = hf_rows("WillHeld/hinglish_top", "default", "test")
    random.Random(20261019).shuffle(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    k = 0
    with (OUT / "items.jsonl").open("w", encoding="utf-8") as fh:
        for i, r in enumerate(rows):
            en, hi = slots(r["en_parse"]), slots(r["cs_parse"])
            if not hi or not en:
                continue
            fh.write(json.dumps({"id": f"top-{i}", "domain": r["domain"], "english": r["en_query"], "hinglish": r["cs_query"],
                                 "slots_english": en, "slots_hinglish": hi}, ensure_ascii=False) + "\n")
            k += 1
            if k >= n:
                break
    print(k, "queries with slots ->", OUT / "items.jsonl")


def norm_words(t: str) -> list[str]:
    return [w for w in (x.strip(",.!?;:\"'()[]{}").lower() for x in t.split()) if w]


def slot_kept(slot: list[str], comp: str) -> bool:
    have = Counter(norm_words(comp))
    need = Counter(w.lower().strip(",.!?;:\"'()[]{}") for w in slot)
    return all(have[w] >= c for w, c in need.items() if w)


def run() -> None:
    import torch

    from compress_eval import HINGLISH_INSTRUCT, load_tokenizers
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m2_compressor.guarded import compress_guarded
    from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.tokenizer import TokenCounter
    from tokopt import TokOptNormalizer
    import csv

    torch.set_num_threads(8)
    items = read_jsonl(OUT / "items.jsonl")
    toks = load_tokenizers()
    o200k = toks["o200k"]
    with HINGLISH_INSTRUCT.open(encoding="utf-8-sig") as fh:
        corpus = [row["prompt"] for row in csv.DictReader(fh)]
    english_corpus = [it["english"] for it in items]
    ctx = None
    conv = BENCH.parent / "external" / "everyday" / "sample.txt"
    if conv.exists():
        ctx = conv.read_text(encoding="utf-8").split("\n")
    tok_old = TokOptNormalizer(o200k, corpus, english_corpus)
    tok_safe = TokOptNormalizer(o200k, corpus, english_corpus, strict=True, context_corpus=ctx or corpus)
    comp = Compressor(counter=TokenCounter(), use_crf=True, use_llmlingua2=True,
                      crf_model_path=BENCH.parent / "models" / "crf_compressor.pkl",
                      tfidf_path=BENCH.parent / "tfidf" / "hinglish_idf.json")
    lingua = get_compressor()

    def plain(rate):
        def f(t):
            r = comp.compress_llmlingua2(t, rate=rate)
            return r.compressed if r.method == "llmlingua2" else t
        return f

    def guarded(rate):
        return lambda t: compress_guarded(t, rate, lingua) or t

    methods = {"heuristic": lambda t: comp.compress_heuristic(t).compressed, "lexical-safe": compress_lexical_safe,
               "crf": lambda t: comp.compress_crf(t).compressed, "tokopt (old)": tok_old, "tokopt-safe": tok_safe,
               "crf+tokopt (old)": lambda t: tok_old(comp.compress_crf(t).compressed),
               "crf+tokopt-safe": lambda t: tok_safe(comp.compress_crf(t).compressed)}
    for r in (0.8, 0.7, 0.5):
        methods |= {f"llmlingua2@{r}": plain(r), f"guarded@{r}": guarded(r)}
    n_o200k = lambda t: len(o200k.encode(t, add_special_tokens=False).ids)
    report = {"n": len(items), "methods": {}, "translation_ratio": {}}
    for name, tk in toks.items():
        en = sum(len(tk.encode(it["english"], add_special_tokens=False).ids) for it in items)
        hi = sum(len(tk.encode(it["hinglish"], add_special_tokens=False).ids) for it in items)
        report["translation_ratio"][name] = {"english_over_hinglish_tokens": round(en / hi, 4)}
    examples = defaultdict(list)
    for m, f in methods.items():
        for lang in ("english", "hinglish"):
            kept = tot = s_ok = s_all = q_ok = 0
            for it in items:
                t = it[lang]
                c = f(t)
                kept += n_o200k(c)
                tot += n_o200k(t)
                sl = it[f"slots_{lang}"]
                oks = [slot_kept(s, c) for s in sl]
                s_ok += sum(oks)
                s_all += len(oks)
                q_ok += all(oks)
                if not all(oks) and len(examples[(m, lang)]) < 3:
                    examples[(m, lang)].append({"orig": t, "comp": c, "lost": [" ".join(s) for s, o in zip(sl, oks) if not o]})
            report["methods"][f"{m}|{lang}"] = {"kept_o200k": round(kept / tot, 4), "slots_kept": round(s_ok / s_all, 4),
                                                "queries_all_slots_kept": round(q_ok / len(items), 4)}
            o = report["methods"][f"{m}|{lang}"]
            print(f"{m:18} {lang:8} kept={o['kept_o200k']:.3f} slots={o['slots_kept']:.3f} all={o['queries_all_slots_kept']:.3f}", flush=True)
    report["tokopt_merges"] = {"old": len(tok_old.best), "safe": len(tok_safe.best), "safe_rejected_by_context": len(tok_safe.rejected)}
    report["examples"] = {f"{m}|{l}": v for (m, l), v in examples.items()}
    print("translation ratio (EN/HI tokens):", report["translation_ratio"])
    print("tokopt merges:", report["tokopt_merges"])
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run"])
    ap.add_argument("--n", type=int, default=2000)
    a = ap.parse_args()
    build(a.n) if a.cmd == "build" else run()
