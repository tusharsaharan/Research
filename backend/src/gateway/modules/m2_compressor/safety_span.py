from __future__ import annotations

import re

from gateway.schemas import SafetySpan

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"https?://\S+|www\.\S+")
_FENCED = re.compile(r"```(?:[A-Za-z+]*\n)?.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`\n]+`")
_PHONE = re.compile(r"(?<!\w)(?:\+\d{1,3}[ \t-]?)?(?:\(?\d{2,4}\)?[ \t-]?)?\d{3,5}[ \t-]?\d{3,5}(?!\w)")
_AMOUNT = re.compile(r"(?:Rs\.?|INR|₹)\s?\d[\d,]*(?:\.\d+)?")

_KINDS = (
    ("code_fenced", _FENCED),
    ("code_inline", _INLINE),
    ("email", _EMAIL),
    ("url", _URL),
    ("phone", _PHONE),
    ("amount", _AMOUNT),
)

_PS = re.compile(r"\[\[PS(\d+)\]\]", re.IGNORECASE)


def detect_spans(text: str) -> list[SafetySpan]:
    """Find protected spans (PII, code, urls, amounts). Later spans see already-matched text."""
    spans: list[SafetySpan] = []
    covered: list[tuple[int, int]] = []
    for kind, rx in _KINDS:
        for m in rx.finditer(text):
            s, e = m.start(), m.end()
            if any(not (e <= cs or s >= ce) for cs, ce in covered):
                continue
            spans.append(SafetySpan(kind=kind, text=m.group(0), start=s, end=e))
            covered.append((s, e))
    return sorted(spans, key=lambda sp: sp.start)


def mask(text: str) -> tuple[str, list[SafetySpan]]:
    """Replace protected spans with [[PSi]] markers, returning masked text and spans."""
    spans = detect_spans(text)
    out = []
    cursor = 0
    for i, sp in enumerate(spans):
        out.append(text[cursor : sp.start])
        out.append(f"[[PS{i}]]")
        cursor = sp.end
    out.append(text[cursor:])
    return "".join(out), spans


def reinject(masked: str, spans: list[SafetySpan]) -> tuple[str, bool]:
    """Re-inject protected spans. Fails closed (ok=False) if any marker is missing/foreign."""
    expected = set(range(len(spans)))
    seen: set[int] = set()
    for m in _PS.finditer(masked):
        idx = int(m.group(1))
        if idx not in expected or idx in seen:
            return masked, False
        seen.add(idx)

    if seen != expected:
        return masked, False

    def sub(m: re.Match[str]) -> str:
        return spans[int(m.group(1))].text

    return _PS.sub(sub, masked), True