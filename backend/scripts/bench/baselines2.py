"""Stronger baselines for the hybrid claim (reviewer-proofing):
  llml2L@r    LLMLingua-2, XLM-RoBERTa-large checkpoint (the one Microsoft's papers report)
  longllml@r  LongLLMLingua: question-aware coarse-to-fine (llmlingua lib, Qwen2.5-0.5B as the small LM)
  bm25@r      question-aware BM25 sentence retrieval to the budget (classic extractive baseline)
Runs on Belebele (Hinglish + English) and on SQuAD / MeetingBank / HotpotQA contexts, budgets 0.5 and 0.33.

    python baselines2.py build --set belebele --shard 1/3
    python baselines2.py build --set squad|meetingbank|hotpot --shard 1/3
    python baselines2.py export --set ... [--tag=-hp]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from common import BENCH, in_shard, read_jsonl

RATES = (0.5, 0.33)
METHODS = [f"{m}@{r}" for r in RATES for m in ("llml2L", "longllml", "bm25")]
_SENT = re.compile(r"(?<=[.!?।])\s+")
_TOK = re.compile(r"[a-z0-9]+")


def bm25_select(text: str, question: str, rate: float, count) -> str:
    sents = [s for s in _SENT.split(text.strip()) if s] or [text]
    docs = [_TOK.findall(s.lower()) for s in sents]
    q = set(_TOK.findall(question.lower()))
    N, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = Counter(w for d in docs for w in set(d))
    def score(d):
        tf = Counter(d)
        return sum(math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(d) / avg))
                   for w in q if w in tf)
    order = sorted(range(N), key=lambda i: -score(docs[i]))
    budget, used, keep = rate * count(text), 0, []
    for i in order:
        c = count(sents[i])
        if used + c > budget and keep:
            continue
        keep.append(i)
        used += c
    return " ".join(sents[i] for i in sorted(keep))


def chunks(text: str) -> list[str]:
    """Paragraphs for LongLLMLingua's coarse stage; single paragraphs become ~3-sentence chunks."""
    paras = [p for p in text.splitlines() if p.strip()]
    if len(paras) >= 3:
        return paras
    sents = [s for s in _SENT.split(text.strip()) if s] or [text]
    return [" ".join(sents[i:i + 3]) for i in range(0, len(sents), 3)]


class Compressors:
    def __init__(self, methods=("llml2L", "longllml", "bm25")):
        self.methods = set(methods)
        from llmlingua import PromptCompressor

        from gateway.tokenizer import TokenCounter
        self.count = TokenCounter().count
        self.large = PromptCompressor("microsoft/llmlingua-2-xlm-roberta-large-meetingbank", use_llmlingua2=True,
                                      device_map="cpu") if "llml2L" in self.methods else None
        self.long = PromptCompressor("Qwen/Qwen2.5-0.5B-Instruct", device_map="cpu") if "longllml" in self.methods else None
        if self.methods & {"bhybrid", "bgraded"}:
            from gateway.modules.m2_compressor.llmlingua2 import get_compressor
            self.small = get_compressor()

    def run(self, text: str, question: str) -> dict:
        from hybrid import bgraded, bhybrid
        out = {}
        n = self.count(text)
        for r in RATES:
            if "bhybrid" in self.methods:
                out[f"bhybrid@{r}"] = bhybrid(text, question, r, {0.5: 0.7, 0.33: 0.6}[r], self.count, self.small)
            if "bgraded" in self.methods:
                out[f"bgraded@{r}"] = bgraded(text, question, r, self.count, self.small)
            if "longllml" in self.methods:
                try:
                    out[f"longllml2@{r}"] = self.long.compress_prompt(
                        chunks(text), question=question, target_token=int(r * n), rank_method="longllmlingua",
                        condition_in_question="after", condition_compare=True, reorder_context="original",
                        dynamic_context_compression_ratio=0.4, context_budget="+0")["compressed_prompt"]
                except Exception as e:
                    print("longllml failed:", repr(e)[:200], file=sys.stderr, flush=True)
            if not self.methods & {"llml2L", "bm25"}:
                continue
            try:
                out[f"llml2L@{r}"] = self.large.compress_prompt(text, rate=r, force_tokens=["\n", "?", "."])["compressed_prompt"]
            except Exception:
                out[f"llml2L@{r}"] = text
            if "bm25" in self.methods:
                out[f"bm25@{r}"] = bm25_select(text, question, r, self.count)
        return out


