"""run_qwen.py — Local-only pass: Ollama qwen2.5 -> qwen_responses.csv (resumable).

Usage:
    python run_qwen.py --n 50            # do next 50 prompts
    python run_qwen.py --n 500 --predict 256
Output: qwen_responses.csv (prompt,cm,ed,mm,l,d,qwen_response), appends, skips done.
"""
import argparse, csv, http.client, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difficulty import difficulty

OUT = "qwen_responses.csv"
FIELDS = ["prompt", "cm", "ed", "mm", "l", "d", "qwen_response"]

def done_set():
    if not os.path.exists(OUT):
        return set()
    with open(OUT, encoding="utf-8", newline="") as f:
        return {r["prompt"] for r in csv.DictReader(f) if r.get("qwen_response")}

def ask(prompt, predict):
    body = json.dumps({"model": os.environ.get("OLLAMA_MODEL", "qwen2.5:latest"),
                       "prompt": prompt, "stream": False,
                       "keep_alive": "30m",
                       "options": {"num_predict": predict}})
    last = ""
    for _ in range(2):
        try:
            c = http.client.HTTPConnection("localhost", 11434, timeout=300)
            c.request("POST", "/api/generate", body=body, headers={"Content-Type": "application/json"})
            r = c.getresponse()
            if r.status != 200:
                last = f"HTTP {r.status}"
                continue
            return (json.loads(r.read().decode()).get("response") or "").strip()
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    raise RuntimeError(last)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--predict", type=int, default=512)
    ap.add_argument("--input", default="prompts.csv")
    a = ap.parse_args()
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        col = next((c for c in ["prompt", "instruction", "text"] if c in rdr.fieldnames), rdr.fieldnames[0])
        allp = list(dict.fromkeys((r.get(col) or "").strip() for r in rdr))
    allp = [p for p in allp if p]
    done = done_set()
    todo = [p for p in allp if p not in done][:a.n]
    print(f"total={len(allp)} done={len(done)} todo_now={len(todo)}", flush=True)
    new = os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
    if not new:
        w.writeheader()
    ok = 0
    for i, p in enumerate(todo):
        try:
            resp = ask(p, a.predict)
            s = difficulty(p)
            w.writerow({"prompt": p, "cm": s["cm"], "ed": s["ed"], "mm": s["mm"],
                        "l": s["l"], "d": s["d"], "qwen_response": resp})
            f.flush()
            ok += 1
            print(f"[{i+1}/{len(todo)}] ok={ok} d={s['d']} len={len(resp)} :: {p[:60]}", flush=True)
        except Exception as e:
            print(f"[{i+1}/{len(todo)}] FAIL :: {p[:60]} :: {e}", flush=True)
    f.close()
    print(f"chunk done ok={ok}/{len(todo)} total_done={len(done)+ok}", flush=True)

if __name__ == "__main__":
    main()
