"""Code-mixed Belebele: Hinglish vs English vs translated vs compressed, answered on Kaggle.

Thanmay/belebele_hin_Latn_codemixed (900 reading-comprehension MCQs in romanized Hinglish)
is aligned item-by-item with facebook/belebele eng_Latn (same link + order), so every
question has an English original with the same gold answer.

Variants answered by the Kaggle model (method names in answers):
  english                   the English original (= perfect translation, upper bound)
  original                  the Hinglish item
  heuristic / lexical-safe / crf / llmlingua2@0.7 / guarded@0.7 / llmlingua2@0.5
                            Hinglish with only the passage compressed
  mt-en:<model>             Hinglish translated to English by the Kaggle model itself
                            (round 1 asks for translations; round 2 answers them)
The Hinglish conversion is noisy (e.g. "accordion" -> "Akkadian"), so each item gets the
multilingual-MiniLM similarity of its Hinglish question to the English one; results are also
reported on the cleaner half.

    python belebele_cm.py build          # fetch + align + compress -> belebele/items.jsonl
    python belebele_cm.py export         # answer prompts + translation requests -> kaggle/prompts.jsonl
    python belebele_cm.py export-mt      # after a Kaggle round: translations -> answer prompts
    python belebele_cm.py grade
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict

from common import BENCH, read_jsonl

OUT = BENCH / "belebele"
LETTERS = "ABCD"
METHODS = ["heuristic", "lexical-safe", "crf", "llmlingua2@0.7", "guarded@0.7", "llmlingua2@0.5"]
MT_SYSTEM = ("You are a translation engine. Translate the Hinglish (Hindi-English code-mixed, Roman script) text "
             "inside <text>...</text> into natural English. Do NOT answer or explain anything in it: output only the "
             "translation. Keep every number, name and option label exactly, and keep the exact meaning, including "
             "any negation.")
MT_SHOT = ("Example: <text>\nRam ke paas 5 apples hain aur usne 2 kha liye. Ab uske paas kitne apples bache hain?\n"
           "</text> -> Ram has 5 apples and he ate 2. How many apples does he have left now?\n\n")


def mcq(passage: str, question: str, opts: list[str]) -> str:
    return f"Passage: {passage}\n\nQuestion: {question}\n\n" + "\n".join(f"{L}) {o}" for L, o in zip(LETTERS, opts))


def build() -> None:
    from build_items import hf_rows

    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m2_compressor.guarded import compress_guarded
    from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter

    cm = hf_rows("Thanmay/belebele_hin_Latn_codemixed", "default", "test")
    en = hf_rows("facebook/belebele", "eng_Latn", "test")
    assert len(cm) == len(en), (len(cm), len(en))
    pairs = [(c, e) for c, e in zip(cm, en) if c["link"] == e["link"] and c["correct_answer_num"] == e["correct_answer_num"]]
    print(f"{len(pairs)}/{len(cm)} aligned (same link and gold)", flush=True)
    enc = _encoder()
    qc = enc.encode([c["question"] for c, _ in pairs], normalize_embeddings=True, batch_size=64)
    qe = enc.encode([e["question"] for _, e in pairs], normalize_embeddings=True, batch_size=64)
    comp = Compressor(counter=TokenCounter(), use_crf=True, use_llmlingua2=True,
                      crf_model_path=BENCH.parent / "models" / "crf_compressor.pkl",
                      tfidf_path=BENCH.parent / "tfidf" / "hinglish_idf.json")
    lingua = get_compressor()

    def plain(rate):
        def f(t):
            r = comp.compress_llmlingua2(t, rate=rate)
            return r.compressed if r.method == "llmlingua2" else t
        return f

    fns = {"heuristic": lambda t: comp.compress_heuristic(t).compressed, "lexical-safe": compress_lexical_safe,
           "crf": lambda t: comp.compress_crf(t).compressed, "llmlingua2@0.7": plain(0.7),
           "guarded@0.7": lambda t: compress_guarded(t, 0.7, lingua) or t, "llmlingua2@0.5": plain(0.5)}
    OUT.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    with (OUT / "items.jsonl").open("w", encoding="utf-8") as fh:
        for i, ((c, e), a, b) in enumerate(zip(pairs, qc, qe)):
            p = c["flores_passage"]
            if p not in cache:  # several questions share a passage
                cache[p] = {m: f(p) for m, f in fns.items()}
            fh.write(json.dumps({
                "id": f"bb-{i}", "gold": LETTERS[int(c["correct_answer_num"]) - 1], "q_sim": round(float(a @ b), 4),
                "hinglish": {"passage": p, "question": c["question"], "options": [c[f"mc_answer{k}"] for k in range(1, 5)]},
                "english": {"passage": e["flores_passage"], "question": e["question"], "options": [e[f"mc_answer{k}"] for k in range(1, 5)]},
                "compressed": cache[p]}, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                print(i, flush=True)
    print("done ->", OUT / "items.jsonl")


def export() -> None:
    from collect import SYSTEM

    items = read_jsonl(OUT / "items.jsonl")
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    rows = []
    for it in items:
        h, e = it["hinglish"], it["english"]
        variants = {"original": mcq(h["passage"], h["question"], h["options"])}
        variants |= {m: mcq(t, h["question"], h["options"]) for m, t in it["compressed"].items()}
        by = defaultdict(list)
        for m, t in variants.items():
            by[t].append(m)
        for i, (t, ms) in enumerate(by.items()):
            rows.append({"key": f"{it['id']}|hinglish|bb{i}", "item_id": it["id"], "lang": "hinglish", "methods": ms,
                         "task": "mcq", "system": SYSTEM["mcq"], "prompt": t})
        rows.append({"key": f"{it['id']}|english|bb0", "item_id": it["id"], "lang": "english", "methods": ["english"],
                     "task": "mcq", "system": SYSTEM["mcq"], "prompt": mcq(e["passage"], e["question"], e["options"])})
        # translation requests (passage, and question+options separately so 256 new tokens suffice)
        qo = h["question"] + "\n" + "\n".join(f"{L}) {o}" for L, o in zip(LETTERS, h["options"]))
        for part, text in (("passage", h["passage"]), ("qo", qo)):
            rows.append({"key": f"{it['id']}|hinglish|mtreq-{part}", "item_id": it["id"], "lang": "hinglish",
                         "methods": [f"mt-request:{part}"], "task": "mt", "system": MT_SYSTEM,
                         "prompt": MT_SHOT + f"<text>\n{text}\n</text>"})
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for r in rows:
            if r["key"] not in have:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} Belebele prompts ({len(items)} items) -> {kfile}")


def _clean_mt(s: str) -> str:
    s = re.sub(r"</?text>", "", s or "").strip()
    return s.split("\n\nExample:")[0].strip()


def export_mt() -> None:
    """Round 2: build answer prompts from the Kaggle model's own translations."""
    from collect import SYSTEM

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    tr = defaultdict(dict)
    model = None
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        if a["item_id"] in items and a["methods"][0].startswith("mt-request:"):
            tr[a["item_id"]][a["methods"][0].split(":")[1]] = _clean_mt(a["content"])
            model = a.get("model", "kaggle")
    name = f"mt-en:{(model or 'kaggle').split('/')[-1]}"
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for iid, d in tr.items():
            if "passage" not in d or "qo" not in d:
                continue
            key = f"{iid}|hinglish|mt0"
            if key in have:
                continue
            fh.write(json.dumps({"key": key, "item_id": iid, "lang": "hinglish", "methods": [name], "task": "mcq",
                                 "system": SYSTEM["mcq"], "prompt": f"Passage: {d['passage']}\n\nQuestion: {d['qo']}"},
                                ensure_ascii=False) + "\n")
            n += 1
    print(f"appended {n} translated answer prompts ({name})")