def units(name: str):
    """(id, tag, text, question) per compression unit of a set."""
    if name == "belebele":
        for it in read_jsonl(BENCH / "belebele" / "items.jsonl"):
            for lang, tag in (("hinglish", "hi"), ("english", "en")):
                yield it["id"], tag, it[lang]["passage"], it[lang]["question"]
    else:
        d = BENCH / ("hotpot" if name == "hotpot" else f"longqa_{name}")
        for it in read_jsonl(d / "items.jsonl")[: 300 if name == "hotpot" else None]:
            yield it["id"], "", it["context"], it["question"]


def build(name: str, shard: str, methods: list[str], outdir: str) -> None:
    import torch
    torch.set_num_threads(4)
    c = Compressors(methods)
    path = BENCH / outdir / f"{name}.{shard.replace('/', 'of')}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(x["id"], x["tag"]) for x in read_jsonl(path)} if path.exists() else set()
    with path.open("a", encoding="utf-8") as fh:
        for iid, tag, text, q in units(name):
            if (iid, tag) in done or not in_shard(iid, shard):
                continue
            v = c.run(text, q)
            fh.write(json.dumps({"id": iid, "tag": tag, "variants": v,
                                 "kept": {m: c.count(t) / max(1, c.count(text)) for m, t in v.items()}}, ensure_ascii=False) + "\n")
            fh.flush()
    print("done", name, shard, flush=True)


def export(name: str, tag_dir: str, outdir: str = "baselines2") -> None:
    from belebele_cm import mcq
    from collect import SYSTEM
    from hotpot import SYSTEM as HSYS

    kfile = BENCH / f"kaggle{tag_dir}" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    items = {}
    if name == "belebele":
        items = {r["id"]: r for r in read_jsonl(BENCH / "belebele" / "items.jsonl")}
    else:
        d = BENCH / ("hotpot" if name == "hotpot" else f"longqa_{name}")
        items = {r["id"]: r for r in read_jsonl(d / "items.jsonl")}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for f in sorted((BENCH / outdir).glob(f"{name}.*.jsonl")):
            for x in read_jsonl(f):
                it = items[x["id"]]
                for m, t in x["variants"].items():
                    if name == "belebele":
                        lang = "hinglish" if x["tag"] == "hi" else "english"
                        meth, key = f"{x['tag']}:{m}", f"{x['id']}|{lang}|{x['tag']}:{m}"
                        row = {"key": key, "item_id": x["id"], "lang": lang, "methods": [meth], "task": "mcq",
                               "system": SYSTEM["mcq"], "prompt": mcq(t, it[lang]["question"], it[lang]["options"])}
                    else:
                        key = f"{x['id']}|english|b2:{m}"
                        row = {"key": key, "item_id": x["id"], "lang": "english", "methods": [m], "task": "hotpot",
                               "system": HSYS, "prompt": f"Context:\n{t}\n\nQuestion: {it['question']}"}
                    if key not in have:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                        n += 1
    print(f"appended {n} -> {kfile}")


