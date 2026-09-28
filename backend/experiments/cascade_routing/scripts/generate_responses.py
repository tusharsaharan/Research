"""
generate_responses.py — Dual-Execution Pipeline (async).

- Local (cheap): Ollama  http://localhost:11434/api/generate  model qwen2.5:7b
- Premium:       Gemini  model gemini-2.5-flash via REST (GOOGLE/GEMINI_API_KEY)
- Storage:       SQLite in WAL mode, resume-safe.

Schema (created if missing):
    responses(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      prompt TEXT UNIQUE,
      cm REAL, ed REAL, mm REAL, llen REAL, d REAL,
      qwen_response TEXT, gemini_response TEXT,
      acceptable INTEGER NULL,  -- filled by judge.py
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )

Usage:
    pip install aiohttp
    set GEMINI_API_KEY=...   (Windows: $env:GEMINI_API_KEY="...")
    python generate_responses.py --input prompts_scored.csv --db cascade.db --limit 100
    python generate_responses.py --input prompts_scored.csv --db cascade.db --workers 8
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import json
import os
import sqlite3
import sys

try:
    import aiohttp
except ImportError:
    print("Missing dep: pip install aiohttp", file=sys.stderr)
    raise

from difficulty import difficulty

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:latest")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

DB_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS responses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prompt TEXT UNIQUE,
  cm REAL, ed REAL, mm REAL, llen REAL, d REAL,
  qwen_response TEXT,
  gemini_response TEXT,
  acceptable INTEGER NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.executescript(DB_SCHEMA)
    con.commit()
    con.close()


def already_done(db: str) -> set[str]:
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT prompt FROM responses WHERE qwen_response IS NOT NULL AND gemini_response IS NOT NULL"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    return {r[0] for r in rows}


async def ollama_generate(session: aiohttp.ClientSession, prompt: str, sem: asyncio.Semaphore) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
               "options": {"num_predict": 256}}
    async with sem:
        # proxy=None: bypass corp proxy for localhost (else 504)
        async with session.post(OLLAMA_URL, json=payload, timeout=aiohttp.ClientTimeout(total=300), proxy=None) as r:
            r.raise_for_status()
            data = await r.json()
            return (data.get("response") or "").strip()


async def gemini_generate(session: aiohttp.ClientSession, prompt: str, sem: asyncio.Semaphore) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with sem:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as r:
            r.raise_for_status()
            data = await r.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError):
                return json.dumps(data)[:4000]


async def process_one(session, prompt, feats, sem_ollama, sem_gemini):
    qwen_task = asyncio.create_task(ollama_generate(session, prompt, sem_ollama))
    gem_task = asyncio.create_task(gemini_generate(session, prompt, sem_gemini))
    qwen_resp, gem_resp = await asyncio.gather(qwen_task, gem_task, return_exceptions=True)
    if isinstance(qwen_resp, Exception):
        raise qwen_resp  # local must succeed; else retry later
    if isinstance(gem_resp, Exception):
        gem_resp = f"__GEMINI_ERROR__ {type(gem_resp).__name__}: {str(gem_resp)[:300]}"
    return (prompt, feats, qwen_resp, gem_resp)


async def run_async(prompts: list[str], db: str, workers: int):
    # Sequential per prompt: Ollama -> INSERT immediately -> Gemini -> UPDATE.
    # A hung Gemini call can never trap an Ollama result; every row commits.
    sem_ollama = asyncio.Semaphore(max(1, workers))
    sem_gemini = asyncio.Semaphore(max(1, min(workers, 4)))
    con = sqlite3.connect(db, timeout=60)
    con.execute("PRAGMA journal_mode=WAL;")
    done, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for i, prompt in enumerate(prompts):
            feats = difficulty(prompt)
            try:
                qwen_resp = await ollama_generate(session, prompt, sem_ollama)
            except Exception as e:
                fail += 1
                print(f"[{i+1}/{len(prompts)}] ollama FAIL {type(e).__name__}: {str(e)[:150]}",
                      file=sys.stderr, flush=True)
                continue
            con.execute(
                """INSERT OR REPLACE INTO responses
                   (prompt, cm, ed, mm, llen, d, qwen_response)
                   VALUES (?,?,?,?,?,?,?)""",
                (prompt, feats["cm"], feats["ed"], feats["mm"], feats["l"], feats["d"], qwen_resp),
            )
            con.commit()
            try:
                gem_resp = await gemini_generate(session, prompt, sem_gemini)
            except Exception as e:
                gem_resp = f"__GEMINI_ERROR__ {type(e).__name__}: {str(e)[:200]}"
            con.execute("UPDATE responses SET gemini_response=? WHERE prompt=?", (gem_resp, prompt))
            con.commit()
            done += 1
            tag = "GEMINI_ERR" if gem_resp.startswith("__GEMINI_ERROR__") else "ok"
            print(f"[{i+1}/{len(prompts)}] saved={done} failed={fail} gemini={tag} :: {prompt[:60]}", flush=True)
    con.close()
    print(f"Done. saved={done} failed={fail}")


def load_prompts(path: str, limit: int | None) -> list[str]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        col = next((c for c in ["prompt", "instruction", "text"] if c in cols), cols[0])
        out = [(r.get(col) or "").strip() for r in reader]
    out = [p for p in out if p]
    # de-dup preserve order
    out = list(dict.fromkeys(out))
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="prompts_scored.csv")
    ap.add_argument("--db", default="cascade.db")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set — Gemini calls will fail.", file=sys.stderr)

    init_db(a.db)
    prompts = load_prompts(a.input, a.limit)
    skip = already_done(a.db)
    todo = [p for p in prompts if p not in skip]
    print(f"total={len(prompts)} already_done={len(skip)} todo={len(todo)}")
    if not todo:
        print("Nothing to do.")
        return
    asyncio.run(run_async(todo, a.db, a.workers))


if __name__ == "__main__":
    main()
