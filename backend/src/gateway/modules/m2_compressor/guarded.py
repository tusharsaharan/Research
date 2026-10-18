"""Meaning-guarded LLMLingua-2 compression.

The 8,000-prompt benchmark showed plain LLMLingua-2 deletes negations (~22% of
prompts that have one at keep-rate 0.7), question words, multiple-choice option
labels, and splits numbers ("$5.50" -> "$ 5. 50"). This wrapper keeps its
compression but removes those failure modes:

1. negation and question words present in the prompt are forced to stay;
2. multiple-choice prompts: only the question stem is compressed, the options
   block ("A) ... B) ...") is kept verbatim;
3. numbers that LLMLingua-2 split are restored to their original spelling;
4. protected spans (numbers in brackets, quotes, math, code, PII) as before.
"""

from __future__ import annotations

import re

from gateway.modules.m2_compressor.safety_span import mask, reinject

NEGATIONS = {"nahi", "nahin", "nhi", "mat", "na", "not", "never", "no", "nothing", "none", "neither", "nor",
             "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "won't", "can't", "cannot", "without"}
QUESTION_WORDS = {"kya", "kyaa", "kaun", "kon", "kab", "kahan", "kidhar", "kaise", "kyun", "kyu", "kitna", "kitne",
                  "kitni", "konsa", "kaunsa", "what", "who", "whom", "whose", "when", "where", "why", "how", "which"}
_OPTIONS = re.compile(r"\n\s*\n?(?=A\)\s)")
_MULTIPART_NUM = re.compile(r"\d+(?:[.,]\d+)+")


def _guard_words(text: str) -> list[str]:
    out = set()
    for w in re.findall(r"[A-Za-z']+", text):
        if w.lower() in NEGATIONS or w.lower() in QUESTION_WORDS:
            out.add(w)
    # Numbers fused with units ("7kg", "1tbsp", "10am", "5th"): LLMLingua-2's
    # force_reserve_digit only keeps pure-digit tokens, so these were dropped.
    for w in text.split():
        w = w.strip(",.!?;:\"'()[]{}")
        if any(ch.isdigit() for ch in w):
            out.add(w)
    return sorted(out)


def _restore_numbers(original: str, compressed: str) -> str:
    for num in set(_MULTIPART_NUM.findall(original)):
        parts = re.split(r"([.,])", num)
        spaced = r"\s*".join(re.escape(p) for p in parts)
        compressed = re.sub(rf"(?<!\d){spaced}(?!\d)", num, compressed)
    return compressed


def split_options(text: str) -> tuple[str, str]:
    m = _OPTIONS.search(text)
    return (text[: m.start()], text[m.start():]) if m else (text, "")


def compress_guarded(text: str, rate: float, lingua) -> str | None:
    """Return the guarded compression, or None if the model failed (caller falls back)."""
    stem, options = split_options(text)
    masked, spans = mask(stem)
    markers = [f"[[PS{i}]]" for i in range(len(spans))]
    got = lingua.compress_masked([masked], [markers], rate=rate, extra_force=_guard_words(stem))[0]
    if got is None:
        return None
    final, ok = reinject(got, spans)
    if not ok:
        return None
    final = _restore_numbers(stem, final)
    return (final.rstrip() + options) if options else final


ADAPTIVE_RATES = (0.4, 0.5, 0.6, 0.7, 0.8)  # most -> least aggressive


def compress_adaptive(text: str, lingua, encoder, tau: float = 0.85, rates=ADAPTIVE_RATES) -> tuple[str, float | None]:
    """Most aggressive guarded compression whose embedding similarity to the
    original stays >= tau. Returns (text, chosen_rate); rate None = unchanged.

    The guards keep negations / question words / numbers / options, which the
    embedding similarity cannot see; the floor protects the remaining meaning.
    LLMLingua-2's forward pass is cached across rates, so extra rates are cheap.
    """
    cands = []
    for r in rates:
        out = compress_guarded(text, r, lingua)
        if out and out != text:
            cands.append((r, out))
    if not cands:
        return text, None
    vecs = encoder.encode([text] + [c[1] for c in cands], normalize_embeddings=True, show_progress_bar=False)
    for (r, out), v in zip(cands, vecs[1:]):
        if float(vecs[0] @ v) >= tau:
            return out, r
    return text, None
