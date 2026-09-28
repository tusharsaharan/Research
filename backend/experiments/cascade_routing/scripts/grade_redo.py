"""grade_redo.py — Gemini-grade the 21 uncapped redos vs premium (same rubric as judge.py).

Writes data/redo_graded.csv: prompt, qwen_uncapped, premium_response, acceptable, grader.
CAVEAT: original 200 were Claude-graded; these 21 are Gemini-graded (same rubric text).
Usage: python scripts/grade_redo.py [--workers 2]
"""
import argparse, asyncio, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from judge_200 import judge_one  # noqa: E402

DATA = os.path.join(HERE, "..", "data")

async def main(workers):
    redo = list(csv.DictReader(open(os.path.join(DATA, "qwen_redo_uncapped.csv"), encoding="utf-8")))
    prem = {r["prompt"]: r["premium_response"] for r in csv.DictReader(open(os.path.join(DATA, "judge_output_200.csv"), encoding="utf-8-sig"))}
    done = set()
    out = os.path.join(DATA, "redo_graded.csv")
    if os.path.exists(out):
        done = {r["prompt"] for r in csv.DictReader(open(out, encoding="utf-8")) if r.get("acceptable") in ("0", "1")}
    todo = [r for r in redo if r["prompt"] not in done]
    print(f"total={len(redo)} done={len(done)} todo={len(todo)}", flush=True)
    f = open(out, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=["prompt", "qwen_uncapped", "premium_response", "acceptable", "grader"], quoting=csv.QUOTE_ALL)
    if not done:
        w.writeheader()
    import aiohttp
    sem = asyncio.Semaphore(workers)
    ok = 0
    async with aiohttp.ClientSession() as session:
        for i, r in enumerate(todo):
            try:
                lab = await judge_one(session, r["prompt"], prem[r["prompt"]], r["qwen_uncapped"], sem)
            except Exception as e:
                print(f"[{i+1}/{len(todo)}] ERROR {type(e).__name__}: {str(e)[:100]}", flush=True)
                continue
            if lab is None:
                print(f"[{i+1}/{len(todo)}] UNPARSEABLE :: {r['prompt'][:60]}", flush=True)
                continue
            w.writerow({"prompt": r["prompt"], "qwen_uncapped": r["qwen_uncapped"],
                        "premium_response": prem[r["prompt"]], "acceptable": lab, "grader": "gemini-3.8-flash"})
            f.flush()
            ok += 1
            print(f"[{i+1}/{len(todo)}] ok={ok} acceptable={lab} :: {r['prompt'][:60]}", flush=True)
    f.close()
    print(f"grade done ok={ok}/{len(todo)}", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    asyncio.run(main(ap.parse_args().workers))
