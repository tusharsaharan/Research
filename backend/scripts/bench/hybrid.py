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


# Budget splits tried at each target (sentence share of tokens). Chosen a priori, not tuned on test:
# "s-heavy" = most of the cut from dropping sentences, "t-heavy" = most from in-sentence deletion.
SPLITS = {0.5: {"s-heavy": 0.6, "t-heavy": 0.8}, 0.33: {"s-heavy": 0.42, "t-heavy": 0.6}}