def grade(name: str, answers_path: str | None = None) -> None:
    """Score saved Kaggle answers for the stronger-baseline batch."""
    from scipy.stats import binomtest, wilcoxon

    answers_path = Path(answers_path or BENCH / "kaggle-hp" / "answers.jsonl")
    variants = {}
    for f in sorted((BENCH / "baselines2").glob(f"{name}.*.jsonl")):
        for x in read_jsonl(f):
            for m, kept in x["kept"].items():
                variants[(x["id"], x.get("tag", ""), m)] = kept

    if name == "belebele":
        items = {r["id"]: r for r in read_jsonl(BENCH / "belebele" / "items.jsonl")}
        from grade import extract_letter

        base_names = {"hi": "original", "en": "english"}
        scores = {}
        answer_files = [answers_path]
        main_answers = BENCH / "kaggle" / "answers.jsonl"
        if main_answers != answers_path:
            answer_files.append(main_answers)
        for answer_file in answer_files:
            for a in read_jsonl(answer_file):
                if a.get("model") != "Qwen/Qwen2.5-3B-Instruct":
                    continue
                tag = "hi" if a.get("lang") == "hinglish" else "en"
                for m in a.get("methods", []):
                    if a["item_id"] not in items:
                        continue
                    score_name = m
                    if tag == "hi" and m in ("llmlingua2@0.5", "llmlingua2@0.33"):
                        score_name = "hi:" + m
                    if m == base_names[tag] or m.startswith(tag + ":") or m in ("llmlingua2@0.5", "llmlingua2@0.33"):
                        scores[(a["item_id"], tag, score_name)] = extract_letter(a["content"]) == items[a["item_id"]]["gold"]

        report = {}
        for tag, lang in (("hi", "hinglish"), ("en", "english")):
            base = base_names[tag]
            ids = [i for i in items if (i, tag, base) in scores]
            res = {"n_original": len(ids), "accuracy_original": round(sum(scores[(i, tag, base)] for i in ids) / max(1, len(ids)), 4), "methods": {}}
            for m in METHODS:
                method = f"{tag}:{m}"
                common = [i for i in ids if (i, tag, method) in scores]
                if not common:
                    continue
                wins = sum(scores[(i, tag, method)] and not scores[(i, tag, base)] for i in common)
                losses = sum(scores[(i, tag, base)] and not scores[(i, tag, method)] for i in common)
                kept = sum(variants.get((i, tag, m), 0.0) for i in common) / len(common)
                res["methods"][method] = {
                    "n": len(common), "accuracy": round(sum(scores[(i, tag, method)] for i in common) / len(common), 4),
                    "accuracy_original_paired": round(sum(scores[(i, tag, base)] for i in common) / len(common), 4),
                    "delta_vs_original_pts": round(100 * sum(scores[(i, tag, method)] - scores[(i, tag, base)] for i in common) / len(common), 2),
                    "p_mcnemar": float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0,
                    "context_tokens_kept": round(kept, 4),
                }
            report[lang] = res

        selected = json.loads((BENCH / "belebele" / "hybrid_select.json").read_text(encoding="utf-8"))
        report["heldout_test"] = {}
        for tag, lang in (("hi", "hinglish"), ("en", "english")):
            for rate in (0.5, 0.33):
                split_key = f"{tag}@{rate}"
                hybrid = selected[split_key]["selected_on_dev"]
                test_ids = [i for i in items if int(hashlib.sha256(f"hybrid-dev|{i}".encode()).hexdigest(), 16) % 3 != 0]
                small = next((m for m in (f"{tag}:llmlingua2@{rate}", f"llmlingua2@{rate}")
                              if all((i, tag, m) in scores for i in test_ids)), None)
                split_report = {"n_test": len(test_ids), "hybrid_selected_on_dev": hybrid, "methods": {}}
                for m in (f"{tag}:{x}@{rate}" for x in ("llml2L", "longllml", "bm25")):
                    common = [i for i in test_ids if (i, tag, m) in scores and (i, tag, hybrid) in scores]
                    if not common:
                        continue
                    comp = {"hybrid": hybrid}
                    if small:
                        comp["llmlingua2_small"] = small
                    split_report["methods"][m] = {"n": len(common), "accuracy": round(sum(scores[(i, tag, m)] for i in common) / len(common), 4), "comparisons": {}}
                    for label, ref in comp.items():
                        wins = sum(scores[(i, tag, m)] and not scores[(i, tag, ref)] for i in common)
                        losses = sum(scores[(i, tag, ref)] and not scores[(i, tag, m)] for i in common)
                        split_report["methods"][m]["comparisons"][label] = {
                            "method": ref,
                            "accuracy": round(sum(scores[(i, tag, ref)] for i in common) / len(common), 4),
                            "delta_pts": round(100 * sum(scores[(i, tag, m)] - scores[(i, tag, ref)] for i in common) / len(common), 2),
                            "p_mcnemar": float(binomtest(wins, wins + losses).pvalue) if wins + losses else 1.0,
                        }
                report["heldout_test"][split_key] = split_report
    else:
        from hotpot import clean, f1

        folder = BENCH / ("hotpot" if name == "hotpot" else f"longqa_{name}")
        items = {r["id"]: r for r in read_jsonl(folder / "items.jsonl")}
        scores = {}
        for a in read_jsonl(answers_path):
            if a["item_id"] not in items:
                continue
            for m in a.get("methods", []):
                if m == "original" or m.startswith("hybrid-") or m.startswith("llmlingua2@") or (m in METHODS and "|b2:" in a.get("key", "")):
                    scores[(a["item_id"], m)] = f1(clean(a["content"]), items[a["item_id"]]["answer"])
        ids = [i for i in items if (i, "original") in scores]
        report = {"n_original": len(ids), "f1_original": round(sum(scores[(i, "original")] for i in ids) / max(1, len(ids)), 4), "methods": {}}
        for m in METHODS:
            common = [i for i in ids if (i, m) in scores]
            if not common:
                continue
            diffs = [scores[(i, m)] - scores[(i, "original")] for i in common]
            p = float(wilcoxon(diffs).pvalue) if any(diffs) else 1.0
            kept = sum(variants.get((i, "", m), 0.0) for i in common) / len(common)
            report["methods"][m] = {
                "n": len(common), "f1": round(sum(scores[(i, m)] for i in common) / len(common), 4),
                "f1_original_paired": round(sum(scores[(i, "original")] for i in common) / len(common), 4),
                "delta_vs_original_f1_pts": round(100 * sum(diffs) / len(common), 2),
                "p_wilcoxon": p, "context_tokens_kept": round(kept, 4),
            }
            rate = "0.5" if m.endswith("@0.5") else "0.33"
            refs = (f"llmlingua2@{rate}", f"hybrid-s0.7@0.5" if rate == "0.5" else "hybrid-t-heavy@0.33")
            comparisons = {}
            for label, ref in zip(("llmlingua2_small", "frozen_hybrid"), refs):
                paired = [i for i in common if (i, ref) in scores]
                if not paired:
                    continue
                delta = [scores[(i, m)] - scores[(i, ref)] for i in paired]
                comparisons[label] = {
                    "method": ref, "n": len(paired),
                    "reference_f1": round(sum(scores[(i, ref)] for i in paired) / len(paired), 4),
                    "delta_f1_pts": round(100 * sum(delta) / len(paired), 2),
                    "p_wilcoxon": float(wilcoxon(delta).pvalue) if any(delta) else 1.0,
                }
            report["methods"][m]["comparisons"] = comparisons

    out = BENCH / "baselines2" / f"{name}_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"saved {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "export", "grade"])
    ap.add_argument("--set", required=True, choices=["belebele", "squad", "meetingbank", "hotpot"])
    ap.add_argument("--shard", default="1/1")
    ap.add_argument("--tag", default="")
    ap.add_argument("--methods", default="llml2L,longllml,bm25")
    ap.add_argument("--out", default="baselines2")
    ap.add_argument("--answers", default=None)
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.set, a.shard, a.methods.split(","), a.out)
    elif a.cmd == "export":
        export(a.set, a.tag, a.out)
    else:
        grade(a.set, a.answers)
