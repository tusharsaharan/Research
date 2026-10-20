"""Learn the coarse/fine budget split per language on a dev split, report on held-out test.

Belebele items are split once by a hash of the item id (dev 1/3, test 2/3). For each language
and target budget (0.5, 0.33) the candidates are: token-only (guarded@t), sentence-only
(sentsel@t), and every hybrid split (hybrid-s-heavy / t-heavy / s{share}). The split with the
best dev accuracy is evaluated on test against the single-stage baselines with exact McNemar
(paired, same test items). Also reports the oracle (best on test) to show selection loss.

    python hybrid_select.py            # 3B answers (kaggle/)
    KAGGLE_TAG=-7b python hybrid_select.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import defaultdict

from belebele_cm import OUT
from common import BENCH, read_jsonl
from grade import extract_letter
from scipy.stats import binomtest

TAG = os.environ.get("KAGGLE_TAG", "")
K = BENCH / f"kaggle{TAG}"


def split(item_id: str) -> str:
    h = int(hashlib.sha256(f"hybrid-dev|{item_id}".encode()).hexdigest(), 16) % 3
    return "dev" if h == 0 else "test"


def main() -> None:
    from gateway.tokenizer import TokenCounter

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    prompts = {p["key"]: p for p in read_jsonl(K / "prompts.jsonl") if p["item_id"] in items and p["task"] == "mcq"}
    tc = TokenCounter()
    ok, kept = {}, defaultdict(list)
    base_tok = {}
    for it in items.values():
        for lang in ("hinglish", "english"):
            base_tok[(it["id"], lang)] = tc.count(it[lang]["passage"])
    alias = {"llmlingua2@0.5": "hi:llmlingua2@0.5", "llmlingua2@0.7": "hi:llmlingua2@0.7", "guarded@0.7": "hi:guarded@0.7",
             "original": "hi:none", "english": "en:none"}
    for a in read_jsonl(K / "answers.jsonl"):
        p = prompts.get(a["key"])
        if not p:
            continue
        for m in a["methods"]:
            m = alias.get(m, m)
            if not m.startswith(("hi:", "en:")):
                continue
            ok[(a["item_id"], m)] = extract_letter(a["content"]) == items[a["item_id"]]["gold"]
            lang = "hinglish" if m.startswith("hi:") else "english"
            passage = p["prompt"].split("\n\nQuestion:")[0].removeprefix("Passage: ")
            kept[m].append(tc.count(passage) / max(1, base_tok[(a["item_id"], lang)]))
    acc = lambda ids, m: sum(ok[(i, m)] for i in ids) / len(ids)
    report = {}
    for tag in ("hi", "en"):
        for t in (0.5, 0.33):
            cands = [m for m in {m for _, m in ok if m.startswith(tag + ":")}
                     if m.endswith(f"@{t}") and ("hybrid" in m or "guarded" in m or "sentsel" in m)]
            ids_all = [i for i in items if all((i, m) in ok for m in cands + [f"{tag}:none"])]
            dev = [i for i in ids_all if split(i) == "dev"]
            test = [i for i in ids_all if split(i) == "test"]
            if not cands or not dev or not test:
                continue
            best = max(cands, key=lambda m: acc(dev, m))
            oracle = max(cands, key=lambda m: acc(test, m))
            row = {"n_dev": len(dev), "n_test": len(test), "selected_on_dev": best, "oracle_on_test": oracle,
                   "test_acc_uncompressed": round(acc(test, f"{tag}:none"), 4), "candidates": {}}
            for m in sorted(cands):
                w = sum(ok[(i, best)] and not ok[(i, m)] for i in test)
                l = sum(ok[(i, m)] and not ok[(i, best)] for i in test)
                row["candidates"][m] = {"kept": round(sum(kept[m]) / len(kept[m]), 4), "dev_acc": round(acc(dev, m), 4),
                                        "test_acc": round(acc(test, m), 4),
                                        "selected_minus_this_pts": round(100 * (w - l) / len(test), 2),
                                        "p": round(binomtest(w, w + l).pvalue, 4) if w + l else 1.0}
            report[f"{tag}@{t}"] = row
            print(f"== {tag} target {t}: dev {len(dev)} test {len(test)}  uncompressed test acc {row['test_acc_uncompressed']:.3f}"
                  f"  -> selected {best}")
            for m, o in sorted(row["candidates"].items(), key=lambda kv: -kv[1]["test_acc"]):
                print(f"   {m:30} kept={o['kept']:.3f} dev={o['dev_acc']:.3f} test={o['test_acc']:.3f} "
                      f"sel-this={o['selected_minus_this_pts']:+.1f} p={o['p']:.3g}")
    (OUT / f"hybrid_select{TAG}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
