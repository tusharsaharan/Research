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
import sys

from belebele_cm import OUT, mcq
from common import BENCH, read_jsonl
from hybrid import SPLITS, hybrid


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


def export(tag: str) -> None:
    from collect import SYSTEM

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    kfile = BENCH / f"kaggle{tag}" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for x in read_jsonl(OUT / "hybrid.jsonl"):
            it = items[x["id"]]
            for m, passage in x["variants"].items():
                lang = "hinglish" if m.startswith("hi:") else "english"
                key = f"{x['id']}|{lang}|{m}"
                if key in have:
                    continue
                src = it[lang]
                fh.write(json.dumps({"key": key, "item_id": x["id"], "lang": lang, "methods": [m], "task": "mcq",
                                     "system": SYSTEM["mcq"], "prompt": mcq(passage, src["question"], src["options"])},
                                    ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} prompts -> {kfile}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "export"])
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    build() if a.cmd == "build" else export(a.tag)
