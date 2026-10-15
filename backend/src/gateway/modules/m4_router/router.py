from __future__ import annotations

import time

from gateway.llm import BaseLLMClient
from gateway.modules.m1_pipeline.hinglish import language_group
from gateway.modules.m3_conformal.conformal import ConformalCalibrator
from gateway.modules.m4_router.difficulty import DifficultyScorer
from gateway.pricing import (
    CHEAP_OUT_PER_1K_USD,
    CHEAP_PER_1K_USD,
    PREMIUM_OUT_PER_1K_USD,
    PREMIUM_PER_1K_USD,
    estimate_cost_usd,
)
from gateway.schemas import DispatchResult
from gateway.tokenizer import TokenCounter


class CascadeRouter:
    """Routes a compressed prompt to the cheap or premium tier (configured model pair)
    using a conformally-calibrated difficulty threshold."""

    def __init__(
        self,
        calibrator: ConformalCalibrator,
        cheap_client: BaseLLMClient,
        premium_client: BaseLLMClient,
        scorer: DifficultyScorer | None = None,
        counter: TokenCounter | None = None,
        dry_run: bool = True,
        cheap_cost_per_1k: float = CHEAP_PER_1K_USD,
        premium_cost_per_1k: float = PREMIUM_PER_1K_USD,
        cheap_out_per_1k: float = CHEAP_OUT_PER_1K_USD,
        premium_out_per_1k: float = PREMIUM_OUT_PER_1K_USD,
    ) -> None:
        self.calibrator = calibrator
        self.cheap_client = cheap_client
        self.premium_client = premium_client
        self.scorer = scorer or DifficultyScorer(counter)
        self.counter = counter or TokenCounter()
        self.dry_run = dry_run
        self.cost_per_1k = {
            "cheap": (cheap_cost_per_1k, cheap_out_per_1k),
            "premium": (premium_cost_per_1k, premium_out_per_1k),
        }

    def _estimate_cost(self, tier: str, prompt_tokens: int, completion_tokens: int) -> float:
        inp, out = self.cost_per_1k[tier]
        return estimate_cost_usd(prompt_tokens, completion_tokens, inp, out)

    async def dispatch_query(
        self, text: str, task_id: str | None = None, temperature: float = 0.0, max_tokens: int | None = None
    ) -> DispatchResult:
        task_id = task_id or f"cmg-{id(self):x}-{int(time.time() * 1e6)}"
        score = self.scorer.score(text)
        # Per-language thresholds when the calibrator was fitted per group
        # (Mondrian); otherwise route_premium falls back to the pooled threshold.
        group = language_group(text)
        threshold = (
            self.calibrator.group_thresholds.get(group, self.calibrator.threshold)
            if self.calibrator.is_mondrian
            else self.calibrator.threshold
        )
        tier = "premium" if self.calibrator.route_premium(score, group) else "cheap"
        client = self.premium_client if tier == "premium" else self.cheap_client

        start = time.perf_counter()
        result = await client.chat([{"role": "user", "content": text}], temperature=temperature, max_tokens=max_tokens)
        latency_ms = (time.perf_counter() - start) * 1000.0

        prompt_tokens = self.counter.count(text)
        completion_tokens = result.usage.completion_tokens or self.counter.count(result.content)
        cost = self._estimate_cost(tier, prompt_tokens, completion_tokens)

        return DispatchResult(
            task_id=task_id,
            model_routed=result.model,
            score=score,
            threshold=threshold,
            tier=tier,
            response=result.content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_est_usd=round(cost, 8),
            latency_ms=round(latency_ms, 3),
            dry_run=self.dry_run,
        )