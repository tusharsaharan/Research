"""Builds local_answers_t4.ipynb (kept as code so the notebook is reproducible).

    python backend/kaggle/build_notebook.py
"""

import json
from pathlib import Path

CELLS = [
    ("markdown", "# Local-model answers (Kaggle GPU)\n\ntransformers only (no vLLM install, which can break "
                 "Kaggle's preinstalled torch), priority order, resumable, error-tolerant.\n"),
    ("code", r'''import glob, json, os, shutil, time, traceback
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-3B-Instruct"   # Apache-2.0; weaker 'cheap' model, different family from gpt-oss
MAX_NEW = 384
BATCH = 24
SAVE_EVERY = 240
PRIORITY = ["original", "crf+tokopt[o200k]", "llmlingua2+spans@0.5", "guarded2@0.5",
            "llmlingua2+spans@0.7", "guarded2@0.7", "llmlingua2+spans@0.3", "guarded2@0.4",
            "llmlingua2+spans@0.8", "guarded2@0.8", "llmlingua2+spans@0.4", "llmlingua2+spans@0.6",
            "guarded2@0.6", "heuristic"]

src = glob.glob("/kaggle/input/**/prompts.jsonl", recursive=True)
assert src, "attach the dataset that contains prompts.jsonl"
OUT = "/kaggle/working/answers.jsonl"
prev = glob.glob("/kaggle/input/**/prev_answers.jsonl", recursive=True)
if prev and not os.path.exists(OUT):
    shutil.copy(prev[0], OUT)
rows = [json.loads(l) for l in open(src[0], encoding="utf-8")]
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"):
        try:
            done.add(json.loads(l)["key"])
        except Exception:
            pass
rank = {m: i for i, m in enumerate(PRIORITY)}
todo = [r for r in rows if r["key"] not in done]
# most important comparisons first; within a priority, similar lengths batch well
todo.sort(key=lambda r: (min(rank.get(m, 99) for m in r["methods"]), len(r["prompt"])))
print(f"{len(rows)} prompts, {len(done)} done, {len(todo)} to go; GPUs: {torch.cuda.device_count()}", flush=True)
'''),
    ("code", r'''tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cuda:0")
model.eval()

def chat_text(r):
    msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["prompt"]}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def generate(batch):
    texts = [chat_text(r) for r in batch]
    enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=2048).to(model.device)
    with torch.no_grad():
        g = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False, pad_token_id=tok.pad_token_id)
    out = []
    for j in range(g.shape[0]):
        new = g[j, enc["input_ids"].shape[1]:]
        out.append((tok.decode(new, skip_special_tokens=True), int(enc["attention_mask"][j].sum()),
                    int((new != tok.pad_token_id).sum())))
    return out
'''),
    ("code", r'''t0, n_ok, n_err, buf = time.time(), 0, 0, []
for s in range(0, len(todo), BATCH):
    batch = todo[s:s + BATCH]
    try:
        res = generate(batch)
    except Exception:
        n_err += len(batch)
        print("batch failed:", traceback.format_exc()[-600:], flush=True)
        torch.cuda.empty_cache()
        continue
    for r, (text, p_tok, c_tok) in zip(batch, res):
        buf.append(json.dumps({"key": r["key"], "item_id": r["item_id"], "lang": r["lang"], "methods": r["methods"],
                               "model": MODEL, "content": text, "prompt_tokens": p_tok,
                               "completion_tokens": c_tok}, ensure_ascii=False))
    n_ok += len(batch)
    if len(buf) >= SAVE_EVERY or s + BATCH >= len(todo):
        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write("\n".join(buf) + "\n")
        buf = []
        print(f"{n_ok}/{len(todo)} answered, {n_err} failed, {time.time()-t0:.0f}s", flush=True)
print("finished ->", OUT)
'''),
]


def main() -> None:
    cells = []
    for kind, src in CELLS:
        c = {"cell_type": kind, "metadata": {}, "source": src}
        if kind == "code":
            c |= {"execution_count": None, "outputs": []}
        cells.append(c)
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    out = Path(__file__).with_name("local_answers_t4.ipynb")
    out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    compile("\n".join(s for k, s in CELLS if k == "code"), "nb", "exec")
    print("wrote", out)


if __name__ == "__main__":
    main()
