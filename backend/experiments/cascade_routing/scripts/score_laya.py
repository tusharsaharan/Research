"""score_laya.py — Difficulty as fine-tuned router P(No): d(x) = P(cheap fails).

Usage: python scripts/score_laya.py --input data/prompts_200.csv --output data/scored_laya_200.csv
Then: full run with --input data/prompts.csv --output data/scored_laya_10378.csv
"""
import argparse, csv, os, time
import laya
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
QUESTIONS = {"cheap": {"type": "choice",
    "instructions": ("Can a small cheap language model handle this request correctly "
                     "on its own, or does it need an expensive premium model?"),
    "criteria": {"Yes": "simple routine request a small model handles well",
                 "No": ("needs a premium model: hard reasoning, code, "
                        "expert advice, or high-stakes accuracy")}}}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(DATA, "prompts_200.csv"))
    ap.add_argument("--output", default=os.path.join(DATA, "scored_laya_200.csv"))
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--chunk", type=int, default=80)
    a = ap.parse_args()
    prompts = [r["prompt"] for r in csv.DictReader(open(a.input, encoding="utf-8-sig"))]
    done = set()
    if os.path.exists(a.output):
        done = {r["prompt"] for r in csv.DictReader(open(a.output, encoding="utf-8")) if r.get("d")}
    todo = [p for p in prompts if p not in done]
    print(f"total={len(prompts)} done={len(done)} todo={len(todo)}", flush=True)
    agent = laya.load("D:/laya")
    print("agent ready", flush=True)
    f = open(a.output, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=["prompt", "d", "prob_yes", "prob_no"], quoting=csv.QUOTE_ALL)
    if not done:
        w.writeheader()
        f.flush()
        os.fsync(f.fileno())
    t0 = time.time()
    for s in range(0, len(todo), a.chunk):
        chunk = todo[s:s + a.chunk]
        res = agent.predict_batch(chunk, QUESTIONS, batch_size=a.batch, sort_by_length=True)
        for p, r in zip(chunk, res):
            pr = r["answers"]["cheap"].get("probabilities", {})
            py, pn = float(pr.get("Yes", 0.0)), float(pr.get("No", 0.0))
            w.writerow({"prompt": p, "d": round(pn, 4), "prob_yes": round(py, 4), "prob_no": pn})
        f.flush()
        print(f"{min(s+a.chunk, len(todo))}/{len(todo)} elapsed={time.time()-t0:.0f}s", flush=True)
    f.close()
    print("scored ->", a.output)

if __name__ == "__main__":
    main()
