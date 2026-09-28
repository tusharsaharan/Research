import csv, sqlite3, http.client, json
from difficulty import difficulty

N = 50
rows = list(csv.DictReader(open("prompts_scored.csv", encoding="utf-8")))
prompts = [r["prompt"] for r in rows[:N]]

con = sqlite3.connect("cascade.db", timeout=60)
con.execute("PRAGMA journal_mode=WAL;")
con.execute("""CREATE TABLE IF NOT EXISTS responses(
id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT UNIQUE,
cm REAL, ed REAL, mm REAL, llen REAL, d REAL,
qwen_response TEXT, gemini_response TEXT, acceptable INTEGER NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
con.commit()

done = 0
for i, p in enumerate(prompts):
    exists = con.execute("SELECT qwen_response FROM responses WHERE prompt=?", (p,)).fetchone()
    if exists and exists[0]:
        done += 1
        continue
    feats = difficulty(p)
    resp = ""
    for attempt in range(3):
        try:
            c = http.client.HTTPConnection("localhost", 11434, timeout=180)
            c.request("POST", "/api/generate",
                      body=json.dumps({"model": "qwen2.5:latest", "prompt": p,
                                       "stream": False, "options": {"num_predict": 256}}),
                      headers={"Content-Type": "application/json"})
            r = c.getresponse()
            data = json.loads(r.read().decode())
            resp = (data.get("response") or "").strip()
            break
        except Exception as e:
            print(f"  retry {attempt+1} {p[:50]} :: {e}")
            resp = "" if attempt == 2 else None
            if resp is None:
                continue
    if not resp:
        print(f"  SKIP {p[:70]}")
        continue
    con.execute("INSERT OR REPLACE INTO responses (prompt,cm,ed,mm,llen,d,qwen_response) VALUES (?,?,?,?,?,?,?)",
                (p, feats["cm"], feats["ed"], feats["mm"], feats["l"], feats["d"], resp))
    con.commit()
    done += 1
    print(f"[{done}/{len(prompts)}] d={feats['d']} len={len(resp)} :: {p[:70]}")
con.close()
print("OLLAMA-ONLY PASS DONE")
