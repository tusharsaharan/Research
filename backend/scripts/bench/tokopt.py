"""Tokenizer-aware spelling normalisation for romanized Hindi (new compressor).

Romanized Hindi has no standard spelling: nahi / nahin / nhi, mujhe / muje,
bahut / bohot / bhot. Different tokenizers split these variants into different
numbers of tokens, and which variant is cheapest depends on the tokenizer
(e.g. XLM-R: "mujhe" = 1 token, "muje" = 2; Qwen2.5: 3 vs 2). This compressor
rewrites each romanized-Hindi word to the attested spelling of the same word
that the *target* tokenizer encodes in the fewest tokens. Nothing is deleted.

"Same word" = same phonetic key (consonant skeleton from phonetic.py) AND same
final vowel, so inflections such as karo / kare / kara are never merged.
Candidates must be attested at least ``min_count`` times in a Hinglish corpus.
Words that occur in English text, numbers, names (capitalised) and protected
negation / question words are never changed.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from gateway.modules.m2_compressor.phonetic import hinglish_phash, is_protected, normalize_chars

_WORD = re.compile(r"^[a-z]+$")
_VOWELS = "aeiou"


_CONS = set("bcdfghjklmnpqrstvwxyz")


def variant_form(w: str) -> str:
    """Canonical form under the two romanization variations that keep the word the same:
    doubled letters (kyaa/kya, accha/acha) and the inherent schwa between two consonants
    (bahut/bhut, kar/kr, pata/pta). Vowel identity is kept, so kiya/kya, uska/iska and
    hota/hata stay distinct (the consonant-skeleton key alone merged them)."""
    s = re.sub(r"(.)\1+", r"\1", w.lower())
    out = [s[0]] if s else []
    for i in range(1, len(s)):
        if s[i] == "a" and i + 1 < len(s) and s[i - 1] in _CONS and s[i + 1] in _CONS:
            continue
        out.append(s[i])
    return "".join(out)


def context_vectors(corpus: list[str], targets: set[str], window: int = 2) -> dict[str, Counter]:
    """Left/right neighbour counts for the target words (distributional check for merges)."""
    vec: dict[str, Counter] = defaultdict(Counter)
    for t in corpus:
        ws = [x.strip(",.!?;:\"'()[]{}").lower() for x in t.split()]
        for i, w in enumerate(ws):
            if w in targets:
                for j in range(max(0, i - window), min(len(ws), i + window + 1)):
                    if j != i and ws[j]:
                        vec[w][("L" if j < i else "R") + ws[j]] += 1
    return vec


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return dot / (na * nb)


def word_key(w: str) -> str | None:
    if not _WORD.match(w):
        return None
    tail = w[-1] if w[-1] in _VOWELS else "-"
    return f"{hinglish_phash(w)}|{tail}"


class TokOptNormalizer:
    def __init__(self, tokenizer, hinglish_corpus: list[str], english_corpus: list[str], min_count: int = 5,
                 strict: bool = False, context_corpus: list[str] | None = None, min_context_cos: float = 0.5) -> None:
        """strict=True (tokopt-safe): words merge only if they share the skeleton key AND the
        variant_form, and (when context_corpus is given) their neighbour distributions agree
        (cosine >= min_context_cos). strict=False reproduces the original, unsafe behaviour."""
        self.tok = tokenizer
        counts: Counter = Counter()
        for t in hinglish_corpus:
            counts.update(w for w in (x.strip(",.!?;:\"'()[]{}") for x in t.split()) if _WORD.match(w))
        self.english = {w.lower() for t in english_corpus for w in re.findall(r"[A-Za-z]+", t)}
        groups: dict[str, list[str]] = defaultdict(list)
        for w, c in counts.items():
            k = word_key(w)
            if k and c >= min_count:
                groups[f"{k}|{variant_form(w)}" if strict else k].append(w)
        self.best: dict[str, str] = {}
        ctx = None
        if strict and context_corpus:
            ctx = context_vectors(context_corpus, {w for ws in groups.values() if len(ws) > 1 for w in ws})
        self.rejected: list[tuple[str, str, float]] = []
        for k, ws in groups.items():
            if len(ws) < 2:
                continue
            # fewest tokens with a leading space (in-sentence position), then most frequent
            best = min(ws, key=lambda w: (self.cost(w), -counts[w]))
            for w in ws:
                if w != best and self.cost(best) < self.cost(w):
                    if ctx is not None:
                        c = cosine(ctx.get(w, Counter()), ctx.get(best, Counter()))
                        if c < min_context_cos:
                            self.rejected.append((w, best, round(c, 3)))
                            continue
                    self.best[w] = best
        self.n_groups = sum(len(ws) >= 2 for ws in groups.values())

    def cost(self, w: str) -> int:
        return len(self.tok.encode(" " + w, add_special_tokens=False).ids)

    def _replace(self, token: str) -> str:
        core = token.strip(",.!?;:\"'()[]{}")
        if not core or core != core.lower():  # names / acronyms / sentence-initial capitals untouched
            return token
        if core in self.english or is_protected(normalize_chars(core)):
            return token
        new = self.best.get(core)
        return token.replace(core, new, 1) if new else token

    def __call__(self, text: str) -> str:
        return "\n".join(" ".join(self._replace(t) for t in line.split(" ")) for line in text.split("\n"))
