from __future__ import annotations

import re

# Devanagari block — genuine Hindi script
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")

# Romanized Hinglish lexicon — curated from frequent Hindi tokens appearing
# in romanized student/support chats. This is intentionally small and
# precision-oriented; the helper is shared by difficulty scoring and
# reasoning-budget estimation so adding words here improves both pillars.
_HINGLISH_TOKENS: frozenset[str] = frozenset(
    {
        # discourse / fillers
        "yaar",
        "matlab",
        "arre",
        "bhai",
        "sun",
        "dekho",
        "basically",
        "actually",
        "like",
        "na",
        "toh",
        "haan",
        "nahi",
        "nahin",
        "hai",
        "hain",
        "tha",
        "thi",
        "the",
        "ho",
        "raha",
        "rahi",
        "rahe",
        "rha",
        "rhi",
        "chal",
        "chala",
        "chali",
        "wala",
        "wali",
        "wale",
        # pronouns / address
        "mera",
        "meri",
        "mere",
        "tera",
        "teri",
        "tere",
        "mujhe",
        "tujhe",
        "hum",
        "aap",
        "tum",
        "yeh",
        "ye",
        "woh",
        "vo",
        "kya",
        "kahan",
        "kaise",
        "kab",
        "kyun",
        "kaun",
        # common verbs / asks
        "kar",
        "karo",
        "karna",
        "karun",
        "karoon",
        "batao",
        "bata",
        "bhejo",
        "bhej",
        "dedo",
        "chahiye",
        "chahie",
        "samajh",
        "samjha",
        "aaya",
        "aayi",
        "gaya",
        "gayi",
        "hoga",
        "hogi",
        "karni",
        "karne",
        "likhna",
        "padhna",
        # support / campus domain
        "hostel",
        "wifi",
        "assignment",
        "deadline",
        "exam",
        "sir",
        "madam",
        # numerals/helpers are not lexicon but help detection
    }
)

_WORD = re.compile(r"[A-Za-z]+")

# Postpositions / particles very frequent in Hinglish
_PARTICLES: frozenset[str] = frozenset({"ka", "ki", "ke", "ko", "mein", "me", "par", "se", "tak", "liye", "bhi", "hi"})


def _romanized_hinglish_count(tokens: list[str]) -> int:
    c = 0
    for t in tokens:
        low = t.lower().strip(",.!?;:\"'()[]{}")
        if low in _HINGLISH_TOKENS or low in _PARTICLES:
            c += 1
    return c


def code_mix_ratio(text: str) -> float:
    """Estimate Hindi/English mix proportion for romanized + Devanagari text.

    Returns 0..1. For pure English → 0.0. For romanized Hinglish like
    "yaar mera phone ..." → >0. Devanagari tokens also count as Hindi.
    """
    tokens = text.split()
    n = len(tokens)
    if n == 0:
        return 0.0
    dev = sum(1 for t in tokens if _DEVANAGARI.search(t))
    roman = _romanized_hinglish_count(tokens)
    # Don't double-count tokens that are both dev and roman (rare)
    hindi = dev + roman
    # If a token matched roman lexicon, count it once
    hindi = min(hindi, n)
    return round(hindi / n, 6)


LANGUAGE_GROUPS = ("english", "hinglish", "mixed_script")
# Short particles that are also common English words; they never decide a group alone.
_AMBIGUOUS = frozenset({"hi", "me", "par", "se", "ko", "na", "the"})


def language_group(text: str) -> str:
    """Language group used for group-conditional (Mondrian) routing guarantees.

    A fixed, documented rule — the guarantee holds for groups *as defined
    here*, so its accuracy must be measured on hand-labelled queries:
      mixed_script — any Devanagari token;
      hinglish     — at least two romanized-Hindi tokens that are not
                     ambiguous English words;
      english      — everything else.
    """
    tokens = text.split()
    if any(_DEVANAGARI.search(t) for t in tokens):
        return "mixed_script"
    hits = 0
    for t in tokens:
        low = t.lower().strip(",.!?;:\"'()[]{}")
        if low not in _AMBIGUOUS and (low in _HINGLISH_TOKENS or low in _PARTICLES):
            hits += 1
    return "hinglish" if hits >= 2 else "english"


def code_mix_detail(text: str) -> dict[str, int | float]:
    """Explain the ratio for debugging / eval tables."""
    tokens = text.split()
    n = len(tokens)
    dev = sum(1 for t in tokens if _DEVANAGARI.search(t))
    roman = _romanized_hinglish_count(tokens)
    hindi = min(dev + roman, n)
    return {
        "n": n,
        "devanagari": dev,
        "roman_hindi": roman,
        "hindi_total": hindi,
        "ratio": round(hindi / n, 6) if n else 0.0,
    }
