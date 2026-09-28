"""make_finetune_pack.py — Build Laya fine-tune pack from judge_output_200_v2.csv.

Split (stratified by grade, seed=42): 140 train / 30 calib / 30 test.
Each row: {"prompt": ..., "gold": "Yes"|"No"} + the shared cheap QUESTION spec.
The Colab notebook tokenizes with laya.build_sequence (same as serving).

Usage: python scripts/make_finetune_pack.py
Output: data/finetune/{train.jsonl, calib.jsonl, test.jsonl, manifest.json, QUESTION.json}
"""
import csv, json, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "finetune")

QUESTION = {
    "type": "choice",
    "instructions": ("Can a small cheap language model handle this request correctly "
                     "on its own, or does it need an expensive premium model?"),
    "criteria": {
        "Yes": "simple routine request a small model handles well",
        "No": ("needs a premium model: hard reasoning, code, "
               "expert advice, or high-stakes accuracy"),
    },
}

def main():
    rows = list(csv.DictReader(open(os.path.join(DATA, "judge_output_200_v2.csv"), encoding="utf-8-sig")))
    ys = [r["prompt"] for r in rows if r["cheap_did_well"] == "Y"]
    ns = [r["prompt"] for r in rows if r["cheap_did_well"] == "N"]
    print(f"pool: Y={len(ys)} N={len(ns)}")
    rnd = random.Random(42)
    for grp in (ys, ns):
        rnd.shuffle(grp)
    def take(ys_, ns_, n):
        ny = round(n * len(ys_) / (len(ys_) + len(ns_)))
        return ys_[:ny], ns_[:n - ny]
    # 30 test, 30 calib, rest train — stratified
    tY, tN = take(ys, ns, 30); ys, ns = ys[len(tY):], ns[len(tN):]
    cY, cN = take(ys, ns, 30); ys, ns = ys[len(cY):], ns[len(cN):]
    splits = {"test": (tY, tN), "calib": (cY, cN), "train": (ys, ns)}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "QUESTION.json"), "w") as f:
        json.dump(QUESTION, f, indent=2)
    manifest = {"seed": 42, "splits": {}}
    for name, (py, pn) in splits.items():
        items = [{"prompt": p, "gold": "Yes"} for p in py] + [{"prompt": p, "gold": "No"} for p in pn]
        rnd.shuffle(items)
        with open(os.path.join(OUT, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        manifest["splits"][name] = {"n": len(items), "Y": len(py), "N": len(pn)}
        print(name, manifest["splits"][name])
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("pack ->", OUT)

if __name__ == "__main__":
    main()