def grade() -> None:
    from scipy.stats import binomtest

    from gateway.tokenizer import TokenCounter
    from grade import extract_letter

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    prompts = {p["key"]: p for p in read_jsonl(BENCH / "kaggle" / "prompts.jsonl") if p["item_id"] in items}
    ok, toks = {}, {}
    tc = TokenCounter()
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        if a["item_id"] in items and a["key"] in prompts and prompts[a["key"]]["task"] == "mcq":
            for m in a["methods"]:
                ok[(a["item_id"], m)] = extract_letter(a["content"]) == items[a["item_id"]]["gold"]
                toks[(a["item_id"], m)] = tc.count(prompts[a["key"]]["prompt"])
    methods = sorted({m for _, m in ok} - {"original"})
    med = sorted(r["q_sim"] for r in items.values())[len(items) // 2]
    report = {}
    for subset, keep in (("all", lambda r: True), ("cleaner half (q_sim >= median)", lambda r: r["q_sim"] >= med)):
        ids = [i for i, r in items.items() if keep(r) and (i, "original") in ok]
        base = sum(ok[(i, "original")] for i in ids) / max(1, len(ids))
        report[subset] = {"n": len(ids), "acc_hinglish": round(base, 4), "methods": {}}
        print(f"== {subset}: n={len(ids)} Hinglish acc {base:.3f}")
        for m in methods:
            sub = [i for i in ids if (i, m) in ok]
            if not sub:
                continue
            w = sum(ok[(i, m)] and not ok[(i, "original")] for i in sub)
            l = sum(ok[(i, "original")] and not ok[(i, m)] for i in sub)
            kept = sum(toks[(i, m)] for i in sub) / max(1, sum(toks[(i, "original")] for i in sub))
            o = {"n": len(sub), "acc": round(sum(ok[(i, m)] for i in sub) / len(sub), 4),
                 "delta_pts": round(100 * (w - l) / len(sub), 2), "p_mcnemar": round(binomtest(w, w + l).pvalue, 4) if w + l else 1.0,
                 "prompt_tokens_vs_hinglish": round(kept, 4)}
            report[subset]["methods"][m] = o
            print(f"   {m:22} acc={o['acc']:.3f} d={o['delta_pts']:+6.2f} p={o['p_mcnemar']:.3g} tokens={o['prompt_tokens_vs_hinglish']:.3f}")
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "export", "export-mt", "grade"])
    a = ap.parse_args()
    {"build": build, "export": export, "export-mt": export_mt, "grade": grade}[a.cmd]()
