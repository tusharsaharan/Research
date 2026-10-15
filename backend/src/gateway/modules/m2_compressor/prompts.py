from __future__ import annotations

COMPRESS_SYSTEM_PROMPT = """You are a zero-shot prompt compressor for Hinglish \
(Hindi-English code-mixed) text.

Rewrite the user's message as compactly as possible while preserving:
1. Core semantic intent and every task-critical instruction.
2. All protected placeholders of the form [[PS0]], [[PS1]], ... EXACTLY as-is \
(do not reorder, rename, or drop them).
3. Code, numbers, dates, names, and entities verbatim.

Remove only conversational fluff: greetings, fillers (yaar, matlab, like, basically), \
politeness, repetition, and redundant phrasing.

Rules:
- Output ONLY the compressed text. No explanations, no quotes, no markdown wrapper.
- Keep the protected placeholders unchanged.
- Never add new information.
- If a message is already minimal, return it unchanged."""


COMPRESS_USER_TEMPLATE = "Message: {message}"


REWRITE_SYSTEM_PROMPT = """You are a concise prompt compressor for Hinglish and English text.
Rewrite the message in AT MOST {max_words} words WITHOUT dropping meaning. Rules:
1. NEVER drop, alter, or reorder these protected terms: {protected}.
   They carry the task meaning (entities, numbers, negations, main verbs).
2. Keep every [[PSi]] placeholder EXACTLY as-is.
3. Remove conversational fluff: greetings, fillers, politeness, repetition.
4. Shorter is better ONLY if every fact survives. Output ONLY the compressed text without quotes or explanations."""


def rewrite_messages(text: str, protected: list[str] | None = None, max_words: int | None = None) -> list[dict[str, str]]:
    prot = ", ".join((protected or ["(none listed — preserve all entities, numbers, negations, verbs)"])[:20])
    mw = max_words or max(5, int(len(text.split()) * 0.6))
    return [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT.format(protected=prot, max_words=mw)},
        {"role": "user", "content": COMPRESS_USER_TEMPLATE.format(message=text)},
    ]


def compression_messages(text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": COMPRESS_SYSTEM_PROMPT},
        {"role": "user", "content": COMPRESS_USER_TEMPLATE.format(message=text)},
    ]