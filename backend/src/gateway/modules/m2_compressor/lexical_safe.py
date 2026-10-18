"""Negation-safe lexical compression (replication + code-mixed extension).

Re-implements the stopword-removal stage of "Lexical Prompt Compression for
Large Language Models" (arXiv 2609.13154, 2026): delete English stopwords
except negations and wh-words. Extension for Hinglish: also delete romanized
filler / discourse words (yaar, bhai, matlab, arre, softener "na", ...) while
keeping Hindi negations (nahi, mat) and question words (kya, kaun, kab, ...).
Protected spans (numbers in brackets, quotes, math, code, PII) are untouched.
"""

from __future__ import annotations

import re

from gateway.modules.m2_compressor.safety_span import mask, reinject

# NLTK English stopword list (standard 179 words), embedded so no corpus download is needed.
NLTK_STOP = set("""i me my myself we our ours ourselves you you're you've you'll you'd your yours yourself yourselves
he him his himself she she's her hers herself it it's its itself they them their theirs themselves what which who
whom this that that'll these those am is are was were be been being have has had having do does did doing a an the
and but if or because as until while of at by for with about against between into through during before after
above below to from up down in out on off over under again further then once here there when where why how all any
both each few more most other some such no nor not only own same so than too very s t can will just don don't should
should've now d ll m o re ve y ain aren aren't couldn couldn't didn didn't doesn doesn't hadn hadn't hasn hasn't
haven haven't isn isn't ma mightn mightn't mustn mustn't needn needn't shan shan't shouldn shouldn't wasn wasn't
weren weren't won won't wouldn wouldn't""".split())
NEGATIONS = {"no", "nor", "not", "never", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
             "won't", "wouldn't", "can't", "cannot", "couldn't", "shouldn't", "hasn't", "haven't", "hadn't",
             "mustn't", "needn't", "shan't", "mightn't", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn",
             "haven", "isn", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won", "wouldn", "don",
             "nahi", "nahin", "nhi", "mat"}
WH = {"what", "which", "who", "whom", "whose", "when", "where", "why", "how",
      "kya", "kyaa", "kaun", "kon", "kab", "kahan", "kidhar", "kaise", "kyun", "kyu", "kitna", "kitne", "kitni",
      "konsa", "kaunsa"}
# Romanized-Hinglish fillers / discourse markers with no task content.
HINGLISH_FILLERS = {"yaar", "yar", "bhai", "bro", "matlab", "arre", "arey", "are", "na", "naa", "basically",
                    "actually", "literally", "accha", "acha", "achha", "haan", "ji", "please", "pls", "plz",
                    "dekho", "suno", "sun", "toh", "to", "bas", "hmm", "ok", "okay"}
DELETE = (NLTK_STOP | HINGLISH_FILLERS) - NEGATIONS - WH
_TOKEN = re.compile(r"\S+")
_STRIP = ",.!?;:\"'()[]{}"


def compress_lexical_safe(text: str) -> str:
    masked, spans = mask(text)
    out_lines = []
    for line in masked.split("\n"):
        kept = []
        for tok in _TOKEN.findall(line):
            core = tok.strip(_STRIP).lower()
            if re.fullmatch(r"\(?[A-H]\)", tok):  # multiple-choice label "A)" — "a" is a stopword
                kept.append(tok)
                continue
            if core and core in DELETE and not tok.startswith("[[PS"):
                # keep trailing sentence punctuation by attaching it to the previous kept token
                tail = tok[len(tok.rstrip(".?!")):]
                if tail and kept:
                    kept[-1] += tail
                continue
            kept.append(tok)
        out_lines.append(" ".join(kept))
    out, ok = reinject("\n".join(out_lines), spans)
    return out if ok and out.strip() else text
