import csv
prompts = [r["prompt"] for r in csv.DictReader(open("prompts.csv", encoding="utf-8-sig"))]
first200 = [p for p in dict.fromkeys(p for p in prompts if p.strip())][:200]
with open("prompts_200.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["prompt"])
    for p in first200:
        w.writerow([p])
got = {r["prompt"]: r for r in csv.DictReader(open("qwen_responses.csv", encoding="utf-8"))}
with open("qwen_200.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["prompt", "cm", "ed", "mm", "l", "d", "qwen_response"], quoting=csv.QUOTE_ALL)
    w.writeheader()
    for p in first200:
        w.writerow(got[p])
print("wrote prompts_200.csv + qwen_200.csv (200 rows each)")
