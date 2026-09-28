"""build_pilot_notebook.py — (re)build colab_qwen_pilot.ipynb (always valid JSON)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "colab_qwen_pilot.ipynb")

MD = lambda *lines: {"cell_type": "markdown", "metadata": {},
                     "source": [l + "\n" if not l.endswith("\n") else l for l in lines]}
CODE = lambda *lines: {"cell_type": "code", "metadata": {},
                       "source": [l + "\n" if not l.endswith("\n") else l for l in lines],
                       "execution_count": None, "outputs": []}

GEN = r"""import csv, json, os, time, urllib.request
from google.colab import drive
drive.mount('/content/drive', force_remount=False)
OLLAMA = "http://localhost:11434"
SRC = "/content/drive/MyDrive/laya_ft/pilot_300.csv"
DST = "/content/qwen_pilot_300.csv"

def ollama_generate(prompt):
    body = json.dumps({"model": "qwen2.5:latest", "prompt": prompt,
                       "stream": False, "options": {"num_predict": 512}}).encode()
    req = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r:
        return json.loads(r.read().decode()).get("response", "").strip()

prompts = [row["prompt"] for row in csv.DictReader(open(SRC, encoding="utf-8-sig"))]
done = set()
if os.path.exists(DST):
    done = {row["prompt"] for row in csv.DictReader(open(DST, encoding="utf-8")) if row.get("qwen_response")}
    print(f"resuming: {len(done)} already done")
todo = [p for p in prompts if p not in done]
print(f"total={len(prompts)} todo={len(todo)}", flush=True)
mode = "a" if done else "w"
with open(DST, mode, encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["prompt", "qwen_response"], quoting=csv.QUOTE_ALL)
    if not done:
        w.writeheader()
        f.flush()
    t0 = time.time()
    ok = 0
    for i, p in enumerate(todo):
        try:
            resp = ollama_generate(p)
        except Exception as e:
            print(f"[{i+1}/{len(todo)}] FAIL {type(e).__name__}: {str(e)[:120]} :: {p[:60]}", flush=True)
            continue
        w.writerow({"prompt": p, "qwen_response": resp})
        f.flush()
        ok += 1
        print(f"[{i+1}/{len(todo)}] ok={ok} len={len(resp)} elapsed={(time.time()-t0)/60:.1f}m :: {p[:60]}", flush=True)
print("PILOT DONE", flush=True)
"""

cells = [
    MD("# Qwen pilot: 300 stratified answers on Colab (Ollama + T4)",
       "",
       "**Inputs** (Drive folder `laya_ft/`): `pilot_300.csv` (prompt column).",
       "**Output:** `/content/qwen_pilot_300.csv` — download back to `data/`.",
       "Time: **~1.5–2.5 hrs**. Resume-safe: re-running continues where it stopped.",
       "",
       "Consistency: same `qwen2.5` Q4_K_M quant + `num_predict 512` as the local 200."),
    MD("## 1. GPU check"),
    CODE("!nvidia-smi --query-gpu=name,memory.total --format=csv",
         "import torch",
         "print('cuda:', torch.cuda.is_available(), '| gpus:', torch.cuda.device_count())",
         "assert torch.cuda.is_available(), 'Runtime -> Change runtime type -> GPU'"),
    MD("## 2. Install + start Ollama, pull model"),
    CODE("!curl -fsSL https://ollama.com/install.sh | sh",
         "!nohup ollama serve > /tmp/ollama.log 2>&1 & sleep 8; cat /tmp/ollama.log | head -5",
         "!ollama pull qwen2.5",
         "!ollama ps"),
    MD("## 3. Verify GPU offload (want 100% GPU, not CPU)"),
    CODE("!ollama ps",
         "!ollama run qwen2.5 'Say hi in one short sentence.'"),
    MD("## 4. Generate (sequential, per-row flush, resume-safe)"),
    CODE(*GEN.splitlines()),
    MD("## 5. Sanity check + download",
       "",
       "Expect 300 rows. Spot-check 2 answers printed below, then download",
       "`/content/qwen_pilot_300.csv` (Files pane → Download) into local `data/`."),
    CODE("import csv",
         "rows = list(csv.DictReader(open('/content/qwen_pilot_300.csv', encoding='utf-8')))",
         "print('rows:', len(rows))",
         "import statistics",
         "ls = [len(r['qwen_response']) for r in rows]",
         "print('len median/min/max:', int(statistics.median(ls)), min(ls), max(ls))",
         "print('empty:', sum(1 for r in rows if not r['qwen_response'].strip()))",
         "for r in rows[:2]:",
         "    print('----', r['prompt'][:80])",
         "    print(r['qwen_response'][:400])"),
]

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python3"}},
      "nbformat": 4, "nbformat_minor": 4}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote", OUT, "cells:", len(cells))
