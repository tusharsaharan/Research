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


def word_key(w: str) -> str | None:
    if not _WORD.match(w):
        return None
    tail = w[-1] if w[-1] in _VOWELS else "-"
    return f"{hinglish_phash(w)}|{tail}"


class TokOptNormalizer:
    def __init__(self, tokenizer, hinglish_corpus: list[str], english_corpus: list[str], min_count: int = 5) -> None:
        self.tok = tokenizer
        counts: Counter = Counter()
        for t in hinglish_corpus:
            counts.update(w for w in (x.strip(",.!?;:\"'()[]{}") for x in t.split()) if _WORD.match(w))
        self.english = {w.lower() for t in english_corpus for w in re.findall(r"[A-Za-z]+", t)}
        groups: dict[str, list[str]] = defaultdict(list)
        for w, c in counts.items():
            k = word_key(w)
            if k and c >= min_count:
                groups[k].append(w)
        self.best: dict[str, str] = {}
        for k, ws in groups.items():
            if len(ws) < 2:
                continue
            # fewest tokens with a leading space (in-sentence position), then most frequent
            best = min(ws, key=lambda w: (self.cost(w), -counts[w]))
            for w in ws:
                if w != best and self.cost(best) < self.cost(w):
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
