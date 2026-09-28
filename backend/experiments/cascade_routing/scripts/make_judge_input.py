"""Build judge_input_200.csv: prompt + NEW m9 d/features + qwen + premium + cheap_ok."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

scored = {r["prompt"]: r for r in csv.DictReader(open(os.path.join(DATA, "prompts_scored.csv"), encoding="utf-8"))}
qwen = {r["prompt"]: r["qwen_response"] for r in csv.DictReader(open(os.path.join(DATA, "qwen_200.csv"), encoding="utf-8"))}
prem = [(r["prompt"], r["response"]) for r in csv.DictReader(open(os.path.join(DATA, "prompts_first_200_with_responses.csv"), encoding="utf-8-sig"))]
routed = {r["prompt"]: r["cheap_ok"] for r in csv.DictReader(open(os.path.join(DATA, "prompts_routed.csv"), encoding="utf-8-sig"))}

out = os.path.join(DATA, "judge_input_200.csv")
n = 0
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["prompt", "d", "n_tokens", "code_mix", "math_count", "logic_count", "budget",
                                      "qwen_response", "premium_response", "cheap_ok"], quoting=csv.QUOTE_ALL)
    w.writeheader()
    for p, pr in prem:
        s = scored[p]
        w.writerow({"prompt": p, "d": s["d"], "n_tokens": s["n_tokens"], "code_mix": s["code_mix"],
                    "math_count": s["math_count"], "logic_count": s["logic_count"], "budget": s["budget"],
                    "qwen_response": qwen[p], "premium_response": pr, "cheap_ok": routed[p]})
        n += 1
print(f"wrote {out} ({n} rows)")
