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


class _TiktokenShim:
    """tiktoken behind the tokenizers.Tokenizer interface used here (.encode(...).ids)."""

    class _Enc:
        def __init__(self, ids):
            self.ids = ids

    def __init__(self, name: str) -> None:
        import tiktoken

        self._e = tiktoken.get_encoding(name)

    def encode(self, text: str, add_special_tokens: bool = False):
        return self._Enc(self._e.encode(text, disallowed_special=()))


def load_tokenizers() -> dict[str, Tokenizer]:
    out = {}
    try:  # gpt-oss / GPT-4o family tokenizer: the serving models' own token counts
        out["o200k"] = _TiktokenShim("o200k_base")
    except Exception:
        pass
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


_LETTER = re.compile(r"(?<![A-Za-z])([A-H])(?:\)|\s)")


def _digits(t: str) -> str:
    """All digits in order. Equal digit sequences = numbers only reformatted
    ('$ 5. 50', '10, 440, 000'), not deleted or changed."""
    return "".join(re.findall(r"\d", t))


def _in_order(labels: list[str], seen: list[str]) -> bool:
    """All option labels appear in order (other capital letters in between are fine)."""
    it = iter(seen)
    return all(lab in it for lab in labels)


def survive(orig: str, comp: str) -> dict:
    o_num, c_num = _NUM.findall(orig), _NUM.findall(comp)
    labels = _OPT.findall(orig)
    return {
        "numbers_kept": sorted(o_num) == sorted(c_num) if o_num else None,
        # same digits in the same order: reformatted at most, not deleted
        "numbers_present": _digits(orig) == _digits(comp) if o_num else None,
        # option letters still present in order, even without the ")" (A amount ... B distance ...)
        "option_letters_kept": _in_order(labels, _LETTER.findall(comp + " ")) if labels else None,
        "neg_in": count_set(orig, NEG), "neg_out": count_set(comp, NEG),
        "qw_in": count_set(orig, QW), "qw_out": count_set(comp, QW),
        "postp_in": count_set(orig, POSTP), "postp_out": count_set(comp, POSTP),
        "na_in": count_set(orig, PARTICLE_NA), "na_out": count_set(comp, PARTICLE_NA),
        "options_kept": (_OPT.findall(orig) == _OPT.findall(comp)) if _OPT.search(orig) else None,
    }


