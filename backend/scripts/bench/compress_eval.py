"""Compression benchmark: every compressor on ~8,000 prompts, no API calls.

Prompts (deduplicated, seeded):
  - English gold items (GSM8K, ARC-Challenge, MMLU sample) from items.jsonl
  - their romanized-Hinglish versions that passed the automatic checks
  - real romanized-Hinglish user prompts (Hinglish-Instruct, 10,378), sampled to fill 8,000

Compressors: heuristic (filler pruning), crf (CRF linguistic compressor),
tokopt (tokenizer-aware spelling normalisation, new; one per tokenizer),
crf+tokopt. Tokenizers: Qwen2.5 (byte-level BPE, LLM-style), XLM-R
(multilingual SentencePiece) and English BERT WordPiece — all offline.

Per (prompt, method): tokens before/after per tokenizer, and whether meaning-
carrying units survive: numbers, negations (nahi/mat/not...), question words
(kya/kaun/what...), multiple-choice option labels, Hindi postpositions.

    python backend/scripts/bench/compress_eval.py --n 8000
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path

from common import BACKEND, BENCH, latest_variants, read_jsonl, variant_ok
from tokenizers import Tokenizer
from tokopt import TokOptNormalizer

from gateway.modules.m1_pipeline.hinglish import language_group
from gateway.modules.m2_compressor.compressor import Compressor
from gateway.tokenizer import TokenCounter

HF = Path.home() / ".cache" / "huggingface" / "hub"
TOKENIZERS = {
    "qwen2.5": "models--Qwen--Qwen2.5-0.5B-Instruct",
    "xlmr": "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2",
    "bert-en": "models--sentence-transformers--all-MiniLM-L6-v2",
}
HINGLISH_INSTRUCT = BACKEND / "experiments" / "cascade_routing" / "data" / "prompts.csv"
OUT_ROWS = BENCH / "compress_rows.jsonl"
OUT_SUMMARY = BENCH / "compress_summary.json"

# Strict negations only. "na" is excluded: in Hinglish it is mostly a softener
# ("batao na", "sun na"), and "nai" also means "new"; both are reported apart.
NEG = {"nahi", "nahin", "nhi", "mat", "not", "never", "no", "nothing", "none", "neither", "nor",
       "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "won't", "can't", "cannot"}
QW = {"kya", "kyaa", "kaun", "kon", "kab", "kahan", "kidhar", "kaise", "kyun", "kyu", "kitna", "kitne", "kitni",
      "konsa", "kaunsa", "what", "who", "whom", "when", "where", "why", "how", "which"}
PARTICLE_NA = {"na"}
POSTP = {"ka", "ki", "ke", "ko", "se", "mein", "me", "par", "pe", "tak", "liye"}
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
# Option labels anywhere in order (compressors may join lines; inline "A) .. B) .." is fine).
_OPT = re.compile(r"(?<![A-Za-z])([A-H])\)")


def load_tokenizers() -> dict[str, Tokenizer]:
    out = {}
    for name, repo in TOKENIZERS.items():
        files = glob.glob(str(HF / repo / "snapshots" / "*" / "tokenizer.json"))
        if files:
            t = Tokenizer.from_file(files[0])
            t.no_padding()
            t.no_truncation()
            out[name] = t
    return out


def words(text: str) -> list[str]:
    return [w.strip(",.!?;:\"'()[]{}").lower() for w in text.split()]


def count_set(text: str, vocab: set[str]) -> int:
    return sum(w in vocab for w in words(text))


def build_prompts(n: int, seed: int) -> list[dict]:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    prompts = [{"pid": f"{i}/en", "text": r["question_en"], "source": r["source"].split("/")[0],
                "lang": "english", "task": r.get("task", "math")} for i, r in items.items()]
    for v in latest_variants():
        if v["lang"] == "hinglish" and variant_ok(v):
            r = items[v["item_id"]]
            prompts.append({"pid": f"{v['item_id']}/hi", "text": v["text"], "source": r["source"].split("/")[0],
                            "lang": "hinglish", "task": r.get("task", "math")})
    seen = {p["text"] for p in prompts}
    with HINGLISH_INSTRUCT.open(encoding="utf-8-sig") as fh:
        hi = [row["prompt"].strip() for row in csv.DictReader(fh) if row.get("prompt", "").strip()]
    hi = [t for t in dict.fromkeys(hi) if t not in seen and len(t.split()) >= 4]
    random.Random(seed).shuffle(hi)
    for k, t in enumerate(hi[: max(0, n - len(prompts))]):
        prompts.append({"pid": f"hinglish-instruct-{k:05d}", "text": t, "source": "hinglish-instruct",
                        "lang": language_group(t), "task": "open"})
    return prompts[:n] if len(prompts) > n else prompts


def survive(orig: str, comp: str) -> dict:
    o_num, c_num = _NUM.findall(orig), _NUM.findall(comp)
    return {
        "numbers_kept": sorted(o_num) == sorted(c_num) if o_num else None,
        "neg_in": count_set(orig, NEG), "neg_out": count_set(comp, NEG),
        "qw_in": count_set(orig, QW), "qw_out": count_set(comp, QW),
        "postp_in": count_set(orig, POSTP), "postp_out": count_set(comp, POSTP),
        "na_in": count_set(orig, PARTICLE_NA), "na_out": count_set(comp, PARTICLE_NA),
        "options_kept": (_OPT.findall(orig) == _OPT.findall(comp)) if _OPT.search(orig) else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=20261016)
    args = ap.parse_args()

    toks = load_tokenizers()
    prompts = build_prompts(args.n, args.seed)
    # TokOpt vocabularies are learned from the Hinglish-Instruct corpus only (not the evaluated gold items).
    with HINGLISH_INSTRUCT.open(encoding="utf-8-sig") as fh:
        corpus = [row["prompt"] for row in csv.DictReader(fh)]
    english = [p["text"] for p in prompts if p["lang"] == "english" and p["source"] != "hinglish-instruct"]
    norms = {name: TokOptNormalizer(t, corpus, english) for name, t in toks.items() if name != "bert-en"}

    comp = Compressor(counter=TokenCounter(), use_crf=True,
                      crf_model_path=BACKEND / "data" / "models" / "crf_compressor.pkl",
                      tfidf_path=BACKEND / "data" / "tfidf" / "hinglish_idf.json")
    methods = {
        "heuristic": lambda t: comp.compress_heuristic(t).compressed,
        "crf": lambda t: comp.compress_crf(t).compressed,
        **{f"tokopt[{n}]": (lambda t, f=f: f(t)) for n, f in norms.items()},
        **{f"crf+tokopt[{n}]": (lambda t, f=f: f(comp.compress_crf(t).compressed)) for n, f in norms.items()},
    }
    crf_live = comp.compress_crf(prompts[0]["text"]).method == "crf"
    print(f"{len(prompts)} prompts | tokenizers {list(toks)} | crf model loaded: {crf_live}")
    print("tokopt rewrite rules:", {n: len(f.best) for n, f in norms.items()})

    def ntok(text: str) -> dict:
        return {n: len(t.encode(text, add_special_tokens=False).ids) for n, t in toks.items()}

    OUT_ROWS.write_text("", encoding="utf-8")
    agg: dict = defaultdict(lambda: defaultdict(float))
    with OUT_ROWS.open("a", encoding="utf-8") as fh:
        for i, p in enumerate(prompts, 1):
            base = ntok(p["text"])
            for m, fn in methods.items():
                t0 = time.perf_counter()
                out = fn(p["text"])
                ms = (time.perf_counter() - t0) * 1000
                after = ntok(out)
                s = survive(p["text"], out)
                row = {**{k: p[k] for k in ("pid", "source", "lang", "task")}, "method": m, "ms": round(ms, 2),
                       "tokens_before": base, "tokens_after": after, "changed": out != p["text"], **s}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                for key in (f"{p['source']}|{p['lang']}|{m}", f"ALL|{p['lang']}|{m}"):
                    a = agg[key]
                    a["n"] += 1
                    a["changed"] += row["changed"]
                    a["ms"] += ms
                    for tn in toks:
                        a[f"before_{tn}"] += base[tn]
                        a[f"after_{tn}"] += after[tn]
                    if s["numbers_kept"] is not None:
                        a["num_n"] += 1
                        a["num_ok"] += s["numbers_kept"]
                    if s["options_kept"] is not None:
                        a["opt_n"] += 1
                        a["opt_ok"] += s["options_kept"]
                    for unit in ("neg", "qw", "postp", "na"):
                        if s[f"{unit}_in"]:
                            a[f"{unit}_prompts"] += 1
                            a[f"{unit}_lost_prompts"] += s[f"{unit}_out"] < s[f"{unit}_in"]
                            a[f"{unit}_in"] += s[f"{unit}_in"]
                            a[f"{unit}_out"] += min(s[f"{unit}_out"], s[f"{unit}_in"])
            if i % 1000 == 0:
                print(f"  {i}/{len(prompts)}")

    summary = {}
    for key, a in sorted(agg.items()):
        src, lang, m = key.split("|")
        n = a["n"]
        r = {"source": src, "lang": lang, "method": m, "n": int(n), "changed_share": round(a["changed"] / n, 4),
             "ms_mean": round(a["ms"] / n, 2)}
        for tn in toks:
            r[f"kept_ratio_{tn}"] = round(a[f"after_{tn}"] / max(a[f"before_{tn}"], 1), 4)
        r["numbers_kept_rate"] = round(a["num_ok"] / a["num_n"], 4) if a["num_n"] else None
        r["options_kept_rate"] = round(a["opt_ok"] / a["opt_n"], 4) if a["opt_n"] else None
        for unit in ("neg", "qw", "postp", "na"):
            pn = a[f"{unit}_prompts"]
            r[f"{unit}_prompts"] = int(pn)
            r[f"{unit}_loss_rate"] = round(a[f"{unit}_lost_prompts"] / pn, 4) if pn else None
        summary[key] = r
    OUT_SUMMARY.write_text(json.dumps({"n_prompts": len(prompts), "tokenizers": list(toks), "crf_model_loaded": crf_live,
                                       "tokopt_rules": {n: len(f.best) for n, f in norms.items()},
                                       "rows": summary}, indent=2), encoding="utf-8")

    print(f"\n{'lang':9} {'method':22} {'n':>5} {'chg':>5} {'qwen':>6} {'xlmr':>6} {'bert':>6} {'num':>6} {'opt':>6} {'negLost':>7} {'qwLost':>7}")
    for key, r in summary.items():
        if not key.startswith("ALL|"):
            continue
        f = lambda v: "  -  " if v is None else f"{v:.3f}"  # noqa: E731
        print(f"{r['lang']:9} {r['method']:22} {r['n']:>5} {r['changed_share']:.2f} {r.get('kept_ratio_qwen2.5', 0):>6.3f} "
              f"{r.get('kept_ratio_xlmr', 0):>6.3f} {r.get('kept_ratio_bert-en', 0):>6.3f} {f(r['numbers_kept_rate']):>6} "
              f"{f(r['options_kept_rate']):>6} {f(r['neg_loss_rate']):>7} {f(r['qw_loss_rate']):>7}")
    print("summary ->", OUT_SUMMARY)


if __name__ == "__main__":
    main()
