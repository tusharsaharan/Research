"""Paired GSM8K cert items (pair 2): u-rate per language + exact McNemar test.
Writes data/bench/paired_urate_gsm8k.json. Usage: python paired_urate.py"""
import json

from scipy.stats import binomtest

from common import BENCH, read_jsonl

by_item = {}
for r in read_jsonl(BENCH / "grades_pair2.jsonl"):
    if r["source"] == "gsm8k" and r["split"] == "cert" and r["lang"] in ("english", "hinglish"):
        by_item.setdefault(r["item_id"], {})[r["lang"]] = r["u"]
pairs = [v for v in by_item.values() if len(v) == 2]
n = len(pairs)
en, hi = sum(p["english"] for p in pairs), sum(p["hinglish"] for p in pairs)
hi_only = sum(1 for p in pairs if p["hinglish"] and not p["english"])
en_only = sum(1 for p in pairs if p["english"] and not p["hinglish"])
out = {"n_items": n, "u_english": en, "u_hinglish": hi,
       "u_rate_english": round(en / n, 4), "u_rate_hinglish": round(hi / n, 4),
       "discordant_hinglish_only": hi_only, "discordant_english_only": en_only,
       "mcnemar_exact_p": binomtest(en_only, hi_only + en_only, 0.5).pvalue}
(BENCH / "paired_urate_gsm8k.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(out)
