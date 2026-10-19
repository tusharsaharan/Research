"""Which cheap signals tell us that compression changed what the model answers?

Ground truth comes from the Kaggle answers (Qwen2.5-3B): every gold item (GSM8K, ARC,
MMLU; English + Hinglish) answered in its original and each compressed form. For each
(item, language, method) pair:
  changed = the extracted final answer differs from the answer to the original prompt
  broke   = original answer correct and compressed answer wrong
Signals (higher = riskier): 1 - kept ratio (words), 1 - embedding cosine (multilingual
MiniLM), 1 - content-word recall, lost numbers / negations / question words / options,
and, for the attribution, the share of deleted words per word class (Hindi case markers,
auxiliaries, pronouns, connectives, English function words, content words).

Outputs (data/bench/):
  meaning_pairs.jsonl          one row per pair with all signals (reused by gated_compress.py)
  meaning_signals_report.json  AUROC per signal / language / target; a logistic risk model
                               fit on scorer_train items and scored on cert items; and
                               the Hinglish word-class attribution (break-rate odds).

    python meaning_signals.py
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

import numpy as np
from common import BENCH, read_jsonl, split_for
from grade import correct, extract, extract_letter

from gateway.modules.m2_compressor.guarded import NEGATIONS, QUESTION_WORDS, split_options
from gateway.modules.m2_compressor.lexical_safe import NLTK_STOP

# Romanized Hindi function words (spelling variants included). Used for attribution here
# and as the protected set of the Hinglish grammar guard.
HI_CASE = {"ko", "ka", "ki", "ke", "ne", "se", "mein", "me", "mai", "main", "par", "pe", "tak", "liye", "lie",
           "wala", "wali", "wale", "vala", "vali", "vale", "dwara", "taraf", "saath", "sath", "bina", "baad", "pehle",
           "pahle", "andar", "bahar", "upar", "neeche", "niche", "beech", "bich", "tarah", "jaisa", "jaise", "jaisi"}
HI_AUX = {"hai", "hain", "hu", "hoon", "hun", "ho", "tha", "thi", "the", "thay", "hoga", "hogi", "hoge", "honge",
          "raha", "rahi", "rahe", "rha", "rhi", "rhe", "gaya", "gayi", "gaye", "gya", "gyi", "gye", "chuka", "chuki",
          "chuke", "sakta", "sakti", "sakte", "skta", "skti", "skte", "kar", "karo", "karna", "karne", "karke", "kiya",
          "kiye", "ki", "kare", "karein", "karta", "karti", "karte", "hua", "hui", "hue", "hona", "hone", "jata", "jati",
          "jate", "diya", "diye", "di", "liya", "liye", "lo", "do", "de", "dena", "lena", "chahiye", "chahie"}
HI_PRON = {"main", "mai", "mujhe", "mujhko", "mera", "meri", "mere", "hum", "hamein", "humein", "hame", "hamara",
           "hamari", "hamare", "tum", "tumhe", "tumhein", "tumhara", "tumhari", "tumhare", "aap", "aapko", "aapka",
           "aapki", "aapke", "apna", "apni", "apne", "wo", "woh", "vo", "voh", "usne", "usko", "use", "uska", "uski",
           "uske", "unhone", "unko", "unhe", "unka", "unki", "unke", "ye", "yeh", "isne", "isko", "ise", "iska", "iski",
           "iske", "inka", "inki", "inke", "is", "us", "in", "un", "koi", "kuch", "sab", "sabhi", "jo", "jis", "jisne",
           "jiska", "jiski", "jiske"}
HI_CONN = {"aur", "ya", "lekin", "magar", "par", "toh", "to", "agar", "kyunki", "kyuki", "isliye", "phir", "fir", "jab",
           "tab", "bhi", "hi", "sirf", "keval", "fir", "warna", "varna", "jabki", "taki", "taaki", "ki"}
EN_FUNC = set(NLTK_STOP)
_WORD = re.compile(r"[A-Za-z']+|\d[\d,.]*")


def words(t: str) -> list[str]:
    return [w for w in (x.lower().strip("'") for x in _WORD.findall(t or "")) if w]


def word_class(w: str, lang: str) -> str:
    if w[0].isdigit():
        return "number"
    if w in NEGATIONS:
        return "negation"
    if w in QUESTION_WORDS:
        return "question"
    if lang == "hinglish":
        for name, lex in (("hi_case", HI_CASE), ("hi_aux", HI_AUX), ("hi_pron", HI_PRON), ("hi_conn", HI_CONN)):
            if w in lex:
                return name
    if w in EN_FUNC:
        return "en_func"
    return "content"


CLASSES = ["number", "negation", "question", "hi_case", "hi_aux", "hi_pron", "hi_conn", "en_func", "content"]


def answer_of(task: str, content: str):
    a = extract_letter(content) if task == "mcq" else extract(content)
    if task != "mcq" and a is not None:
        try:
            return round(float(a), 6)
        except ValueError:
            return a
    return a


def load_pairs() -> list[dict]:
    items = {r["item_id"]: r for r in read_jsonl(BENCH / "items.jsonl")}
    prompts = {r["key"]: r for r in read_jsonl(BENCH / "kaggle" / "prompts.jsonl") if not r["item_id"].startswith("cq-")}
    ans = {r["key"]: r for r in read_jsonl(BENCH / "kaggle" / "answers.jsonl") if r["key"] in prompts}
    by = defaultdict(dict)  # (item, lang) -> method -> (text, content, prompt_tokens)
    for k, p in prompts.items():
        if k in ans:
            for m in p["methods"]:
                by[(p["item_id"], p["lang"])][m] = (p["prompt"], ans[k]["content"], ans[k]["prompt_tokens"])
    rows = []
    for (iid, lang), d in by.items():
        if "original" not in d or iid not in items:
            continue
        it = items[iid]
        task, gold = it.get("task", "math"), it["gold"]
        o_text, o_content, o_pt = d["original"]
        o_ans, o_ok = answer_of(task, o_content), correct(task, o_content, gold)
        for m, (text, content, pt) in d.items():
            if m == "original":
                continue
            c_ans = answer_of(task, content)
            rows.append({"item_id": iid, "lang": lang, "task": task, "method": m, "split": split_for(iid),
                         "orig": o_text, "comp": text, "orig_correct": o_ok, "comp_correct": correct(task, content, gold),
                         "changed": int(c_ans != o_ans), "broke": int(o_ok and not correct(task, content, gold)),
                         "tok_ratio": pt / max(1, o_pt)})
    return rows


def signals(r: dict) -> dict:
    ow, cw = words(r["orig"]), words(r["comp"])
    cset = set(cw)
    out = {"kept_words": len(cw) / max(1, len(ow))}
    lost = defaultdict(int)
    total = defaultdict(int)
    for w in ow:
        k = word_class(w, r["lang"])
        total[k] += 1
        if w not in cset:
            lost[k] += 1
    content = [w for w in ow if word_class(w, r["lang"]) == "content"]
    out["content_recall"] = 1 - lost["content"] / max(1, len(content))
    for k in CLASSES:
        out[f"lost_{k}"] = lost[k] / total[k] if total[k] else 0.0
        out[f"has_{k}"] = int(total[k] > 0)
    stem, options = split_options(r["orig"])
    if options:
        norm = lambda s: " ".join(s.split())
        out["options_intact"] = int(norm(options) in norm(r["comp"]))
    else:
        out["options_intact"] = 1
    return out


def auroc(y, s):
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y)
    return round(float(roc_auc_score(y, s)), 4) if 0 < y.sum() < len(y) else None


def main() -> None:
    import torch

    torch.set_num_threads(os.cpu_count() or 4)
    rows = load_pairs()
    print(len(rows), "pairs", flush=True)
    for r in rows:
        r.update(signals(r))
    # embedding cosine (multilingual MiniLM, cached by text)
    from adaptive_eval import CACHE

    from gateway.modules.m4_router.certified import _encoder

    emb = {}
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        emb = dict(zip(z["keys"].tolist(), z["vecs"]))
    todo = sorted({t for r in rows for t in (r["orig"], r["comp"])} - set(emb))
    print("embedding", len(todo), "new texts", flush=True)
    if todo:
        emb.update(zip(todo, _encoder().encode(todo, batch_size=128, normalize_embeddings=True, show_progress_bar=False)))
        np.savez(CACHE, keys=np.array(list(emb), dtype=object), vecs=np.stack(list(emb.values())))
    for r in rows:
        r["cosine"] = float(emb[r["orig"]] @ emb[r["comp"]])

    risk_feats = {"1-kept_words": lambda r: 1 - r["kept_words"], "1-tok_ratio": lambda r: 1 - r["tok_ratio"],
                  "1-cosine": lambda r: 1 - r["cosine"], "1-content_recall": lambda r: 1 - r["content_recall"],
                  "lost_number": lambda r: r["lost_number"], "lost_negation": lambda r: r["lost_negation"],
                  "options_broken": lambda r: 1 - r["options_intact"]}
    report = {"n_pairs": len(rows), "auroc": {}, "base_rates": {}}
    for lang in ("english", "hinglish"):
        sub = [r for r in rows if r["lang"] == lang]
        for tgt in ("changed", "broke"):
            y = [r[tgt] for r in sub]
            report["base_rates"][f"{lang}|{tgt}"] = round(float(np.mean(y)), 4)
            for name, f in risk_feats.items():
                report["auroc"][f"{lang}|{tgt}|{name}"] = auroc(y, [f(r) for r in sub])

    # logistic risk model: fit on scorer_train items, evaluate on cert items
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    feat_names = ["kept_words", "tok_ratio", "cosine", "content_recall", "options_intact"] + \
                 [f"lost_{k}" for k in CLASSES] + [f"has_{k}" for k in CLASSES]

    def X(rs):
        return np.array([[r[f] for f in feat_names] + [r["lang"] == "hinglish", r["task"] == "mcq"] for r in rs], float)

    train = [r for r in rows if r["split"] == "scorer_train"]
    cert = [r for r in rows if r["split"] == "cert"]
    report["risk_model"] = {"features": feat_names + ["is_hinglish", "is_mcq"], "n_train": len(train), "n_cert": len(cert)}
    for tgt in ("changed", "broke"):
        sc = StandardScaler().fit(X(train))
        clf = LogisticRegression(max_iter=3000, C=1.0).fit(sc.transform(X(train)), [r[tgt] for r in train])
        p = clf.predict_proba(sc.transform(X(rows)))[:, 1]
        for r, v in zip(rows, p):
            r[f"risk_{tgt}"] = float(v)
        for lang in ("english", "hinglish"):
            sub = [r for r in cert if r["lang"] == lang]
            report["auroc"][f"{lang}|{tgt}|learned_risk (cert items)"] = auroc([r[tgt] for r in sub], [r[f"risk_{tgt}"] for r in sub])
            report["auroc"][f"{lang}|{tgt}|1-cosine (cert items)"] = auroc([r[tgt] for r in sub], [1 - r["cosine"] for r in sub])
        report["risk_model"][f"coef_{tgt}"] = dict(zip(report["risk_model"]["features"], np.round(clf.coef_[0], 3).tolist()))

    # Hinglish attribution: does deleting a word class predict a break, beyond how much was deleted?
    # Logistic regression of broke on per-class lost shares + kept ratio + method dummies, Hinglish pairs
    # with an original-correct answer; bootstrap over items for 95% CIs of each coefficient.
    attrib = {}
    for lang in ("hinglish", "english"):
        sub = [r for r in rows if r["lang"] == lang and r["orig_correct"] and r["method"] != "heuristic"]
        cls = [k for k in CLASSES if any(r[f"has_{k}"] for r in sub) and sum(r[f"lost_{k}"] > 0 for r in sub) >= 30]
        methods = sorted({r["method"] for r in sub})
        def design(rs):
            return np.array([[r[f"lost_{k}"] for k in cls] + [1 - r["kept_words"]] +
                             [r["method"] == m for m in methods[1:]] for r in rs], float)
        y = np.array([r["broke"] for r in sub])
        Xa = design(sub)
        sd = Xa[:, : len(cls) + 1].std(0) + 1e-9
        Xs = Xa.copy()
        Xs[:, : len(cls) + 1] /= sd  # per-SD effects for the shares
        fit = LogisticRegression(max_iter=4000, C=10.0).fit(Xs, y)
        coefs = fit.coef_[0][: len(cls) + 1]
        ids = sorted({r["item_id"] for r in sub})
        idx = defaultdict(list)
        for i, r in enumerate(sub):
            idx[r["item_id"]].append(i)
        rng = np.random.default_rng(0)
        boots = []
        for _ in range(200):
            pick = np.concatenate([idx[i] for i in rng.choice(ids, len(ids))])
            if y[pick].sum() < 5:
                continue
            boots.append(LogisticRegression(max_iter=4000, C=10.0).fit(Xs[pick], y[pick]).coef_[0][: len(cls) + 1])
        boots = np.array(boots)
        names = [f"lost_{k}" for k in cls] + ["1-kept_words"]
        attrib[lang] = {n: {"log_odds_per_sd": round(float(c), 3),
                            "ci95": [round(float(np.percentile(boots[:, j], 2.5)), 3), round(float(np.percentile(boots[:, j], 97.5)), 3)]}
                        for j, (n, c) in enumerate(zip(names, coefs))}
        attrib[lang]["n_pairs"] = len(sub)
    report["break_attribution"] = attrib

    with (BENCH / "meaning_pairs.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({k: v for k, v in r.items() if k not in ("orig", "comp")}, ensure_ascii=False) + "\n")
    (BENCH / "meaning_signals_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for k, v in report["auroc"].items():
        print(f"{k:55} {v}")
    print("base rates", report["base_rates"])
    for lang, a in attrib.items():
        print("== attribution", lang, a["n_pairs"])
        for n, v in a.items():
            if n != "n_pairs":
                print(f"   {n:16} {v['log_odds_per_sd']:+.3f} {v['ci95']}")


if __name__ == "__main__":
    main()
