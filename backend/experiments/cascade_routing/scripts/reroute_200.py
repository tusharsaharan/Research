"""reroute_200.py — Re-run prompts_200.csv through the (fine-tuned) D:/laya router."""
import csv, os, time
import laya
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
QUESTIONS = {"cheap": {"type": "choice",
    "instructions": ("Can a small cheap language model handle this request correctly "
                     "on its own, or does it need an expensive premium model?"),
    "criteria": {"Yes": "simple routine request a small model handles well",
                 "No": ("needs a premium model: hard reasoning, code, "
                        "expert advice, or high-stakes accuracy")}}}

prompts = [r["prompt"] for r in csv.DictReader(open(os.path.join(DATA, "prompts_200.csv"), encoding="utf-8-sig"))]
print("prompts:", len(prompts), flush=True)
agent = laya.load("D:/laya")
print("agent ready", flush=True)
t0 = time.time()
out = os.path.join(DATA, "prompts_rerouted_200.csv")
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["prompt", "cheap_ok", "prob_yes", "prob_no"])
    for s in range(0, len(prompts), 160):
        chunk = prompts[s:s + 160]
        res = agent.predict_batch(chunk, QUESTIONS, batch_size=16, sort_by_length=True)
        for p, r in zip(chunk, res):
            a = r["answers"]["cheap"]
            pr = a.get("probabilities", {})
            w.writerow([p, a["choice"], pr.get("Yes", ""), pr.get("No", "")])
        f.flush()
        print(f"{min(s+160, len(prompts))}/{len(prompts)} elapsed={time.time()-t0:.0f}s", flush=True)
print("wrote", out)
