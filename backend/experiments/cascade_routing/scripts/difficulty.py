"""
difficulty.py — Feature Extraction Module for Hinglish cascade difficulty score.

Formula:
    d(x) = 0.40 * CM + 0.30 * ED + 0.20 * MM + 0.10 * L

Features (all normalized to [0, 1]):
    CM : Code-Mix Ratio  = hindi_tokens / (hindi_tokens + english_tokens)
    ED : Entity Density  = min(1, n_protected_spans / 3)
    MM : Math Markers    = 1.0 if math/logic pattern present else 0.0
    L  : Length Penalty  = min(1, n_tokens / MAX_TOKENS)

Usage:
    python difficulty.py --input prompts.csv --output prompts_scored.csv
    python difficulty.py --text "Tumhara naam kya hai?"
"""
from __future__ import annotations
import argparse
import csv
import re

W_CM, W_ED, W_MM, W_L = 0.40, 0.30, 0.20, 0.10
MAX_TOKENS = 512

# ~250 common Romanized Hindi / Hinglish tokens (STA drift tolerant: lowercased).
HINGLISH_COMMON = {
    "hai", "hain", "ho", "hoga", "hogi", "honge", "tha", "thi", "the", "hu", "hun", "hoon",
    "kya", "kaisa", "kaise", "kaisa", "kaun", "kab", "kahan", "kyun", "kyu", "kaise",
    "ka", "ki", "ke", "ko", "ne", "se", "me", "mein", "main", "hum", "tum", "tu", "aap",
    "yeh", "ye", "woh", "wo", "us", "un", "is", "iss", "uss", "apna", "apne", "apni",
    "mera", "mere", "meri", "tera", "tere", "teri", "uska", "uske", "uski", "unka", "unke",
    "aur", "ya", "par", "per", "bhi", "nahi", "nhi", "na", "mat", "sirf", "bas", "abhi",
    "phir", "wapas", "saath", "sath", "liye", "diye", "wala", "wale", "wali", "vala",
    "kar", "karo", "karke", "kiya", "kiye", "karega", "karna", "karte", "karti", "kart",
    "bata", "batao", "bataye", "likho", "likh", "nikalo", "nikal", "dekho", "dekh", "socho",
    "samjhao", "samjha", "karke", "hoke", "raha", "rahi", "rahe", "rha", "rhi", "rhe",
    "gaya", "gayi", "gaye", "aaya", "aayi", "aaye", "jao", "ja", "aa", "aao",
    "achha", "acha", "accha", "sahi", "galat", "bada", "bade", "badi", "chota", "chote", "choti",
    "naya", "nayi", "purana", "zyada", "jyada", "kam", "bahut", "bohot", "bahot", "kaafi", "kafi",
    "thoda", "thodi", "sab", "sabse", "koi", "kuch", "zyaada", "kitna", "kitne", "kitni",
    "jisme", "jiska", "jiske", "jiski", "uska", "iska", "iska", "dono", "teen", "do", "ek",
    "bhai", "yaar", "dekho", "batao", "bolo", "sunao", "karo", "waale", "waala", "wala",
    "hoti", "hota", "hote", "chahiye", "sakta", "sakte", "sakti", "pa", "paa", "jata", "jati",
    "deta", "deti", "dete", "leta", "leti", "lete", "wala", "wahi", "yahi", "tabhi", "kabhi",
    "hamesha", "agar", "magar", "lekin", "kyunki", "kyonki", "isliye", "phir", "toh", "to",
    "bina", "sath", "tarah", "jaise", "vaise", "aisa", "aisi", "aise", "waisa", "jaisa",
    "karna", "hona", "dena", "lena", "kehna", "bolna", "likhna", "padhna", "samajhna",
    "munna", "arre", "chal", "chalo", "theek", "thik", "haan", "han", "nah", "arey",
}

WORD_RE = re.compile(r"[A-Za-z\u0900-\u097F]+(?:'[A-Za-z]+)?")

