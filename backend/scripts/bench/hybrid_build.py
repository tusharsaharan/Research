"""Build coarse-to-fine hybrid variants (hybrid.py) for code-mixed Belebele and queue them.

Variants per item and language (tag hi/en): {tag}:hybrid-{s-heavy|t-heavy}@{0.5|0.33}, plus
the single-stage references at 0.33 that Belebele did not have yet: {tag}:sentsel@0.33 and
{tag}:guarded@0.33 / {tag}:guarded@0.5 for English (Hinglish guarded@0.7 / llmlingua2 exist).

    python hybrid_build.py build     # -> belebele/hybrid.jsonl (CPU)
    python hybrid_build.py export    # -> kaggle/prompts.jsonl (and kaggle-7b if --tag -7b)
"""

from __future__ import annotations

import argparse
import json

NL = chr(10)
import sys

from belebele_cm import OUT, mcq
from common import BENCH, read_jsonl
from hybrid import SPLITS, hybrid


GRID = {0.5: (0.55, 0.65, 0.75, 0.9), 0.33: (0.37, 0.5, 0.7, 0.85)}  # extra sentence shares


def build_grid() -> None:
    """Extra budget splits (hybrid-s{share}@{target}) for learning the split on a dev set."""
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter

    items = read_jsonl(OUT / "items.jsonl")
    enc, tc, lingua = _encoder(), TokenCounter(), get_compressor()
    with (OUT / "hybrid_grid.jsonl").open("w", encoding="utf-8") as fh:
        for n, it in enumerate(items):
            row = {"id": it["id"], "variants": {}}
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                p, q = it[lang]["passage"], it[lang]["question"]
                for target, shares in GRID.items():
                    for s in shares:
                        row["variants"][f"{tag}:hybrid-s{s}@{target}"] = hybrid(p, q, target, s, enc, tc.count, lingua)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(n, flush=True)
    print("done ->", OUT / "hybrid_grid.jsonl", flush=True)


def build() -> None:
    from belebele_extra import sentsel
    from gateway.modules.m2_compressor.guarded import compress_guarded
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter

    items = read_jsonl(OUT / "items.jsonl")
    enc, tc, lingua = _encoder(), TokenCounter(), get_compressor()
    with (OUT / "hybrid.jsonl").open("w", encoding="utf-8") as fh:
        for n, it in enumerate(items):
            row = {"id": it["id"], "variants": {}}
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                p, q = it[lang]["passage"], it[lang]["question"]
                for target, splits in SPLITS.items():
                    for name, s in splits.items():
                        row["variants"][f"{tag}:hybrid-{name}@{target}"] = hybrid(p, q, target, s, enc, tc.count, lingua)
                row["variants"][f"{tag}:sentsel@0.33"] = sentsel(p, q, 0.33, enc, tc.count)
                for r in (0.5, 0.33):
                    row["variants"][f"{tag}:guarded@{r}"] = compress_guarded(p, r, lingua) or p
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(n, flush=True)
    print("done ->", OUT / "hybrid.jsonl", flush=True)


def build_graded() -> None:
    """Relevance-graded variants (hybrid.graded): graded{spread}@{target}."""
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter
    from hybrid import graded

    items = read_jsonl(OUT / "items.jsonl")
    enc, tc, lingua = _encoder(), TokenCounter(), get_compressor()
    with (OUT / "hybrid_graded.jsonl").open("w", encoding="utf-8") as fh:
        for n, it in enumerate(items):
            row = {"id": it["id"], "variants": {}}
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                p, q = it[lang]["passage"], it[lang]["question"]
                for t in (0.5, 0.33):
                    for sp in (0.6, 1.0):
                        row["variants"][f"{tag}:graded{sp}@{t}"] = graded(p, q, t, enc, tc.count, lingua, spread=sp)
            fh.write(json.dumps(row, ensure_ascii=False) + NL)
            if n % 100 == 0:
                print(n, flush=True)
    print("done ->", OUT / "hybrid_graded.jsonl", flush=True)


def build_graded2(shard: str) -> None:
    """Hinglish-focused round: stronger grading and lexical-weighted relevance. Sharded (i/n)."""
    from common import in_shard
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.modules.m4_router.certified import _encoder
    from gateway.tokenizer import TokenCounter
    from hybrid import graded

    items = [it for it in read_jsonl(OUT / "items.jsonl") if in_shard(it["id"], shard)]
    enc, tc, lingua = _encoder(), TokenCounter(), get_compressor()
    with (OUT / f"graded2.{shard.replace('/', 'of')}.jsonl").open("w", encoding="utf-8") as fh:
        for it in items:
            row = {"id": it["id"], "variants": {}}
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                p, q = it[lang]["passage"], it[lang]["question"]
                for t in (0.5, 0.33):
                    for sp, lw in ((1.5, 0.5), (2.0, 0.5), (1.0, 0.8), (1.5, 0.8)):
                        name = f"{tag}:graded{sp}" + ("-lex" if lw > 0.5 else "") + f"@{t}"
                        row["variants"][name] = graded(p, q, t, enc, tc.count, lingua, spread=sp, lexw=lw)
            fh.write(json.dumps(row, ensure_ascii=False) + NL)
    print("done", shard, flush=True)


def export(tag: str, src: str = "hybrid.jsonl") -> None:
    from collect import SYSTEM

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    kfile = BENCH / f"kaggle{tag}" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for x in [r for f in sorted(OUT.glob(src)) for r in read_jsonl(f)]:
            it = items[x["id"]]
            for m, passage in x["variants"].items():
                lang = "hinglish" if m.startswith("hi:") else "english"
                key = f"{x['id']}|{lang}|{m}"
                if key in have:
                    continue
                q = it[lang]
                fh.write(json.dumps({"key": key, "item_id": x["id"], "lang": lang, "methods": [m], "task": "mcq",
                                     "system": SYSTEM["mcq"], "prompt": mcq(passage, q["question"], q["options"])},
                                    ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} prompts -> {kfile}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "build-grid", "build-graded", "build-graded2", "export", "export-grid", "export-graded", "export-graded2"])
    ap.add_argument("--tag", default="")
    ap.add_argument("--shard", default="1/1")
    a = ap.parse_args()
    {"build": build, "build-grid": build_grid, "export": lambda: export(a.tag),
     "export-grid": lambda: export(a.tag, "hybrid_grid.jsonl"),
     "build-graded": build_graded, "build-graded2": lambda: build_graded2(a.shard),
     "export-graded2": lambda: export(a.tag, "graded2.*.jsonl"), "export-graded": lambda: export(a.tag, "hybrid_graded.jsonl")}[a.cmd]()
