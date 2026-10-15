"""Single source of truth for LLM pricing.

All cost calculations must import from here — never hardcode rates inline.
Update PRICING_DATE when rates change and keep FX in sync with config.

Rates are the configured study pair on Groq (USD per token, list prices from
console.groq.com/docs/models, accessed 2026-09-26; see docs/research/DECISIONS.md
§3b). Input and output are priced separately because output (including gpt-oss
reasoning tokens, which providers bill as completion tokens) costs 4x input.
Token counts come from provider usage when available, otherwise TokenCounter
(tiktoken if installed, else whitespace) — then $/₹ are approximate.
"""

PRICING_DATE = "2026-09-26"
CHEAP_MODEL = "openai/gpt-oss-20b"
PREMIUM_MODEL = "openai/gpt-oss-120b"

# USD per 1K tokens.
CHEAP_PER_1K_USD = 0.000075  # gpt-oss-20b input ($0.075 / MTok)
CHEAP_OUT_PER_1K_USD = 0.00030  # gpt-oss-20b output ($0.30 / MTok)
PREMIUM_PER_1K_USD = 0.00015  # gpt-oss-120b input ($0.15 / MTok)
PREMIUM_OUT_PER_1K_USD = 0.00060  # gpt-oss-120b output ($0.60 / MTok)
FX_INR_PER_USD = 83.5

RATES_PER_1K = {
    "cheap": (CHEAP_PER_1K_USD, CHEAP_OUT_PER_1K_USD),
    "premium": (PREMIUM_PER_1K_USD, PREMIUM_OUT_PER_1K_USD),
}


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    per_1k: float,
    out_per_1k: float | None = None,
) -> float:
    """Cost of one call; ``out_per_1k`` defaults to ``per_1k`` for legacy callers."""
    out = per_1k if out_per_1k is None else out_per_1k
    return (prompt_tokens * per_1k + completion_tokens * out) / 1000.0


def tier_cost_usd(tier: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = RATES_PER_1K[tier]
    return estimate_cost_usd(prompt_tokens, completion_tokens, inp, out)


def savings_vs_premium(prompt_tokens: int, completion_tokens: int, tier: str) -> float:
    if tier != "cheap":
        return 0.0
    premium = tier_cost_usd("premium", prompt_tokens, completion_tokens)
    cheap = tier_cost_usd("cheap", prompt_tokens, completion_tokens)
    return max(0.0, premium - cheap)
