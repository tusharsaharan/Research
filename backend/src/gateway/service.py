from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from gateway.config import Settings, get_settings
from gateway.llm import build_client
from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m3_conformal.conformal import ConformalCalibrator
from gateway.modules.m4_router.difficulty import DifficultyScorer
from gateway.modules.m4_router.router import CascadeRouter
from gateway.modules.m6_telegram.db import LogDB
from gateway.modules.m9_reasoning.budget import (
    HinglishEnglishBudgetComparator,
    ReasoningBudgetEstimator,
)
from gateway.schemas import (
    CalibSample,
    ChatCompletionRequest,
    ChatCompletionResponse,
    GatewayMeta,
)
from gateway.tokenizer import TokenCounter


def default_calibration(n: int = 2000, seed: int = 42) -> list[CalibSample]:
    rng = np.random.default_rng(seed)
    samples: list[CalibSample] = []
    for i in range(n):
        fail = rng.random() < 0.30
        s = rng.uniform(0.25, 0.65) if fail else rng.uniform(0.02, 0.22)
        samples.append(
            CalibSample(
                id=f"cal-{i:04d}",
                nonconformity=round(float(np.clip(s, 0.0, 1.0)), 6),
                cheap_success=not fail,
            )
        )
    return samples


def load_calibration(data_dir: Path) -> list[CalibSample]:
    path = data_dir / "calibration.jsonl"
    if path.exists():
        samples = [
            CalibSample.model_validate(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if samples:
            return samples
    return default_calibration()


class Gateway:
    """Assembles compressor + conformal router into a single request pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        s = self.settings
        self.counter = TokenCounter()

        distilled_map: dict[str, str] = {}
        try:
            from gateway.modules.m10_train.distill import load_mapping

            distilled_map = load_mapping(s.distilled_checkpoint)
        except Exception:
            distilled_map = {}
        self.compressor = Compressor(
            counter=self.counter,
            client=build_client(
                "local",
                model=s.local.model,
                base_url=s.local.base_url,
                api_key=s.local.api_key,
                dry_run=s.dry_run,
                canned=self._mock_compressed(),
                timeout=s.timeout_s,
            ),
            use_model=not s.dry_run,
            distilled_map=distilled_map,
            use_llmlingua2=s.llmlingua2,
            llmlingua2_rate=s.llmlingua2_rate,
            use_crf=s.use_crf,
            crf_model_path=s.crf_model_path,
            tfidf_path=s.tfidf_path,
        )

        calibration = load_calibration(s.data_dir)
        self.calibration: list[CalibSample] = calibration
        self.calibrator = ConformalCalibrator(alpha=s.alpha).calibrate(calibration)

        self.router = CascadeRouter(
            calibrator=self.calibrator,
            cheap_client=build_client(
                "cheap", s.cheap.model, s.cheap.base_url, s.cheap.api_key, s.dry_run, timeout=s.timeout_s
            ),
            premium_client=build_client(
                "premium", s.premium.model, s.premium.base_url, s.premium.api_key, s.dry_run, timeout=s.timeout_s
            ),
            scorer=DifficultyScorer(self.counter),
            counter=self.counter,
            dry_run=s.dry_run,
        )

        self.budget_estimator = ReasoningBudgetEstimator(self.counter)
        self.budget_comparator = HinglishEnglishBudgetComparator(self.budget_estimator)

    @staticmethod
    def _mock_compressed() -> str:
        return "[[COMPRESSED]]"

    def build_meta(self, compressed, dispatch, user_text: str) -> GatewayMeta:
        premium_cost = self.router._estimate_cost(
            "premium", compressed.token_original, dispatch.completion_tokens
        )
        savings = max(0.0, premium_cost - dispatch.cost_est_usd)
        budget = self.budget_estimator.estimate(user_text)
        gloss = self.budget_comparator.gloss_for(user_text)
        budget_delta = (
            self.budget_comparator.delta(user_text, gloss) if gloss is not None else None
        )
        n_cal = len(self.calibration)
        # Primary guarantee is the Hoeffding LTT bound from the calibrator
        # (R_hat + sqrt(log(m/delta)/2n)), not the simple 1/(n+1) split-conformal bound.
        error_bound = (
            round(self.calibrator.risk_bound, 6) if n_cal else self.calibrator.alpha
        )
        return GatewayMeta(
            original_tokens=compressed.token_original,
            compressed_tokens=compressed.token_compressed,
            compression_ratio=compressed.ratio,
            compressed_prompt=compressed.compressed,
            difficulty_score=dispatch.score,
            conformal_threshold=dispatch.threshold,
            tier=dispatch.tier,
            model_routed=dispatch.model_routed,
            estimated_cost_usd=dispatch.cost_est_usd,
            estimated_cost_savings_usd=round(savings, 8),
            reasoning_budget=budget.reasoning_tokens,
            budget_delta_hinglish_en=budget_delta,
            error_bound=error_bound,
            calibration_n=n_cal,
        )

    async def handle(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        user_text = self._last_user_text(request)
        compressed = await self.compressor.compress(user_text)
        dispatch = await self.router.dispatch_query(
            compressed.compressed, temperature=request.temperature, max_tokens=request.max_tokens
        )
        meta = self.build_meta(compressed, dispatch, user_text)

        response = ChatCompletionResponse(
            id=dispatch.task_id,
            created=int(time.time()),
            model=dispatch.model_routed,
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": dispatch.response},
                    "finish_reason": "stop",
                }
            ],
            usage={
                "prompt_tokens": dispatch.prompt_tokens,
                "completion_tokens": dispatch.completion_tokens,
                "total_tokens": dispatch.prompt_tokens + dispatch.completion_tokens,
            },
            x_gateway=meta,
        )
        if self.settings.log_requests:
            try:
                user_id = request.user or "anonymous"
                get_log_db().log(
                    user_id=user_id,
                    original_tokens=compressed.token_original,
                    compressed_tokens=compressed.token_compressed,
                    model_routed=dispatch.model_routed,
                    estimated_cost_savings=float(meta.estimated_cost_savings_usd),
                    task_id=dispatch.task_id,
                    compressed_prompt=compressed.compressed,
                    tier=dispatch.tier,
                    difficulty_score=dispatch.score,
                )
            except Exception:
                pass
        return response

    @staticmethod
    def _last_user_text(request: ChatCompletionRequest) -> str:
        for msg in reversed(request.messages):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    return msg.content
                parts = [p.get("text", "") for p in msg.content if isinstance(p, dict)]
                return " ".join(parts)
        raise ValueError("No user message provided.")


@lru_cache
def get_log_db() -> LogDB:
    return LogDB(get_settings().pilot_db)