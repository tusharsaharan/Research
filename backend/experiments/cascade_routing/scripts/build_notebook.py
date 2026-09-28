"""build_notebook.py — (re)build colab_finetune_laya.ipynb from Python data (always valid JSON)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "colab_finetune_laya.ipynb")

MD = lambda *lines: {"cell_type": "markdown", "metadata": {},
                     "source": [l + "\n" if not l.endswith("\n") else l for l in lines]}
CODE = lambda *lines: {"cell_type": "code", "metadata": {},
                       "source": [l + "\n" if not l.endswith("\n") else l for l in lines],
                       "execution_count": None, "outputs": []}

TRAIN = r"""import os, sys, time, json, random
import torch
from safetensors.torch import load_file, save_file
from transformers import AutoTokenizer
from laya.common import build_model, proper_reward, QTYPES

def collate(items, pad_id):
    n = len(items)
    L = max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, L), pad_id, dtype=torch.long)
    att = torch.zeros((n, L), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    tgt = torch.zeros((n, kmax), dtype=torch.float32)
    for i, it in enumerate(items):
        ids[i, :len(it["ids"])] = torch.tensor(it["ids"])
        att[i, :len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = torch.tensor(it["markers"])
        mmask[i, :k] = True
        tgt[i, :len(it["target"])] = torch.tensor(it["target"], dtype=torch.float32)
    return {"input_ids": ids, "attention_mask": att, "marker_pos": mpos,
            "marker_mask": mmask, "target": tgt,
            "qtype": torch.tensor([it["qtype"] for it in items]),
            "label": torch.tensor([it["label"] for it in items])}

def fit_one_temp(sel):
    if len(sel) < 10:
        return 1.0
    kmax = max(len(z) for z, _ in sel)
    Z = torch.full((len(sel), kmax), -1e4)
    T = torch.zeros((len(sel), kmax))
    for i, (z, t) in enumerate(sel):
        Z[i, :len(z)] = torch.tensor(z)
        T[i, :len(t)] = torch.tensor(t, dtype=torch.float32)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)
    def closure():
        opt.zero_grad()
        loss = -(T * torch.log_softmax(Z / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss
    opt.step(closure)
    return float(torch.clamp(log_t.exp(), 0.1, 10.0).item())

def main():
    ckpt, out = sys.argv[1], sys.argv[2]
    device = torch.device("cuda")
    with open(os.path.join(ckpt, "rl_agent_config.json")) as f:
        cfg = json.load(f)
    cfg["gradient_checkpointing"] = True
    tok = AutoTokenizer.from_pretrained(os.path.join(ckpt, "tokenizer"))
    model = build_model(cfg, encoder_dir=os.path.join(ckpt, "encoder"))
    model.load_state_dict(load_file(os.path.join(ckpt, "model.safetensors")), strict=True)
    model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.head_checkpointing = True
    model.to(device)
    model.train()
    train_items = torch.load("/content/train_items.pt", weights_only=False)
    calib_items = torch.load("/content/calib_items.pt", weights_only=False)
    EPOCHS, MICRO, ACCUM, G = 12, 4, 8, 4
    enc_p = [p for n, p in model.named_parameters() if "encoder." in n]
    head_p = [p for n, p in model.named_parameters() if "encoder." not in n]
    opt = torch.optim.AdamW([{"params": enc_p, "lr": 2.5e-5},
                             {"params": head_p, "lr": 1e-4}], weight_decay=0.01)
    total = (len(train_items) // (MICRO * ACCUM)) * EPOCHS
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, total), eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=True)
    print("train %d items, %d epochs (eff batch %d)" % (len(train_items), EPOCHS, MICRO * ACCUM), flush=True)
    t0 = time.time()
    for epoch in range(EPOCHS):
        random.seed(42 + epoch)
        random.shuffle(train_items)
        sig = 0.4 + (0.1 - 0.4) * epoch / max(1, EPOCHS - 1)
        opt.zero_grad(set_to_none=True)
        eloss, nb, acc = 0.0, 0, 0
        for b in range(0, len(train_items), MICRO):
            chunk = train_items[b:b + MICRO]
            if not chunk:
                continue
            bt = collate(chunk, tok.pad_token_id)
            with torch.autocast("cuda", dtype=torch.float16):
                logits, act = model(bt["input_ids"].to(device), bt["attention_mask"].to(device),
                                    bt["marker_pos"].to(device), bt["marker_mask"].to(device),
                                    bt["qtype"].to(device))
            logits = logits.float()
            mask = bt["marker_mask"].to(device)
            k = mask.sum(-1, keepdim=True).float()
            tgt = bt["target"].to(device)
            eps = torch.randn((G,) + logits.shape, device=device) * sig * mask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            z = logits.detach().unsqueeze(0) + eps
            q = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                r = proper_reward(q, tgt.unsqueeze(0), bt["qtype"].to(device), mask, w_sph=0.75, w_rps=1.0)
                adv = r - r.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sig ** 2)
            loss_rl = -(adv * logp).mean()
            loss_ce = -(tgt * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)).sum(-1).mean()
            loss = (loss_rl + 1.0 * loss_ce) / ACCUM
            scaler.scale(loss).backward()
            acc += 1
            if acc % ACCUM == 0 or (b + MICRO) >= len(train_items):
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt); scaler.update(); sch.step()
                opt.zero_grad(set_to_none=True)
            eloss += loss.item() * ACCUM
            nb += 1
        print("epoch %d/%d loss %.4f time %.0fs" % (epoch + 1, EPOCHS, eloss / max(1, nb), time.time() - t0), flush=True)
        cdir = os.path.join(out, "checkpoint_latest")
        os.makedirs(cdir, exist_ok=True)
        save_file({kk: vv.half().cpu() for kk, vv in model.state_dict().items()},
                  os.path.join(cdir, "model.safetensors"))
    model.eval()
    preds = []
    with torch.no_grad():
        for c in range(0, len(calib_items), 16):
            cb = collate(calib_items[c:c + 16], tok.pad_token_id)
            with torch.autocast("cuda", dtype=torch.float16):
                lsub, _ = model(cb["input_ids"].to(device), cb["attention_mask"].to(device),
                                cb["marker_pos"].to(device), cb["marker_mask"].to(device),
                                cb["qtype"].to(device))
            ln = lsub.float().cpu().numpy()
            for rr, it in enumerate(calib_items[c:c + 16]):
                kk = len(it["markers"])
                preds.append((it["qtype"], ln[rr, :kk], it["target"]))
    temps = []
    for qt in range(3):
        sel = [(z, t) for q, z, t in preds if q == qt]
        temps.append(fit_one_temp(sel) if sel else 1.2)
    print("fitted temps:", [round(x, 3) for x in temps])
    sd = {kk: vv.half().cpu() for kk, vv in model.state_dict().items()}
    save_file(sd, os.path.join(out, "model.safetensors"))
    model.encoder.config.save_pretrained(os.path.join(out, "encoder"))
    tok.save_pretrained(os.path.join(out, "tokenizer"))
    cfg["fine_tuned"] = True
    cfg["model_name"] = "laya-hinglish-cheap"
    cfg["temperature"] = temps
    cfg.pop("temperature_by_options", None)
    with open(os.path.join(out, "rl_agent_config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print("saved", out)

if __name__ == "__main__":
    main()
"""

cells = [
    MD("# Fine-tune Laya router on Hinglish cheap-vs-premium labels (Colab 1x T4)",
       "",
       "Single-GPU adaptation of upstream's `laya_finetune_typed_decisions_2xT4_kaggle` loop.",
       "",
       "**Before running:** upload to Google Drive folder `laya_ft/`:",
       "1. `laya_ckpt.zip` — your `D:/laya` (`model.safetensors`, `encoder/`, `tokenizer/`, `rl_agent_config.json`)",
       "2. `finetune/` — `train.jsonl` (140), `calib.jsonl` (30), `test.jsonl` (30), `QUESTION.json`",
       "",
       "Runtime: Colab **GPU (T4)**. Expected wall time: **~15-30 min**."),
    MD("## 1. GPU check"),
    CODE("!nvidia-smi --query-gpu=name,memory.total --format=csv",
         "import torch",
         "print('cuda:', torch.cuda.is_available(), '| gpus:', torch.cuda.device_count())",
         "assert torch.cuda.is_available(), 'Runtime -> Change runtime type -> GPU'"),
    MD("## 2. Install"),
    CODE("!pip install -q -U \"laya>=0.1.6\" \"transformers>=4.48.0\" safetensors huggingface_hub pandas scipy accelerate tabulate",
         "import laya",
         "print('laya:', laya.__version__)"),
    MD("## 3. Mount Drive, unpack checkpoint + pack"),
    CODE("from google.colab import drive",
         "drive.mount('/content/drive')",
         "import os, zipfile, json",
         "FT = '/content/drive/MyDrive/laya_ft'",
         "CKPT = '/content/laya_ckpt'",
         "os.makedirs(CKPT, exist_ok=True)",
         "assert os.path.exists(f'{FT}/laya_ckpt.zip'), f'put laya_ckpt.zip in {FT}'",
         "assert os.path.exists(f'{FT}/finetune/train.jsonl'), f'put finetune/ in {FT}'",
         "with zipfile.ZipFile(f'{FT}/laya_ckpt.zip') as z:",
         "    z.extractall(CKPT)",
         "print(os.listdir(CKPT))",
         "with open(f'{CKPT}/rl_agent_config.json') as f:",
         "    print('base temps:', json.load(f).get('temperature'))"),
    MD("## 4. Build training items with laya's own tokenizer pipeline"),
    CODE("import json",
         "from transformers import AutoTokenizer",
         "from laya.agent import _fix_tokenizer_config",
         "from laya.common import build_sequence, QTYPES",
         "_fix_tokenizer_config(CKPT)",
         "tok = AutoTokenizer.from_pretrained(os.path.join(CKPT, 'tokenizer'))",
         "with open(os.path.join(CKPT, 'rl_agent_config.json')) as f:",
         "    cfg = json.load(f)",
         "with open(f'{FT}/finetune/QUESTION.json') as f:",
         "    Q = json.load(f)",
         "KEYS = list(Q['criteria'].keys())",
         "QDEF = {'t': Q['type'], 'ins': Q['instructions'], 'crit': Q['criteria']}",
         "def to_item(prompt, gold):",
         "    target = [1.0 if k == gold else 0.0 for k in KEYS]",
         "    seq, markers = build_sequence(tok, prompt, QDEF, cfg['max_len'], cfg['head_max_len'])",
         "    if len(markers) != len(KEYS):",
         "        return None",
         "    return {'ids': seq, 'markers': markers, 'qtype': QTYPES['choice'],",
         "            'target': target, 'label': target.index(max(target))}",
         "import torch",
         "for split in ['train', 'calib', 'test']:",
         "    rows = [json.loads(l) for l in open(f'{FT}/finetune/{split}.jsonl', encoding='utf-8')]",
         "    items = [it for r in rows if (it := to_item(r['prompt'], r['gold']))]",
         "    torch.save(items, f'/content/{split}_items.pt')",
         "    print(split, f'{len(items)}/{len(rows)} items kept')"),
    MD("## 5. Write single-GPU training script"),
    CODE("%%writefile /content/train_single.py", *TRAIN.splitlines()),
    MD("## 6. Train (~15-30 min on T4)"),
    CODE("!python /content/train_single.py /content/laya_ckpt /content/laya_ft_out"),
    MD("## 7. Before/after eval on held-out test 30"),
    CODE("import json",
         "import laya",
         "from laya.common import ece_score",
         "import numpy as np",
         "with open('/content/drive/MyDrive/laya_ft/finetune/QUESTION.json') as f:",
         "    Q = json.load(f)",
         "QS = {'cheap': {'type': Q['type'], 'instructions': Q['instructions'], 'criteria': Q['criteria']}}",
         "test = [json.loads(l) for l in open('/content/drive/MyDrive/laya_ft/finetune/test.jsonl', encoding='utf-8')]",
         "def evaluate(agent):",
         "    correct, confs = [], []",
         "    for row in test:",
         "        a = agent.predict(row['prompt'], QS)['answers']['cheap']",
         "        probs = a.get('probabilities', {})",
         "        ok = float(a['choice'] == row['gold'])",
         "        correct.append(ok)",
         "        confs.append(float(max(probs.values())) if probs else 0.5)",
         "    return float(np.mean(correct)), float(ece_score(np.array(confs), np.array(correct)))",
         "base = laya.Agent('/content/laya_ckpt', device='cuda')",
         "ft = laya.Agent('/content/laya_ft_out', device='cuda')",
         "ab, eb = evaluate(base)",
         "af, ef = evaluate(ft)",
         "print(f'BASE      acc={ab:.3f} ece={eb:.3f}')",
         "print(f'FINETUNED acc={af:.3f} ece={ef:.3f}')",
         "print('GO' if af > ab + 0.05 else 'REVIEW - gain too small')"),
    MD("## 8. Bring it home",
       "",
       "1. Download from `/content/laya_ft_out`: `model.safetensors` + `rl_agent_config.json`",
       "2. Locally: back up `D:/laya` to `D:/laya_backup_pre_hinglish`, then swap the two files in",
       "3. Re-run your 200 prompts through the swapped router, recompute agreement vs Claude",
       "4. If held-out agreement stays under ~0.70: stop tuning, go manual-labeling fallback (stratified 300-500 subset, same Qwen + premium + Claude loop)"),
]

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python3"}},
      "nbformat": 4, "nbformat_minor": 4}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote", OUT, "cells:", len(cells))
