"""redo_uncapped.py — Re-run ceiling-suspect prompts with num_predict=-1 (until EOS).

Target: rows in judge_output_200.csv with cheap_did_well=N and len(qwen)>1200.
Guardrail: stream the response; abort past ~12000 chars (~3000 tokens), flag RUNAWAY.
Resumable: skips prompts already in qwen_redo_uncapped.csv.
Usage: python scripts/redo_uncapped.py
"""
import csv, http.client, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SRC = os.path.join(DATA, "judge_output_200.csv")
OUT = os.path.join(DATA, "qwen_redo_uncapped.csv")
CHAR_LIM = 12000  # ~3000 tokens; runaway guardrail

def targets():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    return [r["prompt"] for r in rows
            if r["cheap_did_well"] == "N" and len(r["qwen_response"]) > 1200]

def ask(prompt):
    body = json.dumps({"model": os.environ.get("OLLAMA_MODEL", "qwen2.5:latest"),
                       "prompt": prompt, "stream": True, "keep_alive": "30m",
                       "options": {"num_predict": -1}})
    c = http.client.HTTPConnection("localhost", 11434, timeout=1800)
    c.request("POST", "/api/generate", body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}")
    text, runaway = [], False
    buf = b""
    while True:
        chunk = r.read(65536)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            text.append(o.get("response", ""))
            if sum(map(len, text)) > CHAR_LIM:
                runaway = True
                c.close()
                return "".join(text), runaway
            if o.get("done"):
                return "".join(text), False
    return "".join(text), runaway

def main():
    todo_all = targets()
    done = set()
    new = not os.path.exists(OUT)
    if not new:
        done = {r["prompt"] for r in csv.DictReader(open(OUT, encoding="utf-8"))}
    todo = [p for p in todo_all if p not in done]
    print(f"targets={len(todo_all)} done={len(done)} todo={len(todo)}", flush=True)
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=["prompt", "qwen_uncapped", "runaway", "chars"], quoting=csv.QUOTE_ALL)
    if new:
        w.writeheader()
    ok = 0
    for i, p in enumerate(todo):
        try:
            resp, rw = ask(p)
            w.writerow({"prompt": p, "qwen_uncapped": resp, "runaway": int(rw), "chars": len(resp)})
            f.flush()
            ok += 1
            print(f"[{i+1}/{len(todo)}] ok={ok} runaway={int(rw)} chars={len(resp)} :: {p[:60]}", flush=True)
        except Exception as e:
            print(f"[{i+1}/{len(todo)}] FAIL :: {p[:60]} :: {e}", flush=True)
    f.close()
    print(f"redo done ok={ok}/{len(todo)}", flush=True)

if __name__ == "__main__":
    main()
