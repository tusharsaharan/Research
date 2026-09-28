import csv
rows = list(csv.DictReader(open("prompts_scored.csv", encoding="utf-8")))
rows.sort(key=lambda r: len(r["prompt"]))
with open("demo10.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["prompt"])
    w.writeheader()
    for r in rows[:10]:
        w.writerow({"prompt": r["prompt"]})
        print(len(r["prompt"]), r["prompt"][:80])
