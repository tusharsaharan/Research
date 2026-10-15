from __future__ import annotations

import pytest

from gateway.modules.m1_pipeline.hinglish import language_group
from gateway.pricing import estimate_cost_usd, savings_vs_premium, tier_cost_usd


@pytest.mark.parametrize(
    ("text", "group"),
    [
        ("What is the capital of France?", "english"),
        ("hi, can you help me with my code?", "english"),
        ("There are the plants in the garden near the house.", "english"),
        ("yaar mera wifi slow hai kya karun", "hinglish"),
        ("mujhe python sikhna hai", "hinglish"),
        ("मेरा phone charge nahi ho raha", "mixed_script"),
    ],
)
def test_language_group(text, group):
    assert language_group(text) == group


def test_output_tokens_cost_more_than_input():
    assert tier_cost_usd("premium", 0, 1000) == pytest.approx(4 * tier_cost_usd("premium", 1000, 0))


def test_premium_is_twice_cheap_for_gpt_oss_pair():
    assert tier_cost_usd("premium", 300, 500) == pytest.approx(2 * tier_cost_usd("cheap", 300, 500))
    assert savings_vs_premium(300, 500, "cheap") == pytest.approx(tier_cost_usd("cheap", 300, 500))
    assert savings_vs_premium(300, 500, "premium") == 0.0


def test_legacy_single_rate_still_supported():
    assert estimate_cost_usd(1000, 1000, 0.001) == pytest.approx(0.002)
