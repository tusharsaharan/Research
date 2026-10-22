"""Language-aware coarse-to-fine compression (our method).

Motivated by KEY_RESULTS M/M2/N: on long contexts dropping whole irrelevant sentences beats
token deletion at tight budgets, on short passages light token deletion beats sentence
selection, and every word deleted inside a sentence costs Hinglish about twice as much as
English (G). So: (1) coarse — query-aware sentence selection (hybrid embedding + lexical
relevance, belebele_extra.sentsel) keeps a share s of the tokens; (2) fine — guarded
LLMLingua-2 (negations, question words, numbers forced) deletes tokens only inside the kept
sentences, at rate t = target / s_actual. The split s is the knob: "sent-heavy" keeps fewer
sentences and deletes few words inside them; "token-heavy" the reverse.

    from hybrid import hybrid
    hybrid(passage, question, target=0.5, sent_share=0.7, enc=..., count=..., lingua=...)
"""

from __future__ import annotations

from belebele_extra import sentsel

from gateway.modules.m2_compressor.guarded import compress_guarded


def hybrid(passage: str, question: str, target: float, sent_share: float, enc, count, lingua) -> str:
    """sent_share = fraction of the original tokens kept by the sentence stage (>= target)."""
    n = count(passage)
    coarse = sentsel(passage, question, sent_share, enc, count) if sent_share < 0.999 else passage
    kept = count(coarse) / max(1, n)
    t = target / max(kept, 1e-6)
    if t >= 0.97:  # sentence stage already met the budget
        return coarse
    fine = compress_guarded(coarse, max(0.2, t), lingua) or coarse
    got = count(fine) / max(1, n)
    if got > 1.08 * target:  # guards keep forced words, so the token stage undershoots: re-aim once
        t2 = max(0.2, t * target / got)
        fine = compress_guarded(coarse, t2, lingua) or fine
    return fine


def graded(passage: str, question: str, target: float, enc, count, lingua, spread: float = 0.6, lexw: float = 0.5) -> str:
    """Relevance-graded variant: no sentence is dropped outright; each sentence gets its own keep
    rate r_i = clip(c + spread * (rel_i - mean rel), 0.2, 1.0), with c set by bisection so the
    total meets the target (LongLLMLingua-style dynamic ratio, with our guards and the hybrid
    embedding + lexical relevance that also works for romanized Hinglish)."""
    import numpy as np

    from belebele_extra import _SENT, _words

    sents = [s for s in _SENT.split(passage.strip()) if s]
    if len(sents) <= 1:
        return compress_guarded(passage, target, lingua) or passage
    e = enc.encode(sents + [question], normalize_embeddings=True, show_progress_bar=False)
    qw = _words(question)
    rel = (1 - lexw) * (e[:-1] @ e[-1]) + lexw * np.array([len(qw & _words(s)) / max(1, len(qw)) for s in sents])
    rel = (rel - rel.min()) / max(1e-6, rel.max() - rel.min())
    lens = np.array([count(s) for s in sents], float)

    def rates(c):
        return np.clip(c + spread * (rel - rel.mean()), 0.2, 1.0)

    lo, hi = 0.0, 1.5
    for _ in range(30):
        mid = (lo + hi) / 2
        if (rates(mid) * lens).sum() / lens.sum() > target:
            hi = mid
        else:
            lo = mid
    out = []
    for s, r in zip(sents, rates(lo)):
        out.append(s if r >= 0.97 else (compress_guarded(s, float(r), lingua) or s))
    return " ".join(out)


# Budget splits tried at each target (sentence share of tokens). Chosen a priori, not tuned on test:
# "s-heavy" = most of the cut from dropping sentences, "t-heavy" = most from in-sentence deletion.
SPLITS = {0.5: {"s-heavy": 0.6, "t-heavy": 0.8}, 0.33: {"s-heavy": 0.42, "t-heavy": 0.6}}


def bm25_scores(sents: list[str], question: str):
    """Okapi BM25 score of each sentence for the question (lowercase alphanumeric tokens)."""
    import math
    import re
    from collections import Counter

    tok = re.compile(r"[a-z0-9]+")
    docs = [tok.findall(s.lower()) for s in sents]
    q = set(tok.findall(question.lower()))
    n, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = Counter(w for d in docs for w in set(d))
    out = []
    for d in docs:
        tf = Counter(d)
        out.append(sum(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(d) / max(1, avg)))
                       for w in q if w in tf))
    return out


def bhybrid(passage: str, question: str, target: float, sent_share: float, count, lingua) -> str:
    """Hybrid with BM25 relevance in the coarse stage (greedy by BM25 score to sent_share of tokens,
    original order), then guarded in-sentence deletion to the target (one re-aim pass)."""
    from belebele_extra import _SENT

    sents = [s for s in _SENT.split(passage.strip()) if s] or [passage]
    n = count(passage)
    sc = bm25_scores(sents, question)
    keep, used = [], 0
    for i in sorted(range(len(sents)), key=lambda i: -sc[i]):
        c = count(sents[i])
        if used + c > sent_share * n and keep:
            continue
        keep.append(i)
        used += c
    coarse = " ".join(sents[i] for i in sorted(keep))
    t = target / max(used / max(1, n), 1e-6)
    if t >= 0.97:
        return coarse
    fine = compress_guarded(coarse, max(0.2, t), lingua) or coarse
    got = count(fine) / max(1, n)
    if got > 1.08 * target:
        fine = compress_guarded(coarse, max(0.2, t * target / got), lingua) or fine
    return fine


def bgraded(passage: str, question: str, target: float, count, lingua, spread: float = 1.0) -> str:
    """Relevance-graded thinning with BM25 relevance (no sentence dropped)."""
    import numpy as np

    from belebele_extra import _SENT

    sents = [s for s in _SENT.split(passage.strip()) if s]
    if len(sents) <= 1:
        return compress_guarded(passage, target, lingua) or passage
    rel = np.array(bm25_scores(sents, question), float)
    rel = (rel - rel.min()) / max(1e-6, rel.max() - rel.min())
    lens = np.array([count(s) for s in sents], float)
    rates = lambda c: np.clip(c + spread * (rel - rel.mean()), 0.1, 1.0)
    lo, hi = 0.0, 1.5
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if (rates(mid) * lens).sum() / lens.sum() > target else (mid, hi)
    return " ".join(s if r >= 0.97 else (compress_guarded(s, float(r), lingua) or s) for s, r in zip(sents, rates(lo)))
