"""judge_200.py — Gemini-as-judge over judge_input_200.csv -> judged_200.csv.

Resumable: appends, skips prompts already judged. Strict JSON {"acceptable":0/1}.
Usage: python scripts/judge_200.py [--workers 4]
Needs GEMINI_API_KEY (+ HTTPS_PROXY in this sandbox) in env.
"""
import argparse, asyncio, csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from judge import build_payload, GEMINI_MODEL, GEMINI_API_KEY  # noqa: E402

try:
    import aiohttp
except ImportError:
    sys.exit("pip install aiohttp")

DATA = os.path.join(HERE, "..", "data")
INP = os.path.join(DATA, "judge_input_200.csv")
OUT = os.path.join(DATA, "judged_200.csv")

async def judge_one(session, prompt, baseline, candidate, sem):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    async with sem:
        async with session.post(url, json=build_payload(prompt, baseline, candidate),
                                timeout=aiohttp.ClientTimeout(total=90)) as r:
            r.raise_for_status()
            data = await r.json()
            txt = data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        v = int(json.loads(txt).get("acceptable", -1))
        return v if v in (0, 1) else None
    except Exception:
        m = re.search(r'"acceptable"\s*:\s*([01])', txt)
        return int(m.group(1)) if m else None

async def main(workers):
    rows = list(csv.DictReader(open(INP, encoding="utf-8")))
    done = set()
    if os.path.exists(OUT):
        done = {r["prompt"] for r in csv.DictReader(open(OUT, encoding="utf-8")) if r.get("acceptable") in ("0", "1")}
    todo = [r for r in rows if r["prompt"] not in done]
    print(f"total={len(rows)} done={len(done)} todo={len(todo)} model={GEMINI_MODEL}", flush=True)
    if not GEMINI_API_KEY:
        sys.exit("GEMINI_API_KEY not set")
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["acceptable"], quoting=csv.QUOTE_ALL)
    if not done:
        w.writeheader()
    sem = asyncio.Semaphore(workers)
    ok = 0
    async with aiohttp.ClientSession() as session:
        for i, r in enumerate(todo):
            try:
                lab = await judge_one(session, r["prompt"], r["premium_response"], r["qwen_response"], sem)
            except Exception as e:
                print(f"[{i+1}/{len(todo)}] ERROR {type(e).__name__}: {str(e)[:120]}", flush=True)
                continue
            if lab is None:
                print(f"[{i+1}/{len(todo)}] UNPARSEABLE :: {r['prompt'][:60]}", flush=True)
                continue
            w.writerow({**r, "acceptable": lab})
            f.flush()
            ok += 1
            print(f"[{i+1}/{len(todo)}] ok={ok} acceptable={lab} :: {r['prompt'][:60]}", flush=True)
    f.close()
    print(f"judge done ok={ok}/{len(todo)}", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    asyncio.run(main(ap.parse_args().workers))
