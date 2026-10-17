"""Export gold-answer prompts (original + every compressed version) for local-model
answering on a Kaggle/Colab GPU. Output is one self-contained JSONL — upload it
as a Kaggle dataset; the notebook needs nothing else from the repo.

Each row: key (item|lang|method), item_id, lang, method, task, system, prompt.
Identical prompt texts are kept once per (item, lang) with a list of methods,
so unchanged compressions cost nothing.

    python backend/scripts/bench/kaggle_prepare.py            # all methods present in compress_rows*
    python backend/scripts/bench/kaggle_prepare.py --methods crf+tokopt[o200k],guarded2@0.5,llmlingua2+spans@0.5
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict

from collect import SYSTEM
from common import BENCH, latest_variants, read_jsonl, variant_ok

OUT_DIR = BENCH / "kaggle"
DEFAULT_METHODS = ["crf+tokopt[o200k]", "heuristic",
                   "llmlingua2+spans@0.3", "llmlingua2+spans@0.4", "llmlingua2+spans@0.5",
                   "llmlingua2+spans@0.6", "llmlingua2+spans@0.7", "llmlingua2+spans@0.8",
                   "guarded2@0.4", "guarded2@0.5", "guarded2@0.6", "guarded2@0.7", "guarded2@0.8"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    args = ap.parse_args()
    want = set(args.methods.split(","))

    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    originals: dict[tuple, str] = {(i, "english"): r["question_en"] for i, r in items.items()}
    for v in latest_variants():
        if v["lang"] == "hinglish" and variant_ok(v):
            originals[(v["item_id"], "hinglish")] = v["text"]

    texts: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))  # (item, lang) -> text -> methods
    for key, t in originals.items():
        texts[key][t].append("original")
    found = defaultdict(int)
    for f in sorted(glob.glob(str(BENCH / "compress_rows*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["method"] not in want or r["source"] == "hinglish-instruct":
                continue
            item_id, suffix = r["pid"].rsplit("/", 1)
            key = (item_id, "english" if suffix == "en" else "hinglish")
            if key not in originals:
                continue
            t = r["compressed"] if r["changed"] and r.get("compressed") else originals[key]
            if r["method"] not in texts[key][t]:
                texts[key][t].append(r["method"])
                found[r["method"]] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "prompts.jsonl"
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for (item_id, lang), by_text in sorted(texts.items()):
            task = items[item_id].get("task", "math")
            for t, methods in by_text.items():
                fh.write(json.dumps({"key": f"{item_id}|{lang}|{n}", "item_id": item_id, "lang": lang,
                                     "methods": methods, "task": task, "system": SYSTEM[task], "prompt": t},
                                    ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} unique prompts -> {out}")
    print("method coverage (item-languages):", dict(sorted(found.items())))
    missing = sorted(want - set(found))
    if missing:
        print("not found in compress_rows yet (run them first):", missing)


if __name__ == "__main__":
    main()
