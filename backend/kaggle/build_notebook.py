"""Builds local_answers_t4.ipynb (kept as code so the notebook is reproducible).

One worker process per GPU (Kaggle T4 x2 -> ~2x), transformers only (no vLLM
install, which broke Kaggle's torch), priority order, resumable via
prev_answers.jsonl, error-tolerant batches, answers merged into
/kaggle/working/answers.jsonl every few minutes so a timeout keeps them.

    python backend/kaggle/build_notebook.py
"""

import json
from pathlib import Path

SETUP = r'''import glob, json, os, shutil, subprocess, sys, time
import torch

MODEL = "Qwen/Qwen2.5-3B-Instruct"   # Apache-2.0; weaker 'cheap' model, different family from gpt-oss
MAX_NEW = 256
BATCH = 24
PRIORITY = ["original", "crf+tokopt[o200k]", "llmlingua2+spans@0.5", "guarded2@0.5",
            "llmlingua2+spans@0.7", "guarded2@0.7", "llmlingua2+spans@0.3", "guarded2@0.4",
            "llmlingua2+spans@0.8", "guarded2@0.8", "llmlingua2+spans@0.4", "llmlingua2+spans@0.6",
            "guarded2@0.6", "heuristic"]
W = "/kaggle/working"
OUT = f"{W}/answers.jsonl"

src = glob.glob("/kaggle/input/**/prompts.jsonl", recursive=True)
assert src, "attach the dataset that contains prompts.jsonl"
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
todo.sort(key=lambda r: (min(rank.get(m, 99) for m in r["methods"]), len(r["prompt"])))
n_gpu = max(1, torch.cuda.device_count())
for g in range(n_gpu):  # interleave so every GPU works through the priority order
    with open(f"{W}/todo_{g}.jsonl", "w", encoding="utf-8") as fh:
        for r in todo[g::n_gpu]:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"{len(rows)} prompts, {len(done)} done, {len(todo)} to go, {n_gpu} GPU(s)", flush=True)
'''

WORKER = r'''import json, sys, time, traceback
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL, MAX_NEW, BATCH, TODO, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
rows = [json.loads(l) for l in open(TODO, encoding="utf-8")]
tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cuda:0").eval()

def chat_text(r):
    msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["prompt"]}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

t0, n_ok, n_err = time.time(), 0, 0
with open(OUT, "a", encoding="utf-8") as fh:
    for s in range(0, len(rows), BATCH):
        batch = rows[s:s + BATCH]
        try:
            enc = tok([chat_text(r) for r in batch], return_tensors="pt", padding=True,
                      truncation=True, max_length=2048).to(model.device)
            with torch.no_grad():
                g = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False, pad_token_id=tok.pad_token_id)
        except Exception:
            n_err += len(batch)
            print("batch failed:", traceback.format_exc()[-400:], flush=True)
            torch.cuda.empty_cache()
            continue
        for j, r in enumerate(batch):
            new = g[j, enc["input_ids"].shape[1]:]
            fh.write(json.dumps({"key": r["key"], "item_id": r["item_id"], "lang": r["lang"], "methods": r["methods"],
                                 "model": MODEL, "content": tok.decode(new, skip_special_tokens=True),
                                 "prompt_tokens": int(enc["attention_mask"][j].sum()),
                                 "completion_tokens": int((new != tok.pad_token_id).sum())}, ensure_ascii=False) + "\n")
        fh.flush()
        n_ok += len(batch)
        if (s // BATCH) % 10 == 0:
            print(f"{n_ok}/{len(rows)} answered, {n_err} failed, {time.time()-t0:.0f}s", flush=True)
print("worker finished", flush=True)
'''

LAUNCH = r'''open(f"{W}/worker.py", "w").write(WORKER_SRC)

def merge():
    """Fold per-GPU outputs into answers.jsonl (dedup by key) so a timeout keeps them."""
    seen, lines = set(), []
    for f in [OUT] + [f"{W}/out_{g}.jsonl" for g in range(n_gpu)]:
        if os.path.exists(f):
            for l in open(f, encoding="utf-8"):
                try:
                    k = json.loads(l)["key"]
                except Exception:
                    continue
                if k not in seen:
                    seen.add(k); lines.append(l if l.endswith("\n") else l + "\n")
    with open(OUT + ".tmp", "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    os.replace(OUT + ".tmp", OUT)
    return len(seen)

procs = []
for g in range(n_gpu):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(g)}
    procs.append(subprocess.Popen([sys.executable, f"{W}/worker.py", MODEL, str(MAX_NEW), str(BATCH),
                                   f"{W}/todo_{g}.jsonl", f"{W}/out_{g}.jsonl"], env=env,
                                  stdout=open(f"{W}/worker_{g}.log", "w"), stderr=subprocess.STDOUT))
while any(p.poll() is None for p in procs):
    time.sleep(300)
    print(time.strftime("%H:%M"), "answers so far:", merge(), flush=True)
print("all workers finished; total answers:", merge())
for g in range(n_gpu):
    print(f"--- worker {g} log tail ---\n" + open(f"{W}/worker_{g}.log").read()[-800:])
'''


def main() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": "# Local-model answers (Kaggle GPU, one worker per GPU)\n"},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": SETUP},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
         "source": "WORKER_SRC = " + repr(WORKER) + "\n"},
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": LAUNCH},
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    out = Path(__file__).with_name("local_answers_t4.ipynb")
    out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    compile("\n".join(c["source"] for c in cells if c["cell_type"] == "code"), "nb", "exec")
    compile(WORKER, "worker", "exec")
    print("wrote", out)


if __name__ == "__main__":
    main()
