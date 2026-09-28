import time, laya
t0 = time.time()
agent = laya.load("D:/laya")
print(f"loaded in {time.time()-t0:.1f}s")
Q = {"cheap": {"type": "choice",
     "instructions": ("Can a small cheap language model handle this request correctly "
                      "on its own, or does it need an expensive premium model?"),
     "criteria": {"Yes": "simple routine request a small model handles well",
                  "No": ("needs a premium model: hard reasoning, code, "
                         "expert advice, or high-stakes accuracy")}}}
for p in ["Mary ki bio likho.",
          "1/(x - 1)(x - 2) + 1/(x - 2)(x - 3) + 1/(x - 3)(x - 4) = 1/6 ke saare real solutions nikaalo."]:
    r = agent.predict(p, Q)["answers"]["cheap"]
    print(repr(p[:50]), "->", r["choice"], {k: round(v, 3) for k, v in r.get("probabilities", {}).items()})
