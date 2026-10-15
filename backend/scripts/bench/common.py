"""Shared plumbing for the paired English/Hinglish routing benchmark.

Everything lands under backend/data/bench/ as append-only JSONL so every run is
resumable and every number in a report can be traced to raw rows.

Provider calls: one API key per provider (never rotate accounts to dodge rate
limits — Groq limits are per organisation), honour Retry-After, and stop for
the day when the per-model token budget in the ledger is spent.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND / "src"))
BENCH = BACKEND / "data" / "bench"
BENCH.mkdir(parents=True, exist_ok=True)

ITEMS = BENCH / "items.jsonl"  # one row per source item (English + gold)
VARIANTS = BENCH / "variants.jsonl"  # one row per (item, language variant)
ANSWERS = BENCH / "answers.jsonl"  # one row per (item, lang, tier) model call
GRADES = BENCH / "grades.jsonl"  # one row per (item, lang): both tiers graded
LEDGER = BENCH / "ledger.json"  # tokens spent per model per UTC day

SEED = 20261015
# Split by source item so every language variant of an item stays together.
SPLIT_SHARES = (("scorer_train", 0.30), ("pilot", 0.10), ("cert", 0.60))


def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(BACKEND / ".env")
    except ImportError:
        pass


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def latest_variants() -> list[dict]:
    """Last row per (item, language): re-translations supersede failed attempts."""
    last: dict[tuple, dict] = {}
    for v in read_jsonl(VARIANTS):
        last[(v["item_id"], v["lang"])] = v
    return list(last.values())


def variant_ok(v: dict) -> bool:
    return v["lang"] == "english" or all(v["checks"].values())


def in_shard(item_id: str, shard: str | None) -> bool:
    """--shard i/n lets each teammate run a disjoint slice with their own key."""
    if not shard:
        return True
    i, n = (int(x) for x in shard.split("/"))
    return int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % n == i - 1


def split_for(item_id: str) -> str:
    """Deterministic split from a hash of the source item id (seeded)."""
    h = int(hashlib.sha256(f"{SEED}|{item_id}".encode()).hexdigest(), 16) / 2**256
    acc = 0.0
    for name, share in SPLIT_SHARES:
        acc += share
        if h < acc:
            return name
    return SPLIT_SHARES[-1][0]


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ledger() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def tokens_spent_today(model: str) -> int:
    return int(_ledger().get(today(), {}).get(model, 0))


def record_tokens(model: str, n: int) -> None:
    led = _ledger()
    day = led.setdefault(today(), {})
    day[model] = int(day.get(model, 0)) + int(n)
    LEDGER.write_text(json.dumps(led, indent=2))


class BudgetExhausted(RuntimeError):
    pass


def chat(
    model: str,
    messages: list[dict],
    *,
    base_url: str,
    api_key: str,
    max_tokens: int,
    daily_token_budget: int,
    reasoning_effort: str | None = "low",
    max_retries: int = 6,
) -> dict:
    """One chat completion with Retry-After-aware backoff and a daily token cap."""
    import httpx

    if tokens_spent_today(model) >= daily_token_budget:
        raise BudgetExhausted(f"{model}: daily budget {daily_token_budget} tokens spent")
    payload: dict = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
    if reasoning_effort and "gpt-oss" in model:
        payload["reasoning_effort"] = reasoning_effort
    headers = {
        "Authorization": f"Bearer {api_key}",
        # Groq sits behind Cloudflare; urllib-style clients get 403/1010 (DECISIONS.md §3b).
        "User-Agent": "Mozilla/5.0 (research benchmark; contact: repo owner)",
    }
    delay = 2.0
    for attempt in range(max_retries):
        try:
            r = httpx.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers, timeout=120)
        except httpx.HTTPError as e:
            last = f"transport: {e}"
        else:
            if r.status_code == 200:
                data = r.json()
                usage = data.get("usage") or {}
                record_tokens(model, usage.get("total_tokens", 0))
                msg = data["choices"][0]["message"]
                return {
                    "content": msg.get("content") or "",
                    "reasoning": msg.get("reasoning") or "",
                    "finish_reason": data["choices"][0].get("finish_reason"),
                    "usage": usage,
                    "model_returned": data.get("model", model),
                }
            last = f"http {r.status_code}: {r.text[:200]}"
            if r.status_code in (401, 403, 404):
                raise RuntimeError(last)
            retry_after = r.headers.get("retry-after")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
        time.sleep(delay + random.random())
        delay = min(delay * 2, 120)
    raise RuntimeError(f"gave up after {max_retries} attempts: {last}")


def provider(tier: str) -> dict:
    """Model + endpoint for a tier, from backend/.env (GATEWAY_CHEAP__*, GATEWAY_PREMIUM__*)."""
    load_env()
    prefix = f"GATEWAY_{tier.upper()}__"
    model = os.environ.get(prefix + "MODEL", "")
    key = os.environ.get(prefix + "API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
    url = os.environ.get(prefix + "BASE_URL", "https://api.groq.com/openai/v1")
    if not model or not key:
        raise SystemExit(f"Set {prefix}MODEL and {prefix}API_KEY in backend/.env")
    return {"model": model, "api_key": key, "base_url": url}
