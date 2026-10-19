"""Pragmatic-meaning invariance on human Hinglish messages (Yugrathee28/Hinglish-dataset).

Gold labels in this dataset are automatic (label_method strong/weak/fallback), so the
measure is invariance, not accuracy: does a model read the same intent and emotion from the
compressed message as from the original? 75 longer messages with strong-signal labels,
stratified by intent; versions: original, filler pruning, negation-safe stopword removal,
CRF, LLMLingua-2 @0.7 plain and guarded.

    python label_invariance.py build            # sample + compress -> labels/prompts.jsonl
    python api_answer.py --provider gemini --model gemini-3.5-flash-lite --prompts ../../data/bench/labels/prompts.jsonl
    python label_invariance.py grade --answers ../../data/bench/api/gemini-3.5-flash-lite.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import BENCH, read_jsonl

OUT = BENCH / "labels"
INTENTS = ["Question", "Request", "Appreciation", "Criticism", "Complaint", "Humor", "Suggestion", "Neutral"]
EMOTIONS = ["Neutral", "Happy", "Curious", "Frustrated", "Sad", "Humor", "Fear", "Surprised", "Angry", "Disgusted"]
SYSTEM = ("Classify the Hinglish (Hindi-English) message. Reply with exactly one line: "
          f"intent=<one of {', '.join(INTENTS)}>; emotion=<one of {', '.join(EMOTIONS)}>")
METHODS = ["heuristic", "lexical-safe", "crf", "llmlingua2@0.7", "guarded@0.7"]


def build(n: int) -> None:
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m2_compressor.guarded import compress_guarded
    from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.tokenizer import TokenCounter

    rows = [r for r in read_jsonl(OUT / "all.jsonl")
            if r["label_method"] == "strong_signal" and len(r["text"].split()) >= 12 and r["intent"] in INTENTS]
    by = defaultdict(list)
    for r in rows:
        by[r["intent"]].append(r)
    rng = random.Random(20261019)
    pick = []
    for intent in sorted(by, key=lambda k: len(by[k])):  # rare intents first, round-robin up to n
        rng.shuffle(by[intent])
    while len(pick) < n and any(by.values()):
        for intent in list(by):
            if by[intent] and len(pick) < n:
                pick.append(by[intent].pop())
    comp = Compressor(counter=TokenCounter(), use_crf=True, use_llmlingua2=True,
                      crf_model_path=BENCH.parent / "models" / "crf_compressor.pkl",
                      tfidf_path=BENCH.parent / "tfidf" / "hinglish_idf.json")
    lingua = get_compressor()

    def plain(t):
        r = comp.compress_llmlingua2(t, rate=0.7)
        return r.compressed if r.method == "llmlingua2" else t

    fns = {"heuristic": lambda t: comp.compress_heuristic(t).compressed, "lexical-safe": compress_lexical_safe,
           "crf": lambda t: comp.compress_crf(t).compressed, "llmlingua2@0.7": plain,
           "guarded@0.7": lambda t: compress_guarded(t, 0.7, lingua) or t}
    OUT.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with (OUT / "items.jsonl").open("w", encoding="utf-8") as fi, (OUT / "prompts.jsonl").open("w", encoding="utf-8") as fp:
        for r in pick:
            iid = f"lbl-{r['id']}"
            fi.write(json.dumps({"id": iid, "text": r["text"], "intent": r["intent"], "emotion": r["emotion"]}, ensure_ascii=False) + "\n")
            variants = {"original": r["text"]} | {m: f(r["text"]) for m, f in fns.items()}
            by_text = defaultdict(list)
            for m, t in variants.items():
                by_text[t].append(m)
            for i, (t, ms) in enumerate(by_text.items()):
                fp.write(json.dumps({"key": f"{iid}|hinglish|lb{i}", "item_id": iid, "lang": "hinglish", "methods": ms,
                                     "task": "labels", "system": SYSTEM, "prompt": t}, ensure_ascii=False) + "\n")
                n_rows += 1
    print(len(pick), "messages;", n_rows, "unique prompts ->", OUT / "prompts.jsonl")


def parse(reply: str) -> tuple[str | None, str | None]:
    m1 = re.search(r"intent\s*=\s*([A-Za-z]+)", reply or "")
    m2 = re.search(r"emotion\s*=\s*([A-Za-z]+)", reply or "")
    norm = lambda x, opts: next((o for o in opts if x and o.lower() == x.lower()), None)
    return norm(m1 and m1[1], INTENTS), norm(m2 and m2[1], EMOTIONS)


def grade(answers: str) -> None:
    from gateway.tokenizer import TokenCounter

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    texts = {}
    for p in read_jsonl(OUT / "prompts.jsonl") + (read_jsonl(OUT / "repeat.jsonl") if (OUT / "repeat.jsonl").exists() else []):
        for m in p["methods"]:
            texts[(p["item_id"], m)] = p["prompt"]
    pred = {}
    for a in read_jsonl(Path(answers)):
        if a["item_id"] in items:
            for m in a["methods"]:
                pred[(a["item_id"], m)] = parse(a.get("content", ""))
    tc = TokenCounter()
    ids = [i for i in items if (i, "original") in pred and None not in pred[(i, "original")]]
    report = {"n_messages": len(ids),
              "original_vs_gold": {"intent": round(sum(pred[(i, "original")][0] == items[i]["intent"] for i in ids) / max(1, len(ids)), 4),
                                   "emotion": round(sum(pred[(i, "original")][1] == items[i]["emotion"] for i in ids) / max(1, len(ids)), 4)}}
    for m in ["original-repeat"] + METHODS:  # original-repeat = same prompt asked again (noise floor)
        sub = [i for i in ids if (i, m) in pred]
        changed_text = [i for i in sub if texts[(i, m)] != items[i]["text"] or m == "original-repeat"]
        kept = sum(tc.count(texts[(i, m)]) for i in sub) / max(1, sum(tc.count(items[i]["text"]) for i in sub))
        report[m] = {"n": len(sub), "text_changed": len(changed_text), "kept_tokens": round(kept, 4),
                     "intent_same": round(sum(pred[(i, m)][0] == pred[(i, "original")][0] for i in sub) / max(1, len(sub)), 4),
                     "emotion_same": round(sum(pred[(i, m)][1] == pred[(i, "original")][1] for i in sub) / max(1, len(sub)), 4),
                     "both_same_on_changed_texts": round(sum(pred[(i, m)] == pred[(i, "original")] for i in changed_text)
                                                         / max(1, len(changed_text)), 4)}
        o = report[m]
        print(f"{m:16} n={o['n']} changed={o['text_changed']} kept={o['kept_tokens']:.3f} intent_same={o['intent_same']:.3f} "
              f"emotion_same={o['emotion_same']:.3f} both_same(changed)={o['both_same_on_changed_texts']:.3f}")
    print("original vs gold:", report["original_vs_gold"])
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "grade"])
    ap.add_argument("--n", type=int, default=75)
    ap.add_argument("--answers", default=str(BENCH / "api" / "gemini-3.5-flash-lite.jsonl"))
    a = ap.parse_args()
    build(a.n) if a.cmd == "build" else grade(a.answers)
