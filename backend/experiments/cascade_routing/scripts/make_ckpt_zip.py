"""make_ckpt_zip.py — Build the Colab upload artifact from D:/laya.

Includes only what laya.Agent needs (mirrors its loader):
  model.safetensors, encoder/config.json, tokenizer/*, rl_agent_config.json
Excludes: .cache, assets, eval, multilingual, typed-decisions, *.py, README.
Output: D:/Programming/laya_ckpt.zip (ZIP_STORED — safetensors don't compress).
"""
import os, zipfile
SRC = r"D:\laya"
DST = r"D:\Programming\laya_ckpt.zip"
WANT = ["model.safetensors", "rl_agent_config.json",
        "encoder/config.json",
        "tokenizer/tokenizer.json", "tokenizer/tokenizer_config.json"]
# tokenizer dir may hold more (e.g. special_tokens_map); include whole dir if small
extra = []
tokdir = os.path.join(SRC, "tokenizer")
for f in sorted(os.listdir(tokdir)):
    p = f"tokenizer/{f}"
    if p not in WANT:
        extra.append(p)
print("tokenizer extra files:", extra)
files = WANT + extra
missing = [p for p in files if not os.path.exists(os.path.join(SRC, p))]
if missing:
    raise SystemExit(f"MISSING: {missing}")
if os.path.exists(DST):
    os.remove(DST)
with zipfile.ZipFile(DST, "w", zipfile.ZIP_STORED) as z:
    for p in files:
        z.write(os.path.join(SRC, p), p)
        print("added", p)
print("OK ->", DST, f"{os.path.getsize(DST)/1e9:.2f} GB")
