"""Negation stress test: prompt compression on CondaQA (Ravichander et al., EMNLP 2022).

CondaQA questions can only be answered by understanding a negation cue in the
passage (lexical "not"/"never" or affixal "un-"/"-less"), and each passage has
an affirmative edit with the cue removed, so a compressor that drops the cue
should push answers towards the affirmative answer.

Only the passage is compressed; the question is kept verbatim.

    python condaqa.py build                   # test split -> data/bench/condaqa/items.jsonl
    python condaqa.py compress --shard 1/3    # resumable, one process per shard
    python condaqa.py export                  # append prompts to kaggle/prompts.jsonl (runner picks them up)
    python condaqa.py grade                   # answers -> condaqa/report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import BENCH, in_shard, read_jsonl

OUT = BENCH / "condaqa"
EDIT_NAMES = {0: "original", 1: "paraphrase", 2: "scope", 3: "affirmative"}
SYSTEM = ("Read the passage and answer the question with YES, NO, or DON'T KNOW. You may think briefly. "
          "End your reply with a final line of the form '#### <answer>' where <answer> is YES, NO or DON'T KNOW.")
RATES = (0.5, 0.7)
METHODS = ["heuristic", "lexical-stop", "lexical-safe",
           *[f"{m}@{r}" for r in RATES for m in ("llmlingua2", "guarded", "guarded+affix")]]
_LEXICAL_CUES = {"not", "no", "never", "nothing", "none", "nobody", "nowhere", "neither", "nor", "without",
                 "cannot", "n't"}


def cue_kind(cue: str) -> str:
    c = cue.lower().strip()
    return "lexical" if c in _LEXICAL_CUES or c.endswith("n't") else "affixal/other"


def build() -> None:
    from build_items import hf_rows

    rows = hf_rows("lasha-nlp/CONDAQA", "default", "test")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "items.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"id": f"cq-{r['QuestionID']}-{r['PassageID']}-{r['PassageEditID']}",
                                 "passage_id": r["PassageID"], "question_id": r["QuestionID"],
                                 "edit": EDIT_NAMES.get(r["PassageEditID"], str(r["PassageEditID"])),
                                 "cue": r["original cue"], "cue_kind": cue_kind(r["original cue"]),
                                 "passage": r["sentence1"], "question": r["sentence2"], "label": r["label"]},
                                ensure_ascii=False) + "\n")
    print(len(rows), "rows;", dict(Counter(EDIT_NAMES.get(r["PassageEditID"]) for r in rows)),
          dict(Counter(r["label"] for r in rows)))


# ---- affix-aware guard (extension): protect "unX", "disX", "Xless", ... when X is itself a word.
_PREFIX = re.compile(r"^(un|in|im|ir|il|dis|non|non-)([a-z]{4,})$")
_SUFFIX = re.compile(r"^([a-z]{3,})less$")


def affix_negations(text: str, vocab: set[str]) -> list[str]:
    out = []
    for w in re.findall(r"[A-Za-z-]+", text):
        lw = w.lower()
        m = _PREFIX.match(lw)
        if (m and m[2] in vocab) or ((s := _SUFFIX.match(lw)) and s[1] in vocab):
            out.append(w)
    return out


def compress(shard: str | None) -> None:
    import torch

    from gateway.modules.m2_compressor import guarded as G
    from gateway.modules.m2_compressor import lexical_safe as L
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.tokenizer import TokenCounter

    n_shards = int(shard.split("/")[1]) if shard else 1
    torch.set_num_threads(max(1, (os.cpu_count() or 1) // n_shards))
    items = [r for r in read_jsonl(OUT / "items.jsonl") if r["edit"] == "original"]
    passages = {r["passage_id"]: r["passage"] for r in items}  # compress each passage once
    vocab = {w.lower() for r in read_jsonl(OUT / "items.jsonl") for w in re.findall(r"[A-Za-z]+", r["passage"])}
    comp = Compressor(counter=TokenCounter(), use_crf=False, use_llmlingua2=True)
    lingua = get_compressor()
    base_guard = G._guard_words

    def lexical_stop(t: str) -> str:  # 2609.13154 without the negation/wh exemption
        keep = L.DELETE
        L.DELETE = L.NLTK_STOP | L.HINGLISH_FILLERS
        try:
            return L.compress_lexical_safe(t)
        finally:
            L.DELETE = keep

    def plain(rate):
        def f(t):
            r = comp.compress_llmlingua2(t, rate=rate)
            return r.compressed if r.method == "llmlingua2" else t
        return f

    def guarded(rate, affix=False):
        def f(t):
            G._guard_words = (lambda s: sorted(set(base_guard(s)) | set(affix_negations(s, vocab)))) if affix else base_guard
            try:
                return G.compress_guarded(t, rate, lingua) or t
            finally:
                G._guard_words = base_guard
        return f

    fns = {"heuristic": lambda t: comp.compress_heuristic(t).compressed, "lexical-stop": lexical_stop,
           "lexical-safe": L.compress_lexical_safe}
    for r in RATES:
        fns |= {f"llmlingua2@{r}": plain(r), f"guarded@{r}": guarded(r), f"guarded+affix@{r}": guarded(r, True)}

    tag = shard.replace("/", "of") if shard else "all"
    path = OUT / f"compressed.{tag}.jsonl"
    done = {(x["passage_id"], x["method"]) for x in read_jsonl(path)} if path.exists() else set()
    with path.open("a", encoding="utf-8") as fh:
        for pid, text in sorted(passages.items()):
            if not in_shard(str(pid), shard):
                continue
            for m, f in fns.items():
                if (pid, m) in done:
                    continue
                out = f(text)
                fh.write(json.dumps({"passage_id": pid, "method": m, "text": out,
                                     "tok_before": comp.counter.count(text), "tok_after": comp.counter.count(out)},
                                    ensure_ascii=False) + "\n")
            fh.flush()
    print("done", tag)


def compressed() -> dict[tuple, dict]:
    out = {}
    for f in sorted(OUT.glob("compressed.*.jsonl")):
        for r in read_jsonl(f):
            out[(r["passage_id"], r["method"])] = r
    return out


def prompt(passage: str, question: str) -> str:
    return f"Passage: {passage}\n\nQuestion: {question}"


def export() -> None:
    items = read_jsonl(OUT / "items.jsonl")
    comp = compressed()
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for it in items:
            variants = {"original": it["passage"]}
            if it["edit"] == "original":
                variants |= {m: comp[(it["passage_id"], m)]["text"] for m in METHODS if (it["passage_id"], m) in comp}
            by_text: dict[str, list[str]] = defaultdict(list)
            for m, t in variants.items():
                by_text[t].append(m)
            for i, (t, ms) in enumerate(by_text.items()):
                key = f"{it['id']}|english|cq{i}"
                if key in have:
                    continue
                fh.write(json.dumps({"key": key, "item_id": it["id"], "lang": "english", "methods": ms,
                                     "task": "condaqa", "system": SYSTEM, "prompt": prompt(t, it["question"])},
                                    ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} CondaQA prompts -> {kfile}")


def parse(reply: str) -> str | None:
    tail = reply.rsplit("####", 1)[-1] if "####" in reply else reply[-80:]
    t = tail.upper().replace("’", "'")
    for lab in ("DON'T KNOW", "DONT KNOW", "YES", "NO"):
        if lab in t:
            return "DON'T KNOW" if "KNOW" in lab else lab
    return None


def grade(answers=None) -> None:
    from scipy.stats import binomtest

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    pred: dict[tuple, str | None] = {}
    for a in read_jsonl(Path(answers) if answers else BENCH / "kaggle" / "answers.jsonl"):
        if a["item_id"] in items:
            for m in a["methods"]:
                pred[(a["item_id"], m)] = parse(a.get("content") or "")
    comp = compressed()
    # affirmative-edit label for the same question (what a model that ignored the cue would say)
    aff = {(r["passage_id"], r["question_id"]): r["label"] for r in items.values() if r["edit"] == "affirmative"}
    orig = [r for r in items.values() if r["edit"] == "original" and (r["id"], "original") in pred]
    report = {"n_original_answered": len(orig),
              "acc_by_edit": {e: _acc([r for r in items.values() if r["edit"] == e], pred, "original")
                              for e in EDIT_NAMES.values()}}
    for kind in ("all", "lexical", "affixal/other"):
        sub = [r for r in orig if kind == "all" or r["cue_kind"] == kind]
        base = _acc(sub, pred, "original")
        rows = {}
        for m in METHODS:
            both = [r for r in sub if (r["id"], m) in pred]
            if not both:
                continue
            a = [pred[(r["id"], "original")] == r["label"] for r in both]
            b = [pred[(r["id"], m)] == r["label"] for r in both]
            lost, gained = sum(x and not y for x, y in zip(a, b)), sum(y and not x for x, y in zip(a, b))
            p = binomtest(lost, lost + gained).pvalue if lost + gained else 1.0
            flip = [r for r in both if (r["passage_id"], r["question_id"]) in aff
                    and aff[(r["passage_id"], r["question_id"])] != r["label"]]
            to_aff = sum(pred[(r["id"], m)] == aff[(r["passage_id"], r["question_id"])]
                         and pred[(r["id"], "original")] != pred[(r["id"], m)] for r in flip)
            cue_lost = [r for r in both if (r["passage_id"], m) in comp
                        and r["cue"].lower() not in comp[(r["passage_id"], m)]["text"].lower()]
            toks = [comp[(r["passage_id"], m)] for r in both if (r["passage_id"], m) in comp]
            rows[m] = {"n": len(both), "acc": round(sum(b) / len(b), 4), "delta_pts": round(100 * (sum(b) - sum(a)) / len(b), 2),
                       "p_mcnemar": round(p, 4), "kept_tokens": round(sum(t["tok_after"] for t in toks) / max(1, sum(t["tok_before"] for t in toks)), 4),
                       "cue_dropped": round(len(cue_lost) / len(both), 4),
                       "switched_to_affirmative_answer": round(to_aff / max(1, len(flip)), 4)}
        report[kind] = {"n": len(sub), "acc_original": base, "methods": rows}
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("answered originals:", len(orig), "| acc by edit:", report["acc_by_edit"])
    for kind in ("all", "lexical", "affixal/other"):
        print(f"--- {kind} n={report[kind]['n']} base={report[kind]['acc_original']}")
        for m, o in report[kind]["methods"].items():
            print(f"{m:20} kept={o['kept_tokens']:.3f} acc={o['acc']:.3f} d={o['delta_pts']:+6.2f} p={o['p_mcnemar']:.3g} "
                  f"cue_drop={o['cue_dropped']:.3f} to_aff={o['switched_to_affirmative_answer']:.3f}")


def _acc(rows, pred, m):
    got = [pred[(r["id"], m)] == r["label"] for r in rows if (r["id"], m) in pred]
    return round(sum(got) / len(got), 4) if got else None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "compress", "export", "grade"])
    ap.add_argument("--shard", default=None)
    ap.add_argument("--answers", default=None, help="answers file (default: kaggle/answers.jsonl)")
    a = ap.parse_args()
    {"build": build, "export": export, "grade": lambda: grade(a.answers)}.get(a.cmd, lambda: compress(a.shard))()
