import csv
prompts = [r["prompt"] for r in csv.DictReader(open("prompts.csv", encoding="utf-8-sig"))]
first200 = [p for p in dict.fromkeys(p for p in prompts if p.strip())][:200]
got = {r["prompt"]: r["qwen_response"] for r in csv.DictReader(open("qwen_responses.csv", encoding="utf-8"))}
missing = [p for p in first200 if p not in got]
empty = [p for p in first200 if p in got and len(got[p].strip()) < 5]
print("first200:", len(first200), "missing:", len(missing), "too_short:", len(empty))
for p in missing[:5]:
    print("MISS:", p[:80])
for p in empty:
    print("SHORT:", repr(p[:70]), "->", repr(got[p][:60]))
import statistics
lens = [len(got[p]) for p in first200 if p in got]
print("resp_len median:", statistics.median(lens), "min:", min(lens), "max:", max(lens))
