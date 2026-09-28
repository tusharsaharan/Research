"""make_ckpt_zip_ft.py — Zip the CURRENT (fine-tuned) D:/laya for Colab upload."""
import os, zipfile
SRC = r"D:\laya"
DST = r"D:\Programming\laya_ckpt_ft.zip"
files = ["model.safetensors", "rl_agent_config.json", "encoder/config.json"]
tokdir = os.path.join(SRC, "tokenizer")
for f in sorted(os.listdir(tokdir)):
    files.append(f"tokenizer/{f}")
missing = [p for p in files if not os.path.exists(os.path.join(SRC, p))]
if missing:
    raise SystemExit(f"MISSING: {missing}")
if os.path.exists(DST):
    os.remove(DST)
with zipfile.ZipFile(DST, "w", zipfile.ZIP_STORED) as z:
    for p in files:
        z.write(os.path.join(SRC, p), p)
print("OK ->", DST, f"{os.path.getsize(DST)/1e9:.2f} GB")
