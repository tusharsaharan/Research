"""Kaggle script entry point; source and inputs come from the private dataset."""
import glob
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import zipfile

started = time.time()
deadline = started + 3300
os.environ["COMPRESSOR_DEADLINE"] = str(deadline)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "llmlingua==0.2.2", "transformers==4.57.1",
                "accelerate>=0.34,<2", "tiktoken", "pydantic>=2", "scipy", "sentencepiece"], check=True, timeout=300)
sources = glob.glob("/kaggle/input/**/source.zip", recursive=True)
if len(sources) != 1:
    raise RuntimeError("Attach exactly one compressor pilot dataset")
data = pathlib.Path(sources[0]).parent
manifest = json.loads((data / "manifest.json").read_text())
if hashlib.sha256(pathlib.Path(sources[0]).read_bytes()).hexdigest() != manifest["source_sha256"]:
    raise RuntimeError("Source bundle fingerprint mismatch")
root = pathlib.Path("/kaggle/working/pilot_source")
with zipfile.ZipFile(sources[0]) as bundle:
    bundle.extractall(root)
os.environ["PYTHONPATH"] = str(root / "src")
script = str(root / "scripts/bench/compressor_pilot.py")
try:
    subprocess.run([sys.executable, "-u", script, "gpu", "--data", str(data),
                    "--out", "/kaggle/working"], check=True, timeout=max(1, deadline - time.time()))
finally:
    # Report partial coverage even when a dependency, model or time cap fails.
    subprocess.run([sys.executable, script, "grade", "--data", str(data), "--out", "/kaggle/working"],
                   check=False, timeout=30)
