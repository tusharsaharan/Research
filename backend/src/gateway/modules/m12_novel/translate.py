"""Mixture-aware translation with an equivalence gate (Phase 1, novel).

Fixes the "semantic meaning getting lost" problem: the old 3-language
token-optimizer compared token counts of *non-equivalent* texts (word-by-word
dictionary substitution produced word salad). Now every translation must pass
a semantic-equivalence gate before it enters any tax/delta analysis or is
shown as a "translation":

Gate engines (first available wins):
1. embedding  — sentence-transformers multilingual-MiniLM cosine (optional dep)
2. llm        — LLM judge via the local Ollama client (score 0..1 parsed)
3. lexical    — content-word overlap + char-similarity fallback

Threshold profiles are per-engine because the engines have different scales:
an embedding cosine of 0.75 is a strong match, while a *cross-lingual* lexical
overlap of 0.35 (content words preserved, function words translated) is
already a good gloss. Using one threshold for both would reject good
dictionary glosses or accept garbage model output; the profiles encode that.

Gate bands: >= pass → 'pass'; [amber, pass) → 'amber' (usable, flagged);
< amber → 'reject' (fall back to dictionary gloss / passthrough).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from gateway.llm import BaseLLMClient

# Embedding / LLM-judge thresholds (calibrated scales, 0..1 semantics)
PASS_THRESHOLD = 0.75
AMBER_THRESHOLD = 0.50

# Lexical-engine thresholds: cross-lingual token overlap runs much lower
# (function words never match across scripts), so the bands shift down.
LEXICAL_PASS_THRESHOLD = 0.30
LEXICAL_AMBER_THRESHOLD = 0.18

_WORD = re.compile(r"[a-z\u0900-\u097f]+")
_DEVANAGARI = re.compile(r"[\u0900-\u097f]")


def _looks_like_devanagari_hindi(text: str) -> bool:
    """Honesty guard for `hi` output: reject mojibake as `pass`.

    A weak generator (e.g. tiny Ollama model) can emit replacement chars
    or Latin noise while the self-judge LLM scores it 0.8-1.0. Require real
    Devanagari content: >=3 Devanagari chars, no U+FFFD, and Devanagari
    must be at least 10% of alphanumeric content.
    """
    if not text or "\ufffd" in text:
        return False
    deva = len(_DEVANAGARI.findall(text))
    if deva < 3:
        return False
    alnum = len(re.findall(r"[A-Za-z0-9\u0900-\u097f]", text))
    if alnum == 0:
        return False
    return (deva / alnum) >= 0.10

# English function words excluded from lexical content-overlap (they are the
# ones a correct translation *should* change).
_STOP = frozenset(
    {
        "the", "a", "an", "is", "are", "was", "were", "am", "be", "been",
        "to", "of", "in", "on", "at", "for", "with", "and", "or", "but",
        "do", "does", "did", "done", "have", "has", "had", "will", "would",
        "can", "could", "should", "shall", "may", "might", "must", "this",
        "that", "these", "those", "it", "its", "as", "by", "from", "not",
    }
)


@dataclass
class TranslationResult:
    text: str
    similarity: float
    gate: str  # pass | amber | reject
    source: str  # model | dictionary | passthrough
    engine: str  # embedding | llm | lexical


# --------------------------------------------------------------------------
# Similarity engines
# --------------------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokens(text) if t not in _STOP]


def _lexical_similarity(a: str, b: str) -> float:
    """Content-word overlap (soft recall) + char-similarity blend.

    Cross-lingual by design: named entities, technical terms and borrowings
    survive a correct Hinglish→English/Hindi translation and are exactly what
    this measures. Pure function words are ignored so translating them is free.
    """
    ca, cb = _content_tokens(a), _content_tokens(b)
    if ca and cb:
        sa, sb = set(ca), set(cb)
        overlap = len(sa & sb)
        # recall against the source content words: did the translation keep
        # every name/number/technical term it was supposed to?
        recall = overlap / len(sa)
        # precision-side penalty for unrelated extra content
        precision = overlap / len(sb)
        overlap_score = 2 * recall * precision / max(1e-9, recall + precision)
    else:
        overlap_score = 0.0
    char_sim = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    # Devanagari target shares no Latin tokens; rely on length-ratio sanity
    # plus char similarity across shared numerals/URLs.
    if _DEVANAGARI.search(b) and overlap_score == 0.0:
        return 0.5 * char_sim
    return 0.7 * overlap_score + 0.3 * char_sim


_embedding_model = None


def _embedding_similarity(a: str, b: str) -> float | None:
    """Multilingual-MiniLM cosine if sentence-transformers is installed."""
    global _embedding_model
    if _embedding_model is False:
        return None
    try:
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        import numpy as np

        vecs = _embedding_model.encode([a, b], normalize_embeddings=True)
        va, vb = np.asarray(vecs[0]), np.asarray(vecs[1])
        denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
        return float(np.dot(va, vb) / denom)
    except Exception:
        _embedding_model = False
        return None


async def _llm_similarity(client: BaseLLMClient, a: str, b: str) -> float | None:
    """LLM-judge equivalence score in [0,1] via the local (Ollama) client."""
    prompt = (
        "You are a strict semantic-equivalence judge. Given two sentences, "
        "output ONLY a single number between 0.0 and 1.0 for how similar their "
        "meanings are (1.0 = identical meaning, 0.0 = unrelated). Do not explain.\n\n"
        f"Sentence A: {a}\nSentence B: {b}\nScore:"
    )
    try:
        result = await client.chat([{"role": "user", "content": prompt}], temperature=0.0)
        m = re.search(r"(0?\.\d+|1(?:\.0+)?|0(?:\.0+)?)", result.content.strip())
        if not m:
            return None
        return max(0.0, min(1.0, float(m.group(1))))
    except Exception:
        return None


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------


def _thresholds_for(engine: str) -> tuple[float, float]:
    if engine == "lexical":
        return LEXICAL_AMBER_THRESHOLD, LEXICAL_PASS_THRESHOLD
    return AMBER_THRESHOLD, PASS_THRESHOLD


def _gate(similarity: float, amber: float, pas: float) -> str:
    if similarity >= pas:
        return "pass"
    if similarity >= amber:
        return "amber"
    return "reject"


def gate_score(
    similarity: float,
    engine: str = "lexical",
) -> str:
    """Public gate for synchronous scores (pass | amber | reject)."""
    amber, pas = _thresholds_for(engine)
    return _gate(similarity, amber, pas)


async def translate(
    text: str,
    target: str,
    client: BaseLLMClient | None = None,
    dictionary_fallback=None,
) -> TranslationResult:
    """Translate Hinglish -> target ('en' English | 'hi' Devanagari Hindi).

    Uses the local model client; verifies equivalence with the best available
    gate engine. On rejection falls back to the deterministic dictionary gloss
    (English) or passthrough (Hindi), with gate='reject'.
    """
    import inspect

    trimmed = (text or "").strip()
    if not trimmed:
        return TranslationResult("", 1.0, "pass", "passthrough", "lexical")

    source_label = "dictionary" if dictionary_fallback else "passthrough"

    async def _fb(val: str) -> str:
        if dictionary_fallback is None:
            return val
        out = dictionary_fallback(val)
        if inspect.isawaitable(out):
            out = await out
        return out

    if client is None:
        # No model: dictionary/passthrough, judged lexically
        out = await _fb(trimmed)
        sim = _lexical_similarity(trimmed, out)
        amber, pas = _thresholds_for("lexical")
        return TranslationResult(
            out, round(sim, 4), _gate(sim, amber, pas), source_label, "lexical"
        )

    lang_name = "natural Devanagari Hindi" if target == "hi" else "English"
    prompt = (
        f"Translate this Hinglish (Hindi-English code-mixed, roman script) sentence "
        f"to fluent {lang_name}. Preserve all entities, numbers, code, emails and "
        " URLs exactly. Output ONLY the translation, nothing else.\n"
        f"Text: {trimmed}"
    )
    try:
        result = await client.chat([{"role": "user", "content": prompt}], temperature=0.0)
        candidate = result.content.strip()
    except Exception:
        candidate = ""

    if candidate:
        sim = _embedding_similarity(trimmed, candidate)
        engine = "embedding"
        if sim is None:
            sim = await _llm_similarity(client, trimmed, candidate)
            engine = "llm"
        if sim is None:
            sim = _lexical_similarity(trimmed, candidate)
            engine = "lexical"
        amber, pas = _thresholds_for(engine)
        g = _gate(sim, amber, pas)
        if g in ("pass", "amber"):
            if target == "hi" and not _looks_like_devanagari_hindi(candidate):
                # Don't let a corrupt `hi` string through as pass/amber:
                # fall back to passthrough, honestly labeled reject.
                out = await _fb(trimmed)
                return TranslationResult(out, round(float(sim), 4), "reject", source_label, engine)
            return TranslationResult(
                candidate, round(float(sim), 4), g, "model", engine
            )
        # rejected translation → fallback, report the rejected similarity
        out = await _fb(trimmed)
        return TranslationResult(out, round(float(sim), 4), "reject", source_label, engine)

    # model produced nothing → dictionary fallback
    out = await _fb(trimmed)
    sim = _lexical_similarity(trimmed, out)
    amber, pas = _thresholds_for("lexical")
    return TranslationResult(
        out, round(sim, 4), _gate(sim, amber, pas), source_label, "lexical"
    )


def equivalence_ok(tr: TranslationResult, include_amber: bool = True) -> bool:
    """Whether a gated translation may enter tax/delta analyses."""
    return tr.gate == "pass" or (include_amber and tr.gate == "amber")
