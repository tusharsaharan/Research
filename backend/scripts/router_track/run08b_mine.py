"""Mine importance_lexicon.json from Judge-A labels (class ranking + per-word deltas)."""

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from common import load_jsonl, track  # noqa: E402

t = track()
rows = load_jsonl(t / "judgeA_labels.jsonl")
queries = {r["id"]: r for r in load_jsonl(t / "groq_labels.jsonl")}
variants = defaultdict(list)
for r in rows:
    variants[r["variant"]].append(r["delta"])

classes = {}
for v, d in sorted(variants.items()):
    classes[v] = {"n": len(d), "mean_delta": round(statistics.mean(d), 4),
                  "median_delta": round(statistics.median(d), 4),
                  "big_drop_rate": round(sum(1 for x in d if x >= 0.3) / len(d), 4)}

# per-word: queries where V_heu dropped the word -> mean delta
word_delta: dict[str, list] = defaultdict(list)
for r in rows:
    if r["variant"] != "V_heu":
        continue
    q = queries[r["id"]]["text"].split()
    ablated = set(r["ablated"].split())
    for w in q:
        if w not in ablated:
            word_delta[w.lower().strip(",.!?")].append(r["delta"])
words = {w: {"n": len(d), "mean_delta": round(statistics.mean(d), 4)}
         for w, d in word_delta.items() if len(d) >= 5}
top_safe = sorted(words.items(), key=lambda kv: kv[1]["mean_delta"])[:25]
top_risky = sorted(words.items(), key=lambda kv: kv[1]["mean_delta"], reverse=True)[:25]

lex = {"classes": classes,
       "safest_drops": [{w: s} for w, s in top_safe],
       "riskiest_drops": [{w: s} for w, s in top_risky],
       "provisional_epsilon": 0.5,
       "epsilon_note": "PROVISIONAL — final epsilon fit to human_check.csv before freezing"}
(t / "importance_lexicon.json").write_text(json.dumps(lex, indent=2, ensure_ascii=False), encoding="utf-8")
print("classes:", json.dumps(classes, indent=1))
print("safest:", [list(d)[0] for d in top_safe[:10]])
print("riskiest:", [list(d)[0] for d in top_risky[:10]])