def add(agg: dict, row: dict, toks) -> None:
    s, m = row, row["method"]
    for key in (f"{row['source']}|{row['lang']}|{m}", f"ALL|{row['lang']}|{m}"):
        a = agg[key]
        a["n"] += 1
        a["changed"] += row["changed"]
        a["ms"] += row["ms"]
        for tn in toks:
            a[f"before_{tn}"] += row["tokens_before"][tn]
            a[f"after_{tn}"] += row["tokens_after"][tn]
        if s["numbers_kept"] is not None:
            a["num_n"] += 1
            a["num_ok"] += s["numbers_kept"]
        if s["options_kept"] is not None:
            a["opt_n"] += 1
            a["opt_ok"] += s["options_kept"]
            a["optl_ok"] += s["option_letters_kept"]
        if s["numbers_present"] is not None:
            a["nump_ok"] += s["numbers_present"]
        for unit in ("neg", "qw", "postp", "na"):
            if s[f"{unit}_in"]:
                a[f"{unit}_prompts"] += 1
                a[f"{unit}_lost_prompts"] += s[f"{unit}_out"] < s[f"{unit}_in"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=20261016)
    ap.add_argument("--llmlingua", action="store_true", help="add LLMLingua-2 (bert-base multilingual) at keep-rates 0.7 and 0.5; ~1 h on CPU")
    ap.add_argument("--shard", default=None, help="i/n: process every n-th prompt (run n processes in parallel)")
    ap.add_argument("--methods", default=None, help="comma list: run only these methods")
    ap.add_argument("--tag", default="", help="row-file tag so new runs don't overwrite old shards")
    ap.add_argument("--summarize", action="store_true", help="only rebuild the summary from all row files")
    ap.add_argument("--threads", type=int, default=0,
                    help="torch threads per process (0 = cores / shards, avoids oversubscription)")
    args = ap.parse_args()
    import os

    import torch

    n_shards = int(args.shard.split("/")[1]) if args.shard else 1
    torch.set_num_threads(args.threads or max(1, (os.cpu_count() or 1) // n_shards))

    toks = load_tokenizers()
    if args.summarize:
        agg: dict = defaultdict(lambda: defaultdict(float))
        files = sorted(BENCH.glob("compress_rows.*shard*.jsonl")) or [OUT_ROWS]
        n_prompts = set()
        seen_rows: set = set()
        texts = {p["pid"]: p["text"] for p in build_prompts(args.n, args.seed)}
        for f in files:
            for line in f.open(encoding="utf-8"):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue  # partial line from an interrupted run
                if (row["pid"], row["method"]) in seen_rows:
                    continue  # duplicate from overlapping runs
                seen_rows.add((row["pid"], row["method"]))
                orig = texts.get(row["pid"])
                if orig is not None:  # recompute checks with the current metric code
                    row |= survive(orig, row["compressed"] if row["changed"] else orig)
                n_prompts.add(row["pid"])
                add(agg, row, toks)
        return write_summary(agg, toks, len(n_prompts), None, {})
    prompts = build_prompts(args.n, args.seed)
    # TokOpt vocabularies are learned from the Hinglish-Instruct corpus only (not the evaluated gold items).
    with HINGLISH_INSTRUCT.open(encoding="utf-8-sig") as fh:
        corpus = [row["prompt"] for row in csv.DictReader(fh)]
    english = [p["text"] for p in prompts if p["lang"] == "english" and p["source"] != "hinglish-instruct"]
    norms = {name: TokOptNormalizer(t, corpus, english) for name, t in toks.items() if name != "bert-en"}

    comp = Compressor(counter=TokenCounter(), use_crf=True, use_llmlingua2=args.llmlingua,
                      crf_model_path=BACKEND / "data" / "models" / "crf_compressor.pkl",
                      tfidf_path=BACKEND / "data" / "tfidf" / "hinglish_idf.json")
    def lingua(rate: float):
        def f(t: str) -> str:
            r = comp.compress_llmlingua2(t, rate=rate)
            return r.compressed if r.method == "llmlingua2" else t
        return f

    from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe as _lex

    methods = {
        "heuristic": lambda t: comp.compress_heuristic(t).compressed,
        "lexical-safe": _lex,
        "crf": lambda t: comp.compress_crf(t).compressed,
        **{f"tokopt[{n}]": (lambda t, f=f: f(t)) for n, f in norms.items()},
        **{f"crf+tokopt[{n}]": (lambda t, f=f: f(comp.compress_crf(t).compressed)) for n, f in norms.items()},
    }
    if args.llmlingua:
        from gateway.modules.m2_compressor.guarded import compress_guarded
        from gateway.modules.m2_compressor.llmlingua2 import get_compressor

        def guarded(rate: float):
            def f(t: str) -> str:
                out = compress_guarded(t, rate, get_compressor())
                return out if out else t
            return f

        from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe

        methods |= {"lexical-safe+guarded@0.5": (lambda t, g=guarded(0.5): g(compress_lexical_safe(t))),
                    "crf+guarded@0.5": (lambda t, g=guarded(0.5): g(comp.compress_crf(t).compressed))}
        methods |= {"llmlingua2+spans@0.7": lingua(0.7), "llmlingua2+spans@0.5": lingua(0.5),
                    "guarded@0.7": guarded(0.7), "guarded@0.5": guarded(0.5), "guarded@0.4": guarded(0.4),
                    "guarded@0.5+tokopt": (lambda t, g=guarded(0.5), f=norms["o200k"]: f(g(t)))}
        for name in (args.methods or "").split(","):  # any keep-rate on request, e.g. guarded@0.3
            m = re.fullmatch(r"(guarded2?|llmlingua2\+spans)@(0\.\d+)", name)
            if m and name not in methods:
                methods[name] = guarded(float(m[2])) if m[1].startswith("guarded") else lingua(float(m[2]))
    if args.methods:
        keep = set(args.methods.split(","))
        methods = {k: v for k, v in methods.items() if k in keep}
    rows_path = OUT_ROWS
    if args.shard:
        i_s, n_s = (int(x) for x in args.shard.split("/"))
        prompts = prompts[i_s - 1 :: n_s]
        rows_path = BENCH / f"compress_rows.{args.tag + '.' if args.tag else ''}shard{i_s}.jsonl"
    crf_live = comp.compress_crf(prompts[0]["text"]).method == "crf"
    print(f"{len(prompts)} prompts | tokenizers {list(toks)} | crf model loaded: {crf_live}")
    print("tokopt rewrite rules:", {n: len(f.best) for n, f in norms.items()})

    def ntok(text: str) -> dict:
        return {n: len(t.encode(text, add_special_tokens=False).ids) for n, t in toks.items()}

    done: set = set()
    if args.shard and rows_path.exists():  # resume: keep rows from an interrupted run
        for line in rows_path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["pid"], r["method"]))
            except json.JSONDecodeError:
                pass  # half-written last line
        if rows_path.read_bytes()[-1:] not in (b"", b"\n"):
            with rows_path.open("a", encoding="utf-8") as fh0:
                fh0.write("\n")
        print(f"resuming: {len(done)} rows already done")
    else:
        rows_path.write_text("", encoding="utf-8")
    agg: dict = defaultdict(lambda: defaultdict(float))
    with rows_path.open("a", encoding="utf-8") as fh:
        for i, p in enumerate(prompts, 1):
            base = ntok(p["text"])
            for m, fn in methods.items():
                if (p["pid"], m) in done:
                    continue
                t0 = time.perf_counter()
                out = fn(p["text"])
                ms = (time.perf_counter() - t0) * 1000
                after = ntok(out)
                s = survive(p["text"], out)
                row = {**{k: p[k] for k in ("pid", "source", "lang", "task")}, "method": m, "ms": round(ms, 2),
                       "tokens_before": base, "tokens_after": after, "changed": out != p["text"], **s,
                       "compressed": out if out != p["text"] else None}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                add(agg, row, toks)
            if i % 1000 == 0:
                print(f"  {i}/{len(prompts)}")

    if args.shard:
        print("rows ->", rows_path, "(run --summarize after all shards finish)")
        return
    write_summary(agg, toks, len(prompts), crf_live, {n: len(f.best) for n, f in norms.items()})