# ED: regex-protected spans
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MONEY_RE = re.compile(r"(?:₹|\$|€|£|Rs\.?|INR|USD)\s?[\d,]+(?:\.\d+)?|\b\d+\s?(?:rupees|dollars|rs)\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b")
NUMERIC_ENTITY_RE = re.compile(r"\b\d{4,}\b")  # long IDs, PINs, etc.

# MM: math / logic markers
MATH_RE = re.compile(
    r"(\d+\s*[+\-*/^=%<>!]+\s*\d+)"      # 4x + 2y, 1/6, x^2
    r"|(\b\d+\s*(?:\+|\-|\*|/|%|=|<|>|<=|>=|==|!=)\s*\w+)"
    r"|(\b\w+\s*(?:\+|\-|\*|/|=|<|>|<=|>=|==)\s*\d+)"
    r"|(sqrt|log|sin|cos|tan|factorial|probability|equation|formula|calculate|LCM|HCF|area|volume|sum|average|percent)",
    re.IGNORECASE,
)
LOGIC_RE = re.compile(r"(&&|\|\||=>|->|<-|∀|∃|∈|∑|∏|√|π|∞|\bx\^2\b|\by\^2\b)")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def compute_cm(text: str) -> float:
    toks = tokenize(text)
    if not toks:
        return 0.0
    h = sum(1 for t in toks if t in HINGLISH_COMMON)
    e = len(toks) - h
    return h / (h + e) if (h + e) else 0.0


def count_protected_spans(text: str) -> int:
    n = 0
    n += len(EMAIL_RE.findall(text))
    n += len(URL_RE.findall(text))
    n += len(MONEY_RE.findall(text))
    n += len(PHONE_RE.findall(text))
    # numeric IDs only count if no other entity found (avoid double counting math)
    if n == 0:
        n += len(NUMERIC_ENTITY_RE.findall(text))
    return n


def compute_ed(text: str) -> float:
    return min(1.0, count_protected_spans(text) / 3.0)


def compute_mm(text: str) -> float:
    return 1.0 if (MATH_RE.search(text) or LOGIC_RE.search(text)) else 0.0


def compute_l(text: str, max_tokens: int = MAX_TOKENS) -> float:
    n = len(tokenize(text))
    return min(1.0, n / max_tokens)


def difficulty(text: str, max_tokens: int = MAX_TOKENS) -> dict:
    cm = compute_cm(text)
    ed = compute_ed(text)
    mm = compute_mm(text)
    l = compute_l(text, max_tokens)
    d = W_CM * cm + W_ED * ed + W_MM * mm + W_L * l
    return {"cm": round(cm, 4), "ed": round(ed, 4), "mm": mm, "l": round(l, 4), "d": round(d, 4)}


def score_csv(in_path: str, out_path: str, text_col: str = "prompt", max_tokens: int = MAX_TOKENS):
    import os
    # auto-detect column: prompt | instruction | text
    with open(in_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        col = text_col if text_col in cols else next(
            (c for c in ["prompt", "instruction", "text"] if c in cols), cols[0]
        )
        rows = list(reader)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["prompt", "cm", "ed", "mm", "l", "d"])
        w.writeheader()
        for r in rows:
            t = (r.get(col) or "").strip()
            s = difficulty(t, max_tokens)
            w.writerow({"prompt": t, "cm": s["cm"], "ed": s["ed"], "mm": s["mm"], "l": s["l"], "d": s["d"]})
    print(f"Scored {len(rows)} prompts -> {os.path.abspath(out_path)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="prompts.csv")
    ap.add_argument("--output", default="prompts_scored.csv")
    ap.add_argument("--text-col", default="prompt")
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--text", default=None, help="Score a single string and exit")
    a = ap.parse_args()
    if a.text is not None:
        print(difficulty(a.text, a.max_tokens))
    else:
        score_csv(a.input, a.output, a.text_col, a.max_tokens)


if __name__ == "__main__":
    main()
