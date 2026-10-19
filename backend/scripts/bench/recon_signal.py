"""Reconstruction surprisal as a per-prompt meaning-loss signal.

Idea (cf. 2503.19114, which judges information preservation by reconstructing the
original from the compressed form): if a small LM can predict the original prompt well
from the compressed one, little meaning was lost. Signal per (item, method):
    recon = mean NLL of the original's tokens given "Compressed: <c>\\nOriginal: "
          - the same quantity with the original itself in place of <c> (copy baseline)
computed with Qwen2.5-0.5B-Instruct (local, CPU). Higher = more information lost.

Runs on certification items only (all Hinglish, a seeded sample of English), sharded:
    python recon_signal.py --shard 1/3 --n-english 700
    python recon_signal.py --eval          # AUROC vs the other signals -> recon_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

import numpy as np
from common import BENCH, in_shard, read_jsonl

OUT = BENCH / "recon"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
PREFIX = "Below is a shortened version of a text, followed by the full original text.\nShortened: "


def selected(n_english: int) -> set[tuple[str, str]]:
    cert = {(r["item_id"], r["lang"]) for r in read_jsonl(BENCH / "meaning_pairs.jsonl") if r["split"] == "cert"}
    en = sorted(k for k in cert if k[1] == "english")
    hi = sorted(k for k in cert if k[1] == "hinglish")
    return set(random.Random(20261019).sample(en, min(n_english, len(en)))) | set(hi)


def run(shard: str | None, n_english: int) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from meaning_signals import load_pairs

    n_sh = int(shard.split("/")[1]) if shard else 1
    torch.set_num_threads(max(1, (os.cpu_count() or 1) // n_sh))
    tok = AutoTokenizer.from_pretrained(MODEL)
    lm = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).eval()
    keep = selected(n_english)
    pairs = [r for r in load_pairs() if (r["item_id"], r["lang"]) in keep and in_shard(r["item_id"], shard)]
    jobs = {}
    for r in pairs:
        jobs[(r["item_id"], r["lang"], "original")] = (r["orig"], r["orig"])
        jobs[(r["item_id"], r["lang"], r["method"])] = (r["comp"], r["orig"])
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"recon.{shard.replace('/', 'of') if shard else 'all'}.jsonl"
    done = {(x["item_id"], x["lang"], x["method"]) for x in read_jsonl(path)} if path.exists() else set()
    todo = [(k, v) for k, v in sorted(jobs.items()) if k not in done]
    print(len(todo), "to score", flush=True)
    with path.open("a", encoding="utf-8") as fh:
        for (iid, lang, m), (comp, orig) in todo:
            a = tok(PREFIX + comp + "\nOriginal: ", add_special_tokens=False)["input_ids"]
            b = tok(orig, add_special_tokens=False)["input_ids"]
            ids = torch.tensor([a + b])
            with torch.no_grad():
                logits = lm(ids).logits[0, len(a) - 1:-1].float()
            nll = torch.nn.functional.cross_entropy(logits, ids[0, len(a):], reduction="mean").item()
            fh.write(json.dumps({"item_id": iid, "lang": lang, "method": m, "nll": round(nll, 5)}) + "\n")
            fh.flush()
    print("done", flush=True)


def load_recon() -> dict[tuple, float]:
    """(item, lang, method) -> nll(comp) - nll(copy baseline)."""
    raw = {}
    for f in OUT.glob("recon.*.jsonl"):
        for x in read_jsonl(f):
            raw[(x["item_id"], x["lang"], x["method"])] = x["nll"]
    out = {}
    for (iid, lang, m), v in raw.items():
        base = raw.get((iid, lang, "original"))
        if m != "original" and base is not None:
            out[(iid, lang, m)] = v - base
    return out


def evaluate() -> None:
    from sklearn.metrics import roc_auc_score

    rec = load_recon()
    rows = [r for r in read_jsonl(BENCH / "meaning_pairs.jsonl") if (r["item_id"], r["lang"], r["method"]) in rec]
    report = {"n_pairs": len(rows)}
    for lang in ("english", "hinglish"):
        sub = [r for r in rows if r["lang"] == lang]
        for tgt in ("changed", "broke"):
            y = [r[tgt] for r in sub]
            for name, s in (("recon", [rec[(r["item_id"], lang, r["method"])] for r in sub]),
                            ("1-cosine", [1 - r["cosine"] for r in sub]),
                            ("1-kept_words", [1 - r["kept_words"] for r in sub]),
                            ("learned_risk", [r[f"risk_{tgt}"] for r in sub])):
                report[f"{lang}|{tgt}|{name}"] = round(float(roc_auc_score(y, s)), 4) if 0 < sum(y) < len(y) else None
            # does recon add information beyond how much was deleted? AUROC within kept-ratio terciles
            kw = np.array([r["kept_words"] for r in sub])
            for q, (lo, hi) in enumerate(zip(np.quantile(kw, [0, 1 / 3, 2 / 3]), np.quantile(kw, [1 / 3, 2 / 3, 1.0001]))):
                idx = [i for i, v in enumerate(kw) if lo <= v < hi]
                yy = [y[i] for i in idx]
                if 0 < sum(yy) < len(yy):
                    report[f"{lang}|{tgt}|recon within kept-tercile {q + 1}"] = round(float(roc_auc_score(
                        yy, [rec[(sub[i]["item_id"], lang, sub[i]["method"])] for i in idx])), 4)
                    report[f"{lang}|{tgt}|1-cosine within kept-tercile {q + 1}"] = round(float(roc_auc_score(
                        yy, [1 - sub[i]["cosine"] for i in idx])), 4)
    (BENCH / "recon_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k, v in report.items():
        print(f"{k:55} {v}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default=None)
    ap.add_argument("--n-english", type=int, default=700)
    ap.add_argument("--eval", action="store_true")
    a = ap.parse_args()
    evaluate() if a.eval else run(a.shard, a.n_english)