def write_summary(agg, toks, n_prompts, crf_live, rules) -> None:
    summary = {}
    for key, a in sorted(agg.items()):
        src, lang, m = key.split("|")
        n = a["n"]
        r = {"source": src, "lang": lang, "method": m, "n": int(n), "changed_share": round(a["changed"] / n, 4),
             "ms_mean": round(a["ms"] / n, 2)}
        for tn in toks:
            r[f"kept_ratio_{tn}"] = round(a[f"after_{tn}"] / max(a[f"before_{tn}"], 1), 4)
        r["numbers_kept_rate"] = round(a["num_ok"] / a["num_n"], 4) if a["num_n"] else None
        r["numbers_present_rate"] = round(a["nump_ok"] / a["num_n"], 4) if a["num_n"] else None
        r["options_kept_rate"] = round(a["opt_ok"] / a["opt_n"], 4) if a["opt_n"] else None
        r["option_letters_kept_rate"] = round(a["optl_ok"] / a["opt_n"], 4) if a["opt_n"] else None
        for unit in ("neg", "qw", "postp", "na"):
            pn = a[f"{unit}_prompts"]
            r[f"{unit}_prompts"] = int(pn)
            r[f"{unit}_loss_rate"] = round(a[f"{unit}_lost_prompts"] / pn, 4) if pn else None
        summary[key] = r
    OUT_SUMMARY.write_text(json.dumps({"n_prompts": n_prompts, "tokenizers": list(toks), "crf_model_loaded": crf_live,
                                       "tokopt_rules": rules,
                                       "rows": summary}, indent=2), encoding="utf-8")

    print(f"\n{'lang':9} {'method':22} {'n':>5} {'chg':>5} {'o200k':>6} {'qwen':>6} {'xlmr':>6} {'num':>6} {'opt':>6} {'negLost':>7} {'qwLost':>7}")
    for key, r in summary.items():
        if not key.startswith("ALL|"):
            continue
        f = lambda v: "  -  " if v is None else f"{v:.3f}"  # noqa: E731
        print(f"{r['lang']:9} {r['method']:22} {r['n']:>5} {r['changed_share']:.2f} {r.get('kept_ratio_o200k', 0):>6.3f} "
              f"{r.get('kept_ratio_qwen2.5', 0):>6.3f} {r.get('kept_ratio_xlmr', 0):>6.3f} {f(r['numbers_kept_rate']):>6} "
              f"{f(r['options_kept_rate']):>6} {f(r['neg_loss_rate']):>7} {f(r['qw_loss_rate']):>7}")
    print("summary ->", OUT_SUMMARY)


if __name__ == "__main__":
    main()
