"""
judge.py — LLM-as-a-Judge Module (Gemini, strict JSON).

For each row in SQLite where acceptable IS NULL:
  - send (prompt, premium_baseline, qwen_candidate) to Gemini
  - generationConfig.response_mime_type = "application/json"
  - parse {"acceptable": 0|1} -> update DB

Usage:
    pip install aiohttp
    $env:GEMINI_API_KEY="..."
    python judge.py --db cascade.db --limit 200 --workers 6
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sqlite3
import sys

try:
    import aiohttp
except ImportError:
    print("Missing dep: pip install aiohttp", file=sys.stderr)
    raise

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

JUDGE_SYSTEM = """You are a strict evaluator for Hinglish (Romanized Hindi-English) responses.
Compare CANDIDATE (local Qwen 7B) against BASELINE (premium Gemini).
Mark acceptable=1 ONLY if candidate is factually faithful and semantically adequate:
- same conclusion / answer, no hallucinated facts, no flipped numbers/names
- Hinglish or English both OK, grammar slips OK if meaning intact
- if baseline says unknown/refuses, candidate must also refuse/hedge, not invent
Otherwise acceptable=0.
Return STRICT JSON only: {"acceptable": 1} or {"acceptable": 0}"""


def build_payload(prompt: str, baseline: str, candidate: str) -> dict:
    user = (
        f"PROMPT:\n{prompt}\n\nBASELINE (premium):\n{baseline}\n\n"
        f"CANDIDATE (qwen 7B):\n{candidate}\n\nReturn JSON only."
    )
    return {
        "system_instruction": {"parts": [{"text": JUDGE_SYSTEM}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.0},
    }


async def judge_one(session: aiohttp.ClientSession, prompt, baseline, candidate, sem) -> int | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    async with sem:
        async with session.post(url, json=build_payload(prompt, baseline, candidate),
                                timeout=aiohttp.ClientTimeout(total=90)) as r:
            r.raise_for_status()
            data = await r.json()
            try:
                txt = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return None
    try:
        obj = json.loads(txt)
        v = int(obj.get("acceptable", -1))
        return v if v in (0, 1) else None
    except Exception:
        # try to salvage trailing {"acceptable": X}
        import re
        m = re.search(r'"acceptable"\s*:\s*([01])', txt)
        return int(m.group(1)) if m else None


async def run_async(db: str, limit: int | None, workers: int):
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL;")
    q = "SELECT id, prompt, gemini_response, qwen_response FROM responses WHERE acceptable IS NULL AND qwen_response IS NOT NULL AND gemini_response IS NOT NULL"
    if limit:
        q += f" LIMIT {int(limit)}"
    rows = con.execute(q).fetchall()
    con.close()
    print(f"to_judge={len(rows)}")
    if not rows:
        return
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    sem = asyncio.Semaphore(workers)
    con = sqlite3.connect(db, timeout=60)
    ok0 = ok1 = fail = 0
    async with aiohttp.ClientSession() as session:
        chunk = max(8, workers * 4)
        for i in range(0, len(rows), chunk):
            batch = rows[i : i + chunk]
            tasks = [judge_one(session, p, g, qwen, sem) for (_id, p, g, qwen) in batch]
            labels = await asyncio.gather(*tasks, return_exceptions=True)
            for (_id, *_), lab in zip(batch, labels):
                if isinstance(lab, Exception) or lab is None:
                    fail += 1
                    continue
                con.execute("UPDATE responses SET acceptable=? WHERE id=?", (int(lab), _id))
                if lab == 1:
                    ok1 += 1
                else:
                    ok0 += 1
            con.commit()
            print(f"[{i+len(batch)}/{len(rows)}] accept=1:{ok1} accept=0:{ok0} fail:{fail}")
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="cascade.db")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    asyncio.run(run_async(a.db, a.limit, a.workers))


if __name__ == "__main__":
    main()
