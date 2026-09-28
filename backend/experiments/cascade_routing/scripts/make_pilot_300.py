"""make_pilot_300.py — Stratified 300-prompt pilot sample (30 per P(No) decile)."""
import csv, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

scored = {}
for r in csv.DictReader(open(os.path.join(DATA, "scored_laya_10378.csv"), encoding="utf-8")):
    scored[r["prompt"]] = float(r["d"])
done200 = {r["prompt"] for r in csv.DictReader(open(os.path.join(DATA, "prompts_200.csv"), encoding="utf-8-sig"))}
pool = [(p, d) for p, d in scored.items() if p not in done200]
print(f"pool={len(pool)} (excl done 200)")
rnd = random.Random(7)
buckets = [[] for _ in range(10)]
for p, d in pool:
    buckets[min(9, int(d * 10))].append((p, d))
sample = []
for i, b in enumerate(buckets):
    rnd.shuffle(b)
    take = b[:30]
    sample.extend(take)
    ds = [d for _, d in take]
    print(f"decile {i}: pool={len(b)} took={len(take)} d_range=({min(ds):.3f},{max(ds):.3f})" if take else f"decile {i}: EMPTY")
rnd.shuffle(sample)
with open(os.path.join(DATA, "pilot_300.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["prompt"])
    for p, _ in sample:
        w.writerow([p])
print("pilot_300.csv rows:", len(sample))
