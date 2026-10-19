"""Answer the shared prompt file (kaggle/prompts.jsonl) with an API model, resumable.

Keys come from GEMINI_API_KEY / OPENAI_API_KEY (process env, else the Windows user
environment set by `setx`); they are never printed or written anywhere.
Output rows use the same schema as the Kaggle answers (key, item_id, lang, methods,
model, content, prompt_tokens, completion_tokens), plus the exact model version
the provider reports, in data/bench/api/<model>.jsonl.

    python api_answer.py --list-models gemini
    python api_answer.py --provider gemini --model gemini-2.5-flash --task condaqa --limit 50
    python api_answer.py --provider openai --model gpt-5-mini --task condaqa --max-tokens-total 2000000
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from pathlib import Path
from common import BENCH, read_jsonl

PROMPTS = BENCH / "kaggle" / "prompts.jsonl"
OUT = BENCH / "api"
ENV = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


def key(provider: str) -> str:
    """The value saved with `setx` wins: this process may hold an older copy."""
    name = ENV[provider]
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        pass
    if os.environ.get(name):
        return os.environ[name]
    raise SystemExit(f"{name} is not set")


GEMINI_URLS = ("https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
               "https://aiplatform.googleapis.com/v1/publishers/google/models/{m}:generateContent")  # AI Studio, Vertex express


def call_gemini(client: httpx.Client, k: str, model: str, system: str, prompt: str, max_out: int, url_i: list[int]) -> dict:
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_out}}
    if model.startswith("gemini-2.5"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0 if "flash" in model else 512}
    elif model.startswith("gemini"):  # 3.x: thinking levels
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
    r = client.post(GEMINI_URLS[url_i[0]].format(m=model), headers={"x-goog-api-key": k}, json=body)
    if r.status_code in (401, 403, 404) and url_i[0] == 0:  # key type belongs to the other endpoint
        url_i[0] = 1
        r = client.post(GEMINI_URLS[1].format(m=model), headers={"x-goog-api-key": k}, json=body)
    r.raise_for_status()
    j = r.json()
    parts = j.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    u = j.get("usageMetadata", {})
    return {"content": "".join(p.get("text", "") for p in parts if not p.get("thought")),
            "model_version": j.get("modelVersion", model),
            "prompt_tokens": u.get("promptTokenCount", 0),
            "completion_tokens": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)}


def call_openai(client: httpx.Client, k: str, model: str, system: str, prompt: str, max_out: int, _=None) -> dict:
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_completion_tokens": max_out}
    if model.startswith(("gpt-5", "o")):
        body["reasoning_effort"] = "low" if model.startswith("o") else "minimal"
    else:
        body["temperature"] = 0
    r = client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {k}"}, json=body)
    r.raise_for_status()
    j = r.json()
    u = j.get("usage", {})
    return {"content": j["choices"][0]["message"].get("content") or "", "model_version": j.get("model", model),
            "prompt_tokens": u.get("prompt_tokens", 0), "completion_tokens": u.get("completion_tokens", 0)}


def list_models(provider: str) -> None:
    k = key(provider)
    if provider == "openai":
        r = httpx.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=30)
        r.raise_for_status()
        print(sorted(m["id"] for m in r.json()["data"] if m["id"].startswith(("gpt", "o"))))
        return
    r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": k}, timeout=30)
    if r.status_code != 200:
        print("AI Studio listing not allowed for this key (HTTP", r.status_code, ") - probably a Vertex express key")
        return
    print(sorted(m["name"].split("/")[-1] for m in r.json()["models"] if "generateContent" in m.get("supportedGenerationMethods", [])))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-models", choices=list(ENV))
    ap.add_argument("--provider", choices=list(ENV))
    ap.add_argument("--model")
    ap.add_argument("--prompts", default=str(PROMPTS), help="prompt file (default: kaggle/prompts.jsonl)")
    ap.add_argument("--task", help="only prompts of this task (condaqa, math, mcq)")
    ap.add_argument("--methods", help="comma list; keep prompts carrying any of these methods")
    ap.add_argument("--limit", type=int, default=0, help="random sample of N items (all their variants)")
    ap.add_argument("--ids", help="file with one item_id per line (overrides --limit)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-out", type=int, default=512)
    ap.add_argument("--max-tokens-total", type=int, default=0, help="stop after this many tokens (in+out) this run")
    a = ap.parse_args()
    if a.list_models:
        return list_models(a.list_models)
    k = key(a.provider)
    rows = read_jsonl(Path(a.prompts))
    if a.task:
        rows = [r for r in rows if r["task"] == a.task]
    if a.methods:
        want = set(a.methods.split(","))
        rows = [r for r in rows if want & set(r["methods"])]
    if a.ids:
        keep = set(open(a.ids, encoding="utf-8").read().split())
        rows = [r for r in rows if r["item_id"] in keep]
    elif a.limit:
        ids = sorted({r["item_id"] for r in rows})
        keep = set(random.Random(20261018).sample(ids, min(a.limit, len(ids))))
        rows = [r for r in rows if r["item_id"] in keep]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.model}.jsonl"
    done = {r["key"] for r in read_jsonl(path)} if path.exists() else set()
    todo = [r for r in rows if r["key"] not in done]
    print(f"{len(rows)} prompts selected, {len(done & {r['key'] for r in rows})} done, {len(todo)} to go", flush=True)
    fn = call_gemini if a.provider == "gemini" else call_openai
    lock, spent, stop, errors = threading.Lock(), [0], threading.Event(), [0]
    url_i = [0]
    client = httpx.Client(timeout=600)

    def work(r: dict) -> None:
        if stop.is_set():
            return
        for attempt in range(8):
            try:
                out = fn(client, k, a.model, r["system"], r["prompt"], a.max_out, url_i)
                break
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if "insufficient_quota" in e.response.text or "PerDay" in e.response.text:
                    print("no credits / daily quota left - stopping (resume tomorrow or enable billing)", flush=True)
                    stop.set()
                    return
                if code in (429, 500, 502, 503, 504):
                    time.sleep(min(120, 5 * 2**attempt) * (0.5 + random.random()))
                    continue
                with lock:
                    errors[0] += 1
                    if errors[0] <= 3:
                        print("HTTP", code, e.response.text[:300].replace(k, "***"), flush=True)
                    if errors[0] >= 20:
                        stop.set()
                return
            except httpx.TransportError:
                time.sleep(5 * 2**attempt)
        else:
            return
        row = {kk: r[kk] for kk in ("key", "item_id", "lang", "methods")} | {"model": a.model, **out}
        with lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            spent[0] += out["prompt_tokens"] + out["completion_tokens"]
            if a.max_tokens_total and spent[0] >= a.max_tokens_total:
                stop.set()

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    n = len(read_jsonl(path))
    print(f"done: {n} answers in {path.name}; tokens this run {spent[0]:,}; errors {errors[0]}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
