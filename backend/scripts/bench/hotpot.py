"""Long-context compression test on HotpotQA (distractor, validation): the setting
LLMLingua-style compressors are designed for (~1-1.5k-token contexts, 10 paragraphs,
2 of them gold). Only the context is compressed; the question is kept verbatim.

Methods: heuristic, lexical-safe (2609.13154), LLMLingua-2 plain / guarded,
question-aware guarded (LongLLMLingua's idea: force-keep context words that occur in
the question), and Selective Context (Li et al. 2023: drop the lowest self-information
words, scored by a small causal LM, Qwen2.5-0.5B).

    python hotpot.py build --n 1000
    python hotpot.py compress --shard 1/4 [--methods ...]
    python hotpot.py answer --model Qwen/Qwen2.5-1.5B-Instruct --limit 300 --shard 1/2
    python hotpot.py grade --answers <file>
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import string
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import BENCH, in_shard, read_jsonl

OUT = BENCH / "hotpot"
RATES = (0.5, 0.33)
METHODS = ["heuristic", "lexical-safe", *[f"{m}@{r}" for r in RATES for m in ("llmlingua2", "guarded", "qaware")],
           "selective@0.5", "selective@0.33", "sentsel@0.5", "sentsel@0.33",
           "hybrid-s-heavy@0.5", "hybrid-t-heavy@0.5", "hybrid-s-heavy@0.33", "hybrid-t-heavy@0.33",
           # round 2: finer splits around the winner, tighter budgets, relevance-graded
           "hybrid-s0.7@0.5", "hybrid-s0.9@0.5", "hybrid-s0.5@0.25", "hybrid-s0.7@0.25", "hybrid-s0.45@0.2",
           "hybrid-s0.65@0.2", "graded0.6@0.5", "graded0.6@0.33", "graded0.6@0.25", "llmlingua2@0.25", "llmlingua2@0.2"]
SYSTEM = "Answer the question using the context. Reply with the short answer only (a few words, or yes/no)."
STOP = set("a an the of in on at to for by with from and or is are was were be been what which who whom whose when "
           "where why how did does do that this these those as it its into than then there their they he she his her".split())


def build(n: int) -> None:
    from build_items import hf_rows

    rows = hf_rows("hotpotqa/hotpot_qa", "distractor", "validation")
    random.Random(20261019).shuffle(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "items.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows[:n]:
            ctx = "\n".join(f"{t}: {''.join(s)}" for t, s in zip(r["context"]["title"], r["context"]["sentences"]))
            fh.write(json.dumps({"id": "hp-" + r["id"], "question": r["question"], "answer": r["answer"],
                                 "type": r["type"], "level": r["level"], "context": ctx}, ensure_ascii=False) + "\n")
    print(n, "items ->", OUT / "items.jsonl")


# ---------------------------------------------------------------- Selective Context
class SelectiveContext:
    """Word-level self-information pruning (Li et al., EMNLP 2023), lexical-unit = word."""

    def __init__(self, model="Qwen/Qwen2.5-0.5B-Instruct"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model)
        self.lm = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch.float32).eval()

    def info(self, text: str):
        torch = self.torch
        enc = self.tok(text, return_offsets_mapping=True, return_tensors="pt", truncation=True, max_length=4096)
        with torch.no_grad():
            logits = self.lm(input_ids=enc["input_ids"]).logits[0]
        ids = enc["input_ids"][0]
        lp = torch.log_softmax(logits[:-1].float(), -1).gather(1, ids[1:, None])[:, 0]
        si = [0.0] + (-lp).tolist()  # first token: no context -> 0 (kept by the word rule below)
        return enc["offset_mapping"][0].tolist(), si

    def compress(self, text: str, keep: float) -> str:
        offs, si = self.info(text)
        words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
        score = [0.0] * len(words)
        wi = 0
        for (s, e), v in zip(offs, si):
            while wi < len(words) and words[wi][1] <= s:
                wi += 1
            if wi < len(words) and e > words[wi][0]:
                score[wi] += v
        k = max(1, round(keep * len(words)))
        keep_idx = set(sorted(range(len(words)), key=lambda i: -score[i])[:k])
        lines, cur = [], []
        for i, (s, e) in enumerate(words):
            if i in keep_idx:
                cur.append(text[s:e])
            if i + 1 == len(words) or "\n" in text[e:words[i + 1][0]]:
                lines.append(" ".join(cur))
                cur = []
        return "\n".join(l for l in lines if l)


def compress(shard: str | None, only: list[str] | None, limit: int = 0) -> None:
    import torch

    from gateway.modules.m2_compressor import guarded as G
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m2_compressor.lexical_safe import compress_lexical_safe
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor
    from gateway.tokenizer import TokenCounter

    n_shards = int(shard.split("/")[1]) if shard else 1
    torch.set_num_threads(max(1, (os.cpu_count() or 1) // n_shards))
    methods = only or METHODS
    comp = Compressor(counter=TokenCounter(), use_crf=False, use_llmlingua2=True)
    lingua = get_compressor()
    base_guard = G._guard_words
    sel = SelectiveContext() if any(m.startswith("selective") for m in methods) else None

    def plain(rate):
        def f(t, q):
            r = comp.compress_llmlingua2(t, rate=rate)
            return r.compressed if r.method == "llmlingua2" else t
        return f

    def guarded(rate, qaware=False):
        def f(t, q):
            qwords = {w for w in re.findall(r"[A-Za-z0-9']+", q) if w.lower() not in STOP}
            extra = sorted({w for w in re.findall(r"[A-Za-z0-9']+", t) if w in qwords}) if qaware else []
            G._guard_words = lambda s: sorted(set(base_guard(s)) | set(extra))
            try:
                return G.compress_guarded(t, rate, lingua) or t
            finally:
                G._guard_words = base_guard
        return f

    fns = {"heuristic": lambda t, q: comp.compress_heuristic(t).compressed, "lexical-safe": lambda t, q: compress_lexical_safe(t)}
    for r in RATES:
        fns |= {f"llmlingua2@{r}": plain(r), f"guarded@{r}": guarded(r), f"qaware@{r}": guarded(r, True)}
    fns |= {"llmlingua2@0.25": plain(0.25), "llmlingua2@0.2": plain(0.2)}
    if any(m.startswith("sentsel") for m in methods):
        from belebele_extra import sentsel
        from gateway.modules.m4_router.certified import _encoder
        enc = _encoder()
        fns |= {f"sentsel@{r}": (lambda t, q, r=r: sentsel(t, q, r, enc, comp.counter.count)) for r in (0.5, 0.33)}
    if any(m.startswith(("hybrid", "graded")) for m in methods):
        from hybrid import SPLITS, graded, hybrid
        from gateway.modules.m4_router.certified import _encoder
        henc = _encoder()
        for tgt, sp in SPLITS.items():
            for name, sh in sp.items():
                fns[f"hybrid-{name}@{tgt}"] = (lambda t, q, tgt=tgt, sh=sh: hybrid(t, q, tgt, sh, henc, comp.counter.count, lingua))
        for m in methods:  # generic names: hybrid-s{share}@{target}, graded{spread}@{target}
            if m in fns:
                continue
            g = re.fullmatch(r"hybrid-s([\d.]+)@([\d.]+)", m)
            if g:
                fns[m] = (lambda t, q, sh=float(g[1]), tgt=float(g[2]): hybrid(t, q, tgt, sh, henc, comp.counter.count, lingua))
            g = re.fullmatch(r"graded([\d.]+)@([\d.]+)", m)
            if g:
                fns[m] = (lambda t, q, sp=float(g[1]), tgt=float(g[2]): graded(t, q, tgt, henc, comp.counter.count, lingua, spread=sp))
    if sel:
        fns |= {"selective@0.5": lambda t, q: sel.compress(t, 0.5), "selective@0.33": lambda t, q: sel.compress(t, 0.33)}
    tag = shard.replace("/", "of") if shard else "all"
    path = OUT / f"compressed.{tag}.jsonl"
    done = {(x["id"], x["method"]) for x in read_jsonl(path)} if path.exists() else set()
    with path.open("a", encoding="utf-8") as fh:
        for it in read_jsonl(OUT / "items.jsonl")[: limit or None]:
            if not in_shard(it["id"], shard):
                continue
            for m in methods:
                if (it["id"], m) in done:
                    continue
                out = fns[m](it["context"], it["question"])
                fh.write(json.dumps({"id": it["id"], "method": m, "text": out, "tok_before": comp.counter.count(it["context"]),
                                     "tok_after": comp.counter.count(out)}, ensure_ascii=False) + "\n")
            fh.flush()
    print("done", tag, flush=True)


def compressed() -> dict:
    out = {}
    for f in sorted(OUT.glob("compressed.*.jsonl")):
        for r in read_jsonl(f):
            out[(r["id"], r["method"])] = r
    return out


def prompts(limit: int) -> list[dict]:
    items = read_jsonl(OUT / "items.jsonl")[: limit or None]
    comp = compressed()
    rows = []
    for it in items:
        variants = {"original": it["context"]} | {m: comp[(it["id"], m)]["text"] for m in METHODS if (it["id"], m) in comp}
        by_text = defaultdict(list)
        for m, t in variants.items():
            by_text[t].append(m)
        for i, (t, ms) in enumerate(by_text.items()):
            rows.append({"key": f"{it['id']}|english|hp{i}", "item_id": it["id"], "lang": "english", "methods": ms,
                         "task": "hotpot", "system": SYSTEM, "prompt": f"Context:\n{t}\n\nQuestion: {it['question']}"})
    return rows


def export(limit: int) -> None:
    rows = prompts(limit)
    with (OUT / "prompts.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "prompts ->", OUT / "prompts.jsonl")


def export_kaggle(limit: int) -> None:
    """Append HotpotQA prompts (all compressed versions) to the Kaggle queue (KAGGLE_TAG selects the folder).
    Grade afterwards from that folder: cd data/bench/kaggle && python ../../../scripts/bench/hotpot.py grade --answers answers.jsonl"""
    kfile = BENCH / f"kaggle{os.environ.get('KAGGLE_TAG', '')}" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for r in prompts(limit):
            if r["key"] not in have:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"appended {n} HotpotQA prompts -> {kfile}")


def answer(model: str, limit: int, shard: str | None) -> None:
    """Local CPU answering (greedy, short answers)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    n_shards = int(shard.split("/")[1]) if shard else 1
    torch.set_num_threads(max(1, (os.cpu_count() or 1) // n_shards))
    tok = AutoTokenizer.from_pretrained(model)
    lm = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch.float32).eval()
    name = model.split("/")[-1]
    path = OUT / f"answers.{name}.{shard.replace('/', 'of') if shard else 'all'}.jsonl"
    done = {r["key"] for r in read_jsonl(path)} if path.exists() else set()
    rows = [r for r in prompts(limit) if in_shard(r["key"], shard) and r["key"] not in done]
    rows.sort(key=lambda r: (r["item_id"], len(r["prompt"])))
    print(len(rows), "to answer", flush=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["prompt"]}]
            ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)["input_ids"]
            with torch.no_grad():
                g = lm.generate(ids, max_new_tokens=24, do_sample=False)
            out = tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)
            fh.write(json.dumps({**{k: r[k] for k in ("key", "item_id", "lang", "methods")}, "model": model, "content": out,
                                 "prompt_tokens": int(ids.shape[1]), "completion_tokens": int(g.shape[1] - ids.shape[1])},
                                ensure_ascii=False) + "\n")
            fh.flush()
    print("done", flush=True)


