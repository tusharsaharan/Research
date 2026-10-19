"""Deletion vs sentence selection vs abstractive rewriting, Hinglish and English (code-mixed Belebele).

Adds to the Belebele test (belebele_cm.py) three families at matched budgets, for BOTH the
Hinglish passage and its English original:
  llmlingua2@r          token deletion (LLMLingua-2 multilingual), baseline
  sentsel@r             query-aware sentence selection (CPC 2409.01227 / PC-SubMax 2609.32474
                        style): greedy facility-location coverage of the passage + relevance to
                        the question, whole sentences only, original order, until r of the tokens
  rewrite:<model>       abstractive rewrite by a small LLM in the SAME language (Cmprsr
                        2511.12281 / SCOPE 2508.15813 / Telegraph English 2605.04426 idea):
                        Kaggle round 1 writes the rewrite, round 2 answers it
Method names carry the language: "hi:" / "en:"; baselines are "original" (Hinglish) and
"english".

    python belebele_extra.py build        # CPU: sentsel + English llmlingua2 -> belebele/extra.jsonl
    python belebele_extra.py export       # answer prompts + rewrite requests -> kaggle/prompts.jsonl
    python belebele_extra.py export-rw    # after a Kaggle round: rewrites -> answer prompts
    python belebele_extra.py grade
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict

import numpy as np
from belebele_cm import LETTERS, OUT, mcq
from common import BENCH, read_jsonl

RATES = (0.7, 0.5)
RW_SYSTEM = ("Rewrite the text inside <text>...</text> as briefly as possible in the SAME language and style "
             "(Hinglish stays Hinglish, English stays English). Keep every fact, number, name, date and negation "
             "that a reader could be asked about; drop only repetition and filler. Do not add, answer or explain "
             "anything. Output only the rewritten text.")
_SENT = re.compile(r"(?<=[.!?।])\s+")


_STOP = {"the", "a", "an", "of", "to", "in", "is", "was", "and", "or", "ke", "ki", "ka", "ko", "se", "mein", "me",
         "hai", "hain", "tha", "thi", "the", "par", "kya", "kaun", "kis", "kiske", "which", "what", "who", "whose", "passage",
         "according"}


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 2 and w not in _STOP}


def sentsel(passage: str, question: str, rate: float, enc, count) -> str:
    sents = [s for s in _SENT.split(passage.strip()) if s]
    if len(sents) <= 1:
        return passage
    e = enc.encode(sents + [question], normalize_embeddings=True, show_progress_bar=False)
    S, q = e[:-1], e[-1]
    sim = S @ S.T
    qw = _words(question)
    lex = np.array([len(qw & _words(t)) / max(1, len(qw)) for t in sents])  # word overlap: works for romanized text
    rel = 0.5 * (S @ q) + 0.5 * lex
    budget = rate * count(passage)
    chosen, cover, used = [], np.zeros(len(sents)), 0
    while True:
        best, gain = None, -1e9
        for i in range(len(sents)):
            if i in chosen or used + count(sents[i]) > budget:
                continue
            g = np.maximum(cover, sim[i]).sum() - cover.sum() + len(sents) * 0.5 * rel[i]
            g /= max(1, count(sents[i])) ** 0.5  # prefer short informative sentences
            if g > gain:
                best, gain = i, g
        if best is None:
            break
        chosen.append(best)
        cover = np.maximum(cover, sim[best])
        used += count(sents[best])
    if not chosen:  # budget below the shortest sentence: keep the most relevant one
        chosen = [int(np.argmax(rel))]
    return " ".join(sents[i] for i in sorted(chosen))


def build() -> None:
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter

    items = read_jsonl(OUT / "items.jsonl")
    enc = _encoder()
    tc = TokenCounter()
    comp = Compressor(counter=tc, use_crf=False, use_llmlingua2=True)

    def plain(t, r):
        x = comp.compress_llmlingua2(t, rate=r)
        return x.compressed if x.method == "llmlingua2" else t

    cache: dict = {}
    with (OUT / "extra.jsonl").open("w", encoding="utf-8") as fh:
        for n, it in enumerate(items):
            row = {"id": it["id"], "variants": {}}
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                p, q = it[lang]["passage"], it[lang]["question"]
                for r in RATES:
                    row["variants"][f"{tag}:sentsel@{r}"] = sentsel(p, q, r, enc, tc.count)
                    if tag == "en":
                        key = (p, r)
                        if key not in cache:
                            cache[key] = plain(p, r)
                        row["variants"][f"en:llmlingua2@{r}"] = cache[key]
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if n % 150 == 0:
                print(n, flush=True)
    print("done ->", OUT / "extra.jsonl", flush=True)


def export() -> None:
    from collect import SYSTEM

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    rows, seen_pass = [], set()
    for x in read_jsonl(OUT / "extra.jsonl"):
        it = items[x["id"]]
        for m, passage in x["variants"].items():
            lang = "hinglish" if m.startswith("hi:") else "english"
            src = it[lang]
            rows.append({"key": f"{x['id']}|{lang}|{m}", "item_id": x["id"], "lang": lang, "methods": [m], "task": "mcq",
                         "system": SYSTEM["mcq"], "prompt": mcq(passage, src["question"], src["options"])})
        for lang, tag in (("hinglish", "hi"), ("english", "en")):
            p = it[lang]["passage"]
            if (lang, p) in seen_pass:  # passages are shared by several questions: rewrite once
                continue
            seen_pass.add((lang, p))
            rows.append({"key": f"{x['id']}|{lang}|rwreq", "item_id": x["id"], "lang": lang, "methods": [f"rw-request:{tag}"],
                         "task": "rewrite", "system": RW_SYSTEM, "prompt": f"<text>\n{p}\n</text>"})
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for r in rows:
            if r["key"] not in have:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} prompts -> {kfile}")


def export_rw() -> None:
    from collect import SYSTEM

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    rw, model = {}, "kaggle"
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        if a["item_id"] in items and a["methods"][0].startswith("rw-request:"):
            lang = "hinglish" if a["methods"][0].endswith("hi") else "english"
            text = re.sub(r"</?text>", "", a["content"] or "").strip()
            rw[(lang, items[a["item_id"]][lang]["passage"])] = text
            model = a.get("model", model).split("/")[-1]
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for iid, it in items.items():
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                t = rw.get((lang, it[lang]["passage"]))
                key = f"{iid}|{lang}|rw"
                if not t or key in have:
                    continue
                fh.write(json.dumps({"key": key, "item_id": iid, "lang": lang, "methods": [f"{tag}:rewrite:{model}"],
                                     "task": "mcq", "system": SYSTEM["mcq"],
                                     "prompt": mcq(t, it[lang]["question"], it[lang]["options"])}, ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} rewrite answer prompts")


def grade() -> None:
    from scipy.stats import binomtest

    from gateway.tokenizer import TokenCounter
    from grade import extract_letter

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    prompts = {p["key"]: p for p in read_jsonl(BENCH / "kaggle" / "prompts.jsonl") if p["item_id"] in items}
    tc = TokenCounter()
    ok, ptok = {}, {}
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        p = prompts.get(a["key"])
        if p and p["task"] == "mcq":
            for m in a["methods"]:
                ok[(a["item_id"], m)] = extract_letter(a["content"]) == items[a["item_id"]]["gold"]
                passage = p["prompt"].split("\n\nQuestion:")[0].removeprefix("Passage: ")
                ptok[(a["item_id"], m)] = tc.count(passage)
    # Hinglish deletion methods from belebele_cm use plain names; map them to "hi:" here
    alias = {m: f"hi:{m}" for m in ("llmlingua2@0.7", "llmlingua2@0.5", "guarded@0.7", "crf", "heuristic", "lexical-safe")}
    for (i, m), v in list(ok.items()):
        if m in alias:
            ok[(i, alias[m])], ptok[(i, alias[m])] = v, ptok[(i, m)]
    report = {}
    for tag, base in (("hi", "original"), ("en", "english")):
        ids = [i for i in items if (i, base) in ok]
        report[tag] = {"n": len(ids), "acc_base": round(sum(ok[(i, base)] for i in ids) / max(1, len(ids)), 4), "methods": {}}
        print(f"== {tag} base={base} n={len(ids)} acc={report[tag]['acc_base']:.3f}")
        for m in sorted({m for _, m in ok if m.startswith(tag + ":")}):
            sub = [i for i in ids if (i, m) in ok]
            if not sub:
                continue
            w = sum(ok[(i, m)] and not ok[(i, base)] for i in sub)
            l = sum(ok[(i, base)] and not ok[(i, m)] for i in sub)
            kept = sum(ptok[(i, m)] for i in sub) / max(1, sum(ptok[(i, base)] for i in sub))
            o = {"n": len(sub), "passage_tokens_kept": round(kept, 4), "acc": round(sum(ok[(i, m)] for i in sub) / len(sub), 4),
                 "delta_pts": round(100 * (w - l) / len(sub), 2), "p_mcnemar": round(binomtest(w, w + l).pvalue, 4) if w + l else 1.0}
            report[tag]["methods"][m] = o
            print(f"   {m:28} kept={kept:.3f} acc={o['acc']:.3f} d={o['delta_pts']:+6.2f} p={o['p_mcnemar']:.3g}")
    (OUT / "extra_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "export", "export-rw", "grade"])
    a = ap.parse_args()
    {"build": build, "export": export, "export-rw": export_rw, "grade": grade}[a.cmd]()
