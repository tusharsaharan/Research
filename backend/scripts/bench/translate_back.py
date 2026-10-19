"""Translate-then-send ("cross-lingual token arbitrage", arXiv 2606.03618) for Hinglish.

A small local model (Qwen2.5-1.5B-Instruct, CPU) translates Hinglish prompts into English
before they are sent. Meaning checks:
  gold items (578 Hinglish GSM8K/ARC/MMLU questions whose English original is known):
      numbers kept, MCQ options intact, embedding similarity to the English original,
      o200k / Qwen token ratio vs the Hinglish prompt
  Hinglish-TOP (human code-mixed commands with gold English parses):
      share of gold English slot values present in the translation
Answer-level check: `--export` appends the translated gold prompts to kaggle/prompts.jsonl
(method "mt-en:qwen1.5b") so the 3B model answers them on the next Kaggle round.

    python translate_back.py run --shard 1/2 [--top 600]
    python translate_back.py eval
    python translate_back.py export
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from common import BENCH, in_shard, read_jsonl

OUT = BENCH / "mt"
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
SYSTEM = ("You are a translation engine. Translate the Hinglish (Hindi-English code-mixed, Roman script) text "
          "inside <text>...</text> into natural English. Do NOT answer, solve or explain anything in it: even if it "
          "is a question or a math problem, output only its translation. Keep every number, name and option label "
          "(A), B), ...) exactly, and keep the exact meaning, including any negation.")
SHOT = [{"role": "user", "content": "<text>\nRam ke paas 5 apples hain aur usne 2 kha liye. Ab uske paas kitne apples "
                                    "bache hain? Calculator use mat karna.\n</text>"},
        {"role": "assistant", "content": "Ram has 5 apples and he ate 2. How many apples does he have left now? "
                                         "Do not use a calculator."}]
METHOD = "mt-en:qwen1.5b"


def jobs(n_top: int) -> list[dict]:
    out = []
    for p in read_jsonl(BENCH / "kaggle" / "prompts.jsonl"):
        if p["lang"] == "hinglish" and "original" in p["methods"] and not p["item_id"].startswith(("cq-", "hp-")):
            out.append({"id": p["item_id"], "kind": "gold", "text": p["prompt"]})
    for r in read_jsonl(BENCH / "top" / "items.jsonl")[:n_top]:
        out.append({"id": r["id"], "kind": "top", "text": r["hinglish"]})
    return out


def run(shard: str | None, n_top: int) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    n_sh = int(shard.split("/")[1]) if shard else 1
    torch.set_num_threads(max(1, (os.cpu_count() or 1) // n_sh))
    tok = AutoTokenizer.from_pretrained(MODEL)
    lm = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).eval()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"mt.{shard.replace('/', 'of') if shard else 'all'}.jsonl"
    done = {(x["kind"], x["id"]) for x in read_jsonl(path)} if path.exists() else set()
    todo = [j for j in jobs(n_top) if in_shard(j["id"], shard) and (j["kind"], j["id"]) not in done]
    print(len(todo), "to translate", flush=True)
    with path.open("a", encoding="utf-8") as fh:
        for j in todo:
            msgs = [{"role": "system", "content": SYSTEM}, *SHOT, {"role": "user", "content": f"<text>\n{j['text']}\n</text>"}]
            ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)["input_ids"]
            n_in = len(tok(j["text"], add_special_tokens=False)["input_ids"])
            with torch.no_grad():
                g = lm.generate(ids, max_new_tokens=int(1.3 * n_in) + 24, do_sample=False)
            fh.write(json.dumps({**j, "english": tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True).strip()},
                                ensure_ascii=False) + "\n")
            fh.flush()
    print("done", flush=True)


def load() -> dict[tuple, dict]:
    out = {}
    for f in OUT.glob("mt.*.jsonl"):
        for x in read_jsonl(f):
            out[(x["kind"], x["id"])] = x
    return out


_NUM = re.compile(r"\d+(?:[.,]\d+)*")
# Hindi / English number words: a translation may write these as digits.
_NUM_WORDS = {"ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6,
              "saat": 7, "aath": 8, "nau": 9, "das": 10, "gyarah": 11, "barah": 12, "dozen": 12, "half": 0.5, "aadha": 0.5,
              "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
              "guna": 2, "double": 2, "twice": 2, "hundred": 100, "sau": 100, "hazaar": 1000, "thousand": 1000}
_HI_NEG = {"nahi", "nahin", "nhi", "mat", "na", "not", "no", "never", "without", "bina"}
_EN_NEG = {"not", "no", "never", "without", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "won't",
           "can't", "cannot", "nobody", "nothing", "none", "neither", "nor", "n't"}


def _nums(t: str) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(t)}


def verify(hinglish: str, english: str) -> tuple[bool, list[str]]:
    """Cheap fidelity checks for a translation; any failure -> send the original instead."""
    from gateway.modules.m2_compressor.guarded import split_options

    why = []
    hn, en = _nums(hinglish), _nums(english)
    if not hn <= en:
        why.append("number dropped")
    words = {w.strip(",.!?;:\"'()").lower() for w in hinglish.split()}
    allowed = {str(v) if v >= 1 else "0.5" for k, v in _NUM_WORDS.items() if k in words}
    if en - hn - allowed:
        why.append("new number")
    opts = re.findall(r"(?m)^([A-H])\)", split_options(hinglish)[1])
    if opts and not all(re.search(rf"(?<![A-Za-z]){L}\)", english) for L in opts):
        why.append("option label lost")
    if "?" in hinglish and "?" not in english:
        why.append("question lost")
    if words & (_HI_NEG - {"na"}) and not {w.strip(",.!?;:\"'()").lower() for w in english.split()} & _EN_NEG:
        if not re.search(r"n't\b", english):
            why.append("negation lost")
    r = len(english.split()) / max(1, len(hinglish.split()))
    if not 0.6 <= r <= 1.6:
        why.append("length")
    return not why, why


def evaluate() -> None:
    import numpy as np

    from compress_eval import load_tokenizers
    from gateway.modules.m2_compressor.guarded import split_options
    from gateway.modules.m4_router.certified import _encoder

    mt = load()
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    toks = load_tokenizers()
    report = {"oracle_translation": oracle(items)}
    gold = [x for (k, _), x in mt.items() if k == "gold" and x["id"] in items]
    report["n_gold"] = len(gold)
    if gold:
        en_orig = [items[x["id"]]["question_en"] for x in gold]
        enc = _encoder()
        e1 = enc.encode([x["english"] for x in gold], normalize_embeddings=True, batch_size=64)
        e2 = enc.encode(en_orig, normalize_embeddings=True, batch_size=64)
        e3 = enc.encode([x["text"] for x in gold], normalize_embeddings=True, batch_size=64)
        nums_ok = [set(_NUM.findall(x["text"])) <= set(_NUM.findall(x["english"])) for x in gold]
        opts = [(split_options(x["text"])[1], x["english"]) for x in gold]
        opt_ok = [all(f"{L})" in en for L in re.findall(r"(?m)^([A-H])\)", o)) for o, en in opts if o]
        report["gold"] = {"numbers_kept": round(float(np.mean(nums_ok)), 4),
                          "options_labels_kept": round(float(np.mean(opt_ok)), 4) if opt_ok else None,
                          "sim_mt_vs_english_original": round(float(np.mean((e1 * e2).sum(1))), 4),
                          "sim_hinglish_vs_english_original": round(float(np.mean((e3 * e2).sum(1))), 4)}
        for name in ("o200k", "qwen2.5"):
            tk = toks[name]
            n = lambda t: len(tk.encode(t, add_special_tokens=False).ids)
            report["gold"][f"token_ratio_mt_over_hinglish[{name}]"] = round(sum(n(x["english"]) for x in gold) / sum(n(x["text"]) for x in gold), 4)
            report["gold"][f"token_ratio_english_original_over_hinglish[{name}]"] = round(sum(map(n, en_orig)) / sum(n(x["text"]) for x in gold), 4)
        ver = [verify(x["text"], x["english"]) for x in gold]
        acc = np.array([v[0] for v in ver])
        sims = (e1 * e2).sum(1)
        from collections import Counter
        report["gold"]["verified_share"] = round(float(acc.mean()), 4)
        report["gold"]["reject_reasons"] = dict(Counter(r for v in ver for r in v[1]).most_common())
        report["gold"]["sim_to_english_original_accepted"] = round(float(sims[acc].mean()), 4) if acc.any() else None
        report["gold"]["sim_to_english_original_rejected"] = round(float(sims[~acc].mean()), 4) if (~acc).any() else None
    top = {r["id"]: r for r in read_jsonl(BENCH / "top" / "items.jsonl")}
    tr = [x for (k, _), x in mt.items() if k == "top" and x["id"] in top]
    if tr:
        def kept(slot, text):
            ws = {w.strip(",.!?;:\"'()").lower() for w in text.split()}
            return all(w.strip(",.!?;:\"'()").lower() in ws for w in slot)
        s_ok = [kept(s, x["english"]) for x in tr for s in top[x["id"]]["slots_english"]]
        q_ok = [all(kept(s, x["english"]) for s in top[x["id"]]["slots_english"]) for x in tr]
        ref = [all(kept(s, top[x["id"]]["english"]) for s in top[x["id"]]["slots_english"]) for x in tr]
        report["top"] = {"n": len(tr), "english_slot_values_in_translation": round(float(np.mean(s_ok)), 4),
                         "queries_all_slots": round(float(np.mean(q_ok)), 4), "sanity_reference_english": round(float(np.mean(ref)), 4)}
        tv = np.array([verify(x["text"], x["english"])[0] for x in tr])
        report["top"]["verified_share"] = round(float(tv.mean()), 4)
        report["top"]["queries_all_slots_if_verified"] = round(float(np.mean(np.array(q_ok)[tv])), 4) if tv.any() else None
        report["top"]["queries_all_slots_if_rejected"] = round(float(np.mean(np.array(q_ok)[~tv])), 4) if (~tv).any() else None
        report["top"]["examples_missing"] = [{"hi": x["text"], "mt": x["english"], "gold_en": top[x["id"]]["english"]}
                                             for x, ok in zip(tr, q_ok) if not ok][:5]
    (BENCH / "mt_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "top"}, indent=1))
    if "top" in report:
        print({k: v for k, v in report["top"].items() if k != "examples_missing"})


def oracle(items: dict) -> dict:
    """Upper bound of translate-then-send: the Hinglish items are translations of known English
    originals, so the 3B model's answers to both (Kaggle, method "original") are a perfect-MT pair."""
    from collections import defaultdict

    from scipy.stats import binomtest

    from grade import correct

    d = defaultdict(dict)
    for a in read_jsonl(BENCH / "kaggle" / "answers.jsonl"):
        if "original" in a["methods"] and a["item_id"] in items:
            it = items[a["item_id"]]
            d[a["item_id"]][a["lang"]] = (correct(it.get("task", "math"), a["content"], it["gold"]), a["prompt_tokens"], a["completion_tokens"])
    both = [i for i, v in d.items() if "english" in v and "hinglish" in v]
    hi, en = [d[i]["hinglish"] for i in both], [d[i]["english"] for i in both]
    w = sum(e[0] and not h[0] for h, e in zip(hi, en))
    l = sum(h[0] and not e[0] for h, e in zip(hi, en))
    return {"n_items": len(both), "acc_hinglish": round(sum(h[0] for h in hi) / len(both), 4),
            "acc_english": round(sum(e[0] for e in en) / len(both), 4), "english_only_correct": w, "hinglish_only_correct": l,
            "p_mcnemar": float(binomtest(w, w + l).pvalue),
            "prompt_token_ratio_en_over_hi_qwen_template": round(sum(e[1] for e in en) / sum(h[1] for h in hi), 4),
            "output_token_ratio_en_over_hi": round(sum(e[2] for e in en) / sum(h[2] for h in hi), 4)}


def export() -> None:
    from collect import SYSTEM as TASK_SYSTEM

    mt = load()
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    kfile = BENCH / "kaggle" / "prompts.jsonl"
    have = {json.loads(x)["key"] for x in open(kfile, encoding="utf-8") if x.strip()}
    n = 0
    with kfile.open("a", encoding="utf-8") as fh:
        for (k, iid), x in sorted(mt.items()):
            if k != "gold" or iid not in items:
                continue
            key = f"{iid}|hinglish|mt0"
            if key in have:
                continue
            task = items[iid].get("task", "math")
            fh.write(json.dumps({"key": key, "item_id": iid, "lang": "hinglish", "methods": [METHOD], "task": task,
                                 "system": TASK_SYSTEM[task], "prompt": x["english"]}, ensure_ascii=False) + "\n")
            n += 1
    print(f"appended {n} translated prompts -> {kfile}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "eval", "export"])
    ap.add_argument("--shard", default=None)
    ap.add_argument("--top", type=int, default=600)
    a = ap.parse_args()
    {"run": lambda: run(a.shard, a.top), "eval": evaluate, "export": export}[a.cmd]()