# ---------------------------------------------------------------- grading (SQuAD EM / F1)
def norm(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def f1(pred: str, gold: str) -> float:
    p, g = norm(pred).split(), norm(gold).split()
    common = Counter(p) & Counter(g)
    k = sum(common.values())
    if not k:
        return 0.0
    pr, rc = k / len(p), k / len(g)
    return 2 * pr * rc / (pr + rc)


def clean(reply: str) -> str:
    r = reply.strip().split("\n")[0]
    r = re.sub(r"^(the )?(short )?answer( is)?:?\s*", "", r, flags=re.I)
    return r.rstrip(".")


def grade(files: list[str]) -> None:
    from scipy.stats import wilcoxon

    items = {r["id"]: r for r in read_jsonl(OUT / "items.jsonl")}
    comp = compressed()
    report = {}
    for fpat in files:
        if Path(fpat).is_absolute():
            rows = read_jsonl(Path(fpat))
        else:
            rows = [r for f in sorted(Path(".").glob(fpat)) if f.exists() for r in read_jsonl(f)] or \
                   [r for f in sorted(OUT.glob(fpat)) for r in read_jsonl(f)]
        sc = {}
        for r in rows:
            if r["item_id"] in items:
                for m in r["methods"]:
                    sc[(r["item_id"], m)] = f1(clean(r["content"]), items[r["item_id"]]["answer"])
        model = rows[0]["model"] if rows else fpat
        base_ids = [i for i in items if (i, "original") in sc]
        print(f"== {model}: {len(base_ids)} items, F1 original {sum(sc[(i, 'original')] for i in base_ids) / max(1, len(base_ids)):.3f}")
        res = {}
        for m in METHODS:
            ids = [i for i in base_ids if (i, m) in sc]
            if not ids:
                continue
            a = [sc[(i, "original")] for i in ids]
            b = [sc[(i, m)] for i in ids]
            diff = [y - x for x, y in zip(a, b)]
            p = wilcoxon(diff).pvalue if any(diff) else 1.0
            toks = [comp[(i, m)] for i in ids if (i, m) in comp]
            kept = sum(t["tok_after"] for t in toks) / max(1, sum(t["tok_before"] for t in toks))
            res[m] = {"n": len(ids), "kept": round(kept, 4), "f1": round(sum(b) / len(b), 4),
                      "delta_f1_pts": round(100 * sum(diff) / len(diff), 2), "p_wilcoxon": round(float(p), 4)}
            print(f"{m:16} kept={kept:.3f} F1={res[m]['f1']:.3f} d={res[m]['delta_f1_pts']:+6.2f} p={res[m]['p_wilcoxon']:.3g} n={len(ids)}")
        report[model] = res
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "compress", "export", "export-kaggle", "answer", "grade"])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--shard", default=None)
    ap.add_argument("--methods", default=None)
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--answers", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.n)
    elif a.cmd == "compress":
        compress(a.shard, a.methods.split(",") if a.methods else None, a.limit)
    elif a.cmd == "export":
        export(a.limit)
    elif a.cmd == "export-kaggle":
        export_kaggle(a.limit)
    elif a.cmd == "answer":
        answer(a.model, a.limit, a.shard)
    else:
        grade(a.answers)
