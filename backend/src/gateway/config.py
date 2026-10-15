from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gateway.pricing import FX_INR_PER_USD, PRICING_DATE


class TierConfig(BaseModel):
    model: str
    base_url: str
    api_key: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GATEWAY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    dry_run: bool = True
    alpha: float = 0.05
    data_dir: Path = Path("data")
    pilot_db: Path = Path("data/pilot.sqlite")
    fx_rate_inr_per_usd: float = FX_INR_PER_USD
    log_requests: bool = True
    cors_origins: list[str] = ["*"]
    compressor_method: str = "heuristic"
    llmlingua2: bool = False
    llmlingua2_rate: float = 0.5
    use_crf: bool = True
    crf_model_path: Path = Path("data/models/crf_compressor.pkl")
    tfidf_path: Path = Path("data/tfidf/hinglish_idf.json")
    crf_aggressive: bool = False
    distilled_checkpoint: Path = Path("data/checkpoints/distilled.json")
    pricing_date: str = PRICING_DATE
    timeout_s: float = 30.0
    telegram_webhook_secret: str = ""
    public_url: str = "http://127.0.0.1:8000"

    # Defaults match the study pair (Groq free tier); llama-3.1-8b-instant was
    # retired by Groq and gpt-4o needs a paid key. backend/.env overrides both.
    cheap: TierConfig = TierConfig(model="openai/gpt-oss-20b", base_url="https://api.groq.com/openai/v1")
    premium: TierConfig = TierConfig(model="openai/gpt-oss-120b", base_url="https://api.groq.com/openai/v1")
    # Ollama tag; HF hub id is Qwen/Qwen3-0.6B (see grpo_config.py)
    local: TierConfig = TierConfig(model="qwen3:0.6b", base_url="http://localhost:11434/v1")

    telegram_token: str = ""

    @field_validator("data_dir", "pilot_db", "distilled_checkpoint", "crf_model_path", "tfidf_path", mode="before")
    @classmethod
    def _resolve_path(cls, v):
        if isinstance(v, str):
            v = Path(v)
        if isinstance(v, Path) and not v.is_absolute():
            # Resolve relative to backend/ directory (src/gateway/config.py -> backend/)
            backend_root = Path(__file__).resolve().parents[2]
            v = (backend_root / v).resolve()
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()