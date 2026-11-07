"""Live demo: heuristic (fixed drops) vs rewrite (understanding) side by side."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from gateway.llm import OpenAIClient  # noqa: E402
from gateway.modules.m2_compressor.compressor import Compressor  # noqa: E402
from gateway.tokenizer import TokenCounter  # noqa: E402
import os

QUERIES = [
    "bhai mera hostel ka wifi slow hai, complaint kahan karun? kal se assignment submit karna hai",
    "arre yaar payment fail ho gaya par paise deduct ho gaye, Rs. 2,500 ka kya karun?",
    "medical leave kaise apply karni hai, certificate kahan submit karna hai? sun na",
    "ek react component me state update nahi ho raha, kya bug ho sakta hai? samjha do thoda simple me",
    "yaar kal chutti hai kya college me, koi notice aaya hai kya? batao na",
]


async def main() -> None:
    key = (os.environ.get("GROQ_API_KEYS", "") or os.environ.get("GROQ_API_KEY", "")).split(",")[0].strip()
    assert key, "set GROQ_API_KEYS"
    client = OpenAIClient(model="openai/gpt-oss-20b", base_url="https://api.groq.com/openai/v1",
                          api_key=key, timeout=60.0)
    comp = Compressor(TokenCounter(), client=client, use_model=True)
    for q in QUERIES:
        h = comp.compress_heuristic(q)
        live = await comp.compress(q)
        print("Q:  ", q)
        print(f"HEU [{h.method} ratio={h.ratio}]: {h.compressed}")
        print(f"LIVE[{live.method} ratio={live.ratio}]: {live.compressed}")
        print("-" * 100)


asyncio.run(main())
