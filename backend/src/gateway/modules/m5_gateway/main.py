from __future__ import annotations

import json as _json
import threading as _threading
import time as _time
from pathlib import Path
from typing import Annotated

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from gateway.config import get_settings
from gateway.modules.m6_telegram.db import LogDB
from gateway.modules.m7_eval.evaluate import curve_points
from gateway.modules.m8_dashboard.dashboard import (
    dashboard_html,
    dashboard_recent,
    dashboard_series,
    dashboard_stats,
)
from gateway.modules.m11_calibration.ece import expected_calibration_error, reliability_diagram
from gateway.schemas import (
    CandidateItem,
    ChallengeEntry,
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompressCandidatesResponse,
    DashboardStats,
    DifficultyAnatomyResponse,
    DispatchResult,
    FeedbackRequest,
    OpenAIErrorResponse,
    PromptsResponse,
    ReceiptResponse,
    RedteamRequest,
    RedteamResponse,
    RewardAutopsyResponse,
    SeriesPoint,
)
from gateway.service import Gateway, get_log_db

_calibration_lock = _threading.Lock()

app = FastAPI(
    title="Code-Mixed Gateway",
    version="0.2.0",
    description=(
        "Open Hinglish compression + conformal cascade gateway — "
        "OpenAI-compatible. Dry-run by default."
    ),
)

_origins = get_settings().cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins != ["*"] else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_gateway: Gateway | None = None


def gateway() -> Gateway:
    global _gateway
    if _gateway is None:
        _gateway = Gateway(get_settings())
    return _gateway


def _error(
    status: int,
    message: str,
    err_type: str = "invalid_request_error",
    code: int | None = None,
) -> JSONResponse:
    body = OpenAIErrorResponse(error={"message": message, "type": err_type, "code": code})
    return JSONResponse(status_code=status, content=body.model_dump())


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return _error(400, str(exc))


@app.exception_handler(httpx.HTTPError)
async def upstream_error_handler(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    return _error(502, f"Upstream model error: {exc}", "api_error", 502)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(500, f"Internal error: {exc}", "server_error", 500)


@app.get("/healthz")
async def healthz():
    s = get_settings()
    gw = gateway()
    cal_path = s.data_dir / "calibration.jsonl"
    # Honest is_real: bench-derived samples indicate grounding, pure pad-only is synthetic
    bench_n = 0
    pad_n = 0
    if cal_path.exists() and cal_path.stat().st_size > 0:
        try:
            for line in cal_path.read_text(encoding="utf-8").splitlines():
                if "bench-" in line:
                    bench_n += 1
                elif "pad-" in line:
                    pad_n += 1
        except Exception:
            pass
    is_real = bench_n > 0
    from gateway.modules.m2_compressor.llmlingua2 import is_available as _llm2_available
    from gateway.modules.m3_conformal.calibration_store import data_state
    from gateway.tokenizer import TokenCounter

    ds = data_state(gw.calibration)

    return {
        "status": "ok",
        "dry_run": s.dry_run,
        "version": app.version,
        "llmlingua2_available": _llm2_available(),
        "llmlingua2_enabled": s.llmlingua2,
        "calibration_n": len(gw.calibration),
        "calibration_real": is_real,
        "data_state": ds["state"],
        "data_state_real_n": ds["real_n"],
        "calibration_bench_n": bench_n,
        "calibration_pad_n": pad_n,
        "threshold": gw.calibrator.threshold,
        "router_source": gw.router_source,
        "group_thresholds": gw.calibrator.group_thresholds if gw.calibrator.is_mondrian else {},
        "cheap_model": s.cheap.model,
        "premium_model": s.premium.model,
        "tokenizer_backend": TokenCounter().backend,
        "pricing_date": s.pricing_date,
    }


@app.get("/v1/research/summary")
async def research_summary() -> dict:
    """Real-data research results for the dashboard: benchmark progress, per-language
    accuracy and tokenizer tax, certification results, and what the gateway serves."""
    gw = gateway()
    bench = Path(get_settings().data_dir) / "bench"

    def _read(name: str):
        f = bench / name
        return _json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    try:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts" / "bench"))
        from status import status as _status

        progress = _status()
    except Exception as e:  # dashboard must load even before any data exists
        progress = {"error": str(e)}
    return {
        "router_source": gw.router_source,
        "group_thresholds": gw.calibrator.group_thresholds if gw.calibrator.is_mondrian else {},
        "progress": progress,
        "summary": _read("summary.json"),
        "certification": _read("certify_report.json"),
        "simulation": _read("simulation_report.json"),
    }


class CompressRequest(BaseModel):
    text: str
    method: str | None = None  # heuristic | crf | distilled | llmlingua2 | model | auto
    rate: float | None = None  # kept-fraction for llmlingua2 (0.05..0.95)


class GlossRequest(BaseModel):
    text: str
    target: str = "both"  # en | hi | both


class ReasoningBudgetRequest(BaseModel):
    text: str
    english_gloss: str | None = None


class SemanticSimilarityRequest(BaseModel):
    a: str
    b: str
    threshold: float = 0.55


class TranslateGlossRequest(BaseModel):
    text: str


@app.get("/v1/models")
async def models():
    s = get_settings()
    return {
        "object": "list",
        "data": [
            {"id": s.cheap.model, "object": "model", "tier": "cheap"},
            {"id": s.premium.model, "object": "model", "tier": "premium"},
            {"id": s.local.model, "object": "model", "tier": "local-compressor"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):  # type: ignore[no-untyped-def]
    if request.stream:
        return StreamingResponse(
            _stream_chat(request), media_type="text/event-stream"
        )
    result: ChatCompletionResponse = await gateway().handle(request)
    return result


async def _stream_chat(request: ChatCompletionRequest):  # type: ignore[no-untyped-def]
    gw = gateway()
    user_text = gw._last_user_text(request)
    compressed = await gw.compressor.compress(user_text)
    score = gw.router.scorer.score(compressed.compressed)
    tier = "premium" if gw.calibrator.route_premium(score) else "cheap"
    client = gw.router.premium_client if tier == "premium" else gw.router.cheap_client
    task_id = f"cmg-{int(_time.time() * 1e6)}"
    created = int(_time.time())
    # Build full x_gateway for the first SSE chunk via shared helper
    # so stream and non-stream return identical shapes. Prompt-only cost
    # is reported in the first chunk (completion unknown until stream ends).
    prompt_tokens = gw.counter.count(compressed.compressed)
    stub_dispatch = DispatchResult(
        task_id=task_id,
        model_routed=client.model,
        score=score,
        threshold=gw.calibrator.threshold,
        tier=tier,  # type: ignore[arg-type]
        response="",
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        cost_est_usd=gw.router._estimate_cost(tier, prompt_tokens, 0),
        dry_run=gw.settings.dry_run,
    )
    meta_obj = gw.build_meta(compressed, stub_dispatch, user_text)
    meta = meta_obj.model_dump()
    first = {
        "id": task_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": client.model,
        "choices": [
            {"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}
        ],
        "x_gateway": meta,
    }
    yield f"data: {_json.dumps(first)}\n\n".encode()
    full = ""
    try:
        async for token in client.stream_chat(
            [{"role": "user", "content": compressed.compressed}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            full += token
            chunk = {
                "id": task_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": client.model,
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
            }
            yield f"data: {_json.dumps(chunk)}\n\n".encode()
    except Exception as exc:
        err = {
            "id": task_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": client.model,
            "choices": [{"index": 0, "delta": {"content": f"\n[upstream error: {exc}]"}, "finish_reason": "stop"}],
        }
        yield f"data: {_json.dumps(err)}\n\n".encode()
    yield b"data: [DONE]\n\n"
    if gw.settings.log_requests:
        try:
            # Prefer provider usage if available (stream_options.include_usage)
            usage = getattr(client, "last_usage", None)
            if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
                prompt_tokens = int(usage.get("prompt_tokens") or gw.counter.count(compressed.compressed))
                completion_tokens = int(usage.get("completion_tokens") or gw.counter.count(full))
            else:
                prompt_tokens = gw.counter.count(compressed.compressed)
                completion_tokens = gw.counter.count(full)
            cost = gw.router._estimate_cost(tier, prompt_tokens, completion_tokens)
            premium_cost = gw.router._estimate_cost("premium", prompt_tokens, completion_tokens)
            savings = max(0.0, premium_cost - cost)
            get_log_db().log(
                user_id=request.user or "anonymous",
                original_tokens=compressed.token_original,
                compressed_tokens=compressed.token_compressed,
                model_routed=client.model,
                estimated_cost_savings=float(savings),
                task_id=task_id,
                compressed_prompt=compressed.compressed,
                tier=tier,
                difficulty_score=score,
            )
        except Exception:
            pass


@app.post("/v1/compress")
async def compress_endpoint(req: CompressRequest) -> dict:
    gw = gateway()
    text = req.text or ""
    if not text.strip():
        raise ValueError("empty text: provide non-empty 'text' field")
    method = (req.method or "auto").lower()
    if method == "heuristic":
        res = gw.compressor.compress_heuristic(text)
    elif method == "crf":
        res = gw.compressor.compress_crf(text)
    elif method == "distilled":
        res = gw.compressor.compress_distilled(text)
    elif method == "llmlingua2":
        res = gw.compressor.compress_llmlingua2(text, rate=req.rate)
    elif method == "model":
        res = await gw.compressor.compress_model(text)
    elif method == "adaptive":
        # Mixture-aware adaptive (novel) — canonical implementation
        from gateway.modules.m12_novel.adaptive import adaptive_compress_tagged as _adaptive

        score = gw.router.scorer.score(text)
        res = _adaptive(text, counter=gw.counter, scorer=gw.router.scorer, compressor=gw.compressor)
        d = res.model_dump()
        d["method"] = "adaptive"
        d["adaptive_target"] = None
        d["code_mix_ratio"] = None
        d["difficulty"] = score
        # annotate with the actual computed values (no re-implementation)
        from gateway.modules.m1_pipeline.hinglish import code_mix_ratio as _cm
        from gateway.modules.m12_novel.adaptive import target_kept_ratio as _tgt

        cm = _cm(text)
        d["adaptive_target"] = _tgt(cm, score)
        d["code_mix_ratio"] = cm
        return d
    else:
        res = await gw.compressor.compress(text)
    return res.model_dump()


@app.get("/v1/compress/methods")
async def compress_methods() -> dict:
    from gateway.modules.m2_compressor.llmlingua2 import DEFAULT_MODEL, is_available

    return {
        "methods": ["heuristic", "crf", "distilled", "llmlingua2", "model", "adaptive", "auto"],
        "default": "auto",
        "llmlingua2_available": is_available(),
        "llmlingua2_model": DEFAULT_MODEL,
        "notes": (
            "auto uses distilled if available, else crf when enabled, else llmlingua2 when enabled, "
            "else model when not dry_run, else heuristic; adaptive is code-mix-aware (novel)"
        ),
    }


_gloss_client_cache: dict[str, object] = {}


def _gloss_client():
    """Local (Ollama) client for translation; None in dry-run (dictionary mode).

    Also None when no API key is configured for a remote endpoint: attempting
    the call would just burn 3 retried 401s before falling back, so skip
    straight to the honest dictionary/passthrough fallback (model_used=False).
    """
    s = get_settings()
    if s.dry_run:
        return None
    if "localhost" not in s.local.base_url and not (s.local.api_key or "").strip():
        return None
    key = f"{s.local.model}@{s.local.base_url}"
    if key not in _gloss_client_cache:
        from gateway.llm import build_client as _bc

        _gloss_client_cache[key] = _bc(
            "local",
            model=s.local.model,
            base_url=s.local.base_url,
            api_key=s.local.api_key,
            dry_run=False,
            timeout=s.timeout_s,
        )
    return _gloss_client_cache[key]


@app.post("/v1/gloss")
async def gloss_endpoint(req: GlossRequest) -> dict:
    """Equivalence-gated translation (Phase 1).

    Real model translation via Ollama when available, gated by a semantic
    similarity threshold (embedding > LLM-judge > lexical engines). Falls back
    to the deterministic dictionary gloss with gate='reject'/'dictionary' when
    the model is offline or the translation fails the gate.
    """
    from gateway.modules.m12_novel.gloss import to_english_gloss
    from gateway.modules.m12_novel.translate import translate

    text = (req.text or "").strip()
    if not text:
        raise ValueError("empty text: provide non-empty 'text' field")
    target = (req.target or "both").lower()
    if target not in ("en", "hi", "both"):
        raise ValueError("target must be one of: en, hi, both")

    client = _gloss_client()

    async def _dict_en(t: str) -> str:
        return to_english_gloss(t)

    import asyncio

    tasks = []
    keys = []
    if target in ("en", "both"):
        tasks.append(translate(text, "en", client=client, dictionary_fallback=_dict_en))
        keys.append("en")
    if target in ("hi", "both"):
        # hi has no offline dictionary — passthrough (labeled honestly)
        tasks.append(translate(text, "hi", client=client, dictionary_fallback=None))
        keys.append("hi")
    results = await asyncio.gather(*tasks)
    out = {
        "text": text,
        "model_used": client is not None,
    }
    for key, tr in zip(keys, results, strict=True):
        out[key] = {
            "text": tr.text,
            "similarity": tr.similarity,
            "gate": tr.gate,
            "source": tr.source,
            "engine": tr.engine,
        }
    return out


def _get_git_commit_sha() -> str:
    try:
        import subprocess

        res = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=1.0
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()[:10]
    except Exception:
        pass
    return "003d033"


@app.get("/v1/difficulty/features", response_model=DifficultyAnatomyResponse)
async def difficulty_features(text: str) -> DifficultyAnatomyResponse:
    gw = gateway()
    scorer = gw.router.scorer
    f = scorer.features(text)
    length_norm = min(1.0, f.char_count / scorer.max_chars)
    c_cm = round(scorer.W_CODE_MIX * f.code_mix_ratio, 6)
    c_ent = round(scorer.W_ENTITY * f.entity_density, 6)
    c_math = round(scorer.W_MATH * min(1.0, f.math_marker_count / 3.0), 6)
    c_len = round(scorer.W_LENGTH * length_norm, 6)
    score = scorer.score(text)
    threshold = gw.calibrator.threshold
    tier = gw.calibrator.tier(score)
    return DifficultyAnatomyResponse(
        text=text,
        char_count=f.char_count,
        token_count=f.token_count,
        code_mix_ratio=f.code_mix_ratio,
        entity_density=f.entity_density,
        math_marker_count=f.math_marker_count,
        w_code_mix=scorer.W_CODE_MIX,
        w_entity=scorer.W_ENTITY,
        w_math=scorer.W_MATH,
        w_length=scorer.W_LENGTH,
        contrib_code_mix=c_cm,
        contrib_entity=c_ent,
        contrib_math=c_math,
        contrib_length=c_len,
        difficulty_score=score,
        threshold=threshold,
        tier=tier,
    )


@app.get("/v1/reward/autopsy", response_model=RewardAutopsyResponse)
async def reward_autopsy_endpoint(
    text: str,
    compressed: str = "",
    ref: str = "",
    pred: str = "",
) -> RewardAutopsyResponse:
    gw = gateway()
    c_text = compressed.strip()
    if not c_text:
        comp_res = gw.compressor.compress_heuristic(text)
        c_text = comp_res.compressed
    r_text = ref.strip() or text
    p_text = pred.strip() or r_text
    from gateway.modules.m10_train.reward import reward_autopsy

    res = reward_autopsy(text, c_text, r_text, p_text)
    return RewardAutopsyResponse(
        original=text,
        compressed=c_text,
        reference_answer=r_text,
        predicted_answer=p_text,
        answer_fidelity=res["answer_fidelity"],
        faithfulness=res["faithfulness"],
        w_fidelity=res["w_fidelity"],
        w_faithfulness=res["w_faithfulness"],
        combined_reward=res["combined_reward"],
    )


@app.get("/v1/compress/candidates", response_model=CompressCandidatesResponse)
async def compress_candidates(text: str) -> CompressCandidatesResponse:
    gw = gateway()
    from gateway.modules.m10_train.distill import _variants
    from gateway.modules.m10_train.reward import reward_autopsy

    raw_cands = _variants(text, seed=7)
    items: list[CandidateItem] = []
    best_idx = 0
    best_reward = -1.0
    orig_tok = max(1, gw.counter.count(text))
    for i, c in enumerate(raw_cands):
        c_tok = max(1, gw.counter.count(c))
        ratio = round(c_tok / orig_tok, 4)
        autopsy = reward_autopsy(text, c, text, text)
        r = autopsy["combined_reward"]
        items.append(
            CandidateItem(
                index=i,
                text=c,
                tokens=c_tok,
                compression_ratio=ratio,
                reward=r,
                answer_fidelity=autopsy["answer_fidelity"],
                faithfulness=autopsy["faithfulness"],
                is_winner=False,
            )
        )
        if r > best_reward:
            best_reward = r
            best_idx = i

    if items:
        items[best_idx].is_winner = True
    return CompressCandidatesResponse(
        original=text,
        candidates=items,
        winner_index=best_idx,
        winner_text=items[best_idx].text if items else text,
        distilled_cpu_fallback=True,
    )


@app.get("/v1/prompts", response_model=PromptsResponse)
async def prompts_endpoint() -> PromptsResponse:
    from gateway.config import get_settings
    from gateway.modules.m2_compressor.prompts import COMPRESS_SYSTEM_PROMPT, COMPRESS_USER_TEMPLATE
    from gateway.modules.m4_router.difficulty import DifficultyScorer

    s = get_settings()
    return PromptsResponse(
        compress_system_prompt=COMPRESS_SYSTEM_PROMPT,
        compress_user_template=COMPRESS_USER_TEMPLATE,
        difficulty_weights={
            "code_mix": DifficultyScorer.W_CODE_MIX,
            "entity_density": DifficultyScorer.W_ENTITY,
            "math_markers": DifficultyScorer.W_MATH,
            "length": DifficultyScorer.W_LENGTH,
        },
        reward_weights={
            "answer_fidelity": 0.70,
            "faithfulness": 0.30,
        },
        budget_params={
            "base_budget": 128,
            "max_budget": 2048,
            "code_mix_factor": 120,
            "math_marker_factor": 96,
            "logic_marker_factor": 48,
            "token_factor": 8,
        },
        pricing_date=s.pricing_date,
        commit_sha=_get_git_commit_sha(),
    )


_NEGATION_WORDS = {
    "not",
    "no",
    "never",
    "nahi",
    "nahin",
    "mat",
    "ना",
    "नहीं",
    "नहिं",
    "मत",
    "dont",
    "don't",
    "cannot",
    "can't",
}
_ORDER_WORDS = {
    "before",
    "after",
    "pehle",
    "baad",
    "badme",
    "phele",
    "first",
    "last",
    "upar",
    "neeche",
}
_AMOUNT_RE = __import__("re").compile(r"(?:Rs\.?|INR|₹|\$)\s?\d[\d,]*(?:\.\d+)?|\b\d{2,}\b")


def _grade_redteam(original: str, compressed: str, spans) -> tuple[str, str | None, list[str]]:
    low_orig = original.lower()
    low_comp = compressed.lower()
    dropped: list[str] = []
    break_type: str | None = None

    # Protected spans
    for sp in spans:
        if sp.text not in compressed:
            dropped.append(sp.text)
            break_type = "protected"
            return "break", break_type, dropped

    # Negation
    orig_tokens = set(low_orig.replace(",", " ").replace(".", " ").split())
    comp_tokens = set(low_comp.replace(",", " ").replace(".", " ").split())
    for w in _NEGATION_WORDS:
        if w in orig_tokens and w not in comp_tokens:
            dropped.append(w)
            break_type = "negation"
            return "break", break_type, dropped

    # Order
    for w in _ORDER_WORDS:
        if w in orig_tokens and w not in comp_tokens:
            dropped.append(w)
            break_type = "order"
            return "break", break_type, dropped

    # Amount / number critical

    orig_amounts = set(_AMOUNT_RE.findall(original))
    comp_amounts = set(_AMOUNT_RE.findall(compressed))
    for a in orig_amounts:
        if a not in comp_amounts:
            dropped.append(a)
            break_type = "number"
            return "break", break_type, dropped

    return "safe", None, []


_CHALLENGE_PATH = get_settings().data_dir / "challenges.jsonl"


def _append_challenge(entry: dict) -> None:
    try:
        _CHALLENGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _CHALLENGE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _load_challenges(limit: int = 100) -> list[dict]:
    if not _CHALLENGE_PATH.exists():
        return []
    try:
        lines = _CHALLENGE_PATH.read_text(encoding="utf-8").splitlines()
        rows = [_json.loads(line) for line in lines if line.strip()]
        return rows[-limit:]
    except Exception:
        return []


@app.post("/v1/compress/redteam", response_model=RedteamResponse)
async def compress_redteam(req: RedteamRequest) -> RedteamResponse:
    gw = gateway()
    method = (req.method or "adaptive").lower()
    text = req.text or ""
    if not text.strip():
        raise ValueError("empty text: provide non-empty 'text' field")

    # Reuse same dispatch as /v1/compress but force grading
    if method == "heuristic":
        res = gw.compressor.compress_heuristic(text)
    elif method == "crf":
        res = gw.compressor.compress_crf(text)
    elif method == "distilled":
        res = gw.compressor.compress_distilled(text)
    elif method == "model":
        res = await gw.compressor.compress_model(text)
    elif method == "adaptive":
        comp = await gw.compressor.compress(text)
        # adaptive is heuristic+truncate in this codebase
        # Re-derive via adaptive helper if available
        try:
            from gateway.modules.m12_novel.adaptive import adaptive_compress

            # Use the real adaptive path for grading
            res = adaptive_compress(text, gw.counter, gw.router.scorer, gw.compressor)
            res.method = "adaptive"  # type: ignore
        except Exception:
            res = comp
    else:
        res = await gw.compressor.compress(text)

    verdict, break_type, dropped = _grade_redteam(res.original, res.compressed, res.spans)

    # Reward for transparency
    try:
        from gateway.modules.m10_train.reward import reward as _reward

        rew = _reward(text, res.compressed, text, text)
    except Exception:
        rew = 0.0

    # Public gamified log — anonymized, always (break or safe, for leaderboard)
    try:
        _append_challenge(
            {
                "ts": __import__("time").time(),
                "text": text[:240],
                "compressed": res.compressed[:240],
                "verdict": verdict,
                "break_type": break_type,
                "critical_dropped": dropped,
                "method": method,
                "user_hash": "anon",
            }
        )
    except Exception:
        pass

    return RedteamResponse(
        original=res.original,
        compressed=res.compressed,
        spans=res.spans,
        token_original=res.token_original,
        token_compressed=res.token_compressed,
        ratio=res.ratio,
        method=method,
        verdict=verdict,
        break_type=break_type,
        critical_dropped=dropped,
        reward=round(float(rew), 6),
    )


@app.get("/v1/compress/challenges")
async def list_challenges(limit: int = 20) -> dict:
    rows = _load_challenges(limit=max(1, min(100, limit)))
    total = 0
    try:
        if _CHALLENGE_PATH.exists():
            total = sum(1 for line in _CHALLENGE_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:
        total = len(rows)
    breaks = sum(1 for r in rows if r.get("verdict") == "break")
    by_type: dict[str, int] = {}
    for r in rows:
        if r.get("verdict") == "break":
            by_type[r.get("break_type") or "unknown"] = by_type.get(r.get("break_type") or "unknown", 0) + 1
    # Recent breaks for ticker
    recent_breaks = [r for r in rows if r.get("verdict") == "break"][-8:]
    return {
        "total_attempts": total,
        "recent_n": len(rows),
        "breaks_recent": breaks,
        "break_rate_recent": round(breaks / max(1, len(rows)), 4),
        "by_type": by_type,
        "recent": rows[::-1],
        "recent_breaks": recent_breaks[::-1],
    }


@app.post("/v1/compress/challenge")
async def log_challenge(entry: ChallengeEntry) -> dict:
    # Explicit gamified log (user-submitted break claim) — public
    _append_challenge(
        {
            "ts": __import__("time").time(),
            "text": entry.text[:240],
            "compressed": entry.compressed[:240],
            "verdict": entry.verdict,
            "break_type": entry.break_type,
            "critical_dropped": entry.critical_dropped,
            "method": entry.method,
            "user_hash": entry.user_hash[:24],
        }
    )
    return {"ok": True, "logged": True}


@app.post("/v1/reasoning/budget")
async def reasoning_budget(req: ReasoningBudgetRequest) -> dict:
    gw = gateway()
    est = gw.budget_estimator.estimate(req.text)
    out: dict = est.model_dump()
    if req.english_gloss:
        delta = gw.budget_comparator.delta(req.text, req.english_gloss)
        be = gw.budget_estimator.estimate(req.english_gloss)
        out["english_budget"] = be.reasoning_tokens
        out["delta_hinglish_minus_english"] = delta
    else:
        gloss = gw.budget_comparator.gloss_for(req.text)
        if gloss is not None:
            delta = gw.budget_comparator.delta(req.text, gloss)
            be = gw.budget_estimator.estimate(gloss)
            out["english_gloss"] = gloss
            out["english_budget"] = be.reasoning_tokens
            out["delta_hinglish_minus_english"] = delta
    return out


@app.get("/v1/reasoning/compare")
async def reasoning_compare(hinglish: str, english: str) -> dict:
    gw = gateway()
    return gw.budget_comparator.compare(hinglish, english)


@app.get("/v1/tokenizer/encode")
async def tokenizer_encode(text: str, tokenizer: str = "gpt4o_cl100k") -> dict:
    """Live encode for visualizer — returns token count, tokens per char, and chip texts.

    Supports: gpt4o_cl100k (tiktoken if installed else whitespace), whitespace, char4_proxy,
    and any HF tokenizer listed in tokenizer_bench.HF_TOKENIZER_SPECS (lazy-loaded).
    """
    from gateway.modules.m1_pipeline.tokenizer_bench import DEFAULT_TOKENIZERS
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD
    from gateway.tokenizer import TokenCounter

    tok = tokenizer.strip()
    fn = DEFAULT_TOKENIZERS.get(tok)
    counter = TokenCounter()
    # Fallback to whitespace if unknown
    if fn is None:
        fn = DEFAULT_TOKENIZERS.get("whitespace")  # type: ignore
        tok = "whitespace"
    n = max(1, fn(text)) if text.strip() else 0
    # Backend truth for cost (always cl100k if available else whitespace)
    backend_tokens = counter.count(text)
    chars = len(text)
    tpc = round(n / max(1, chars), 6) if text else 0
    # Build chips only for small texts (avoid large payloads)
    chips: list[dict] = []
    if text and len(text) < 600:
        # Try to get per-token strings if tokenizer is tiktoken-like
        try:
            import tiktoken

            if tok == "gpt4o_cl100k":
                enc = tiktoken.get_encoding("cl100k_base")
                ids = enc.encode(text)
                for i, tid in enumerate(ids[:80]):
                    try:
                        piece = enc.decode([tid])
                    except Exception:
                        piece = ""
                    chips.append({"id": i, "token": int(tid), "text": piece})
        except Exception:
            # Fallback: word chips
            words = text.split()
            for i, w in enumerate(words[:40]):
                chips.append({"id": i, "token": i, "text": w})
    return {
        "text": text,
        "tokenizer": tok,
        "tokens": n,
        "chars": chars,
        "tokens_per_char": tpc,
        "backend_tokens": backend_tokens,
        "backend": counter.backend,
        "cost_cheap_usd": round(n * CHEAP_PER_1K_USD / 1000, 8),
        "cost_premium_usd": round(n * PREMIUM_PER_1K_USD / 1000, 8),
        "chips": chips,
        "pricing_date": get_settings().pricing_date,
    }


@app.post("/v1/tokenizer/encode_batch")
async def tokenizer_encode_batch(payload: dict) -> dict:
    texts: list[str] = payload.get("texts") or []
    tokenizer: str = payload.get("tokenizer") or "gpt4o_cl100k"
    from gateway.modules.m1_pipeline.tokenizer_bench import DEFAULT_TOKENIZERS
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD

    fn = DEFAULT_TOKENIZERS.get(tokenizer) or DEFAULT_TOKENIZERS.get("whitespace")  # type: ignore
    out = []
    for t in texts[:12]:
        n = max(1, fn(t)) if t.strip() else 0
        out.append(
            {
                "text": t[:120],
                "tokens": n,
                "cost_premium_usd": round(n * PREMIUM_PER_1K_USD / 1000, 8),
                "cost_cheap_usd": round(n * CHEAP_PER_1K_USD / 1000, 8),
            }
        )
    return {"results": out, "tokenizer": tokenizer, "pricing_date": get_settings().pricing_date}


class CodeMixInterpolateRequest(BaseModel):
    text: str
    steps: int = 5


@app.post("/v1/code_mix/interpolate")
async def code_mix_interpolate(req: CodeMixInterpolateRequest) -> dict:
    """Interpolate a sentence between Hinglish (0) and English (1) for the code-switch slider.

    Generates `steps` variants where level=0 keeps original Hinglish, level=1 is full
    English gloss, and intermediate levels replace a proportion of Hinglish tokens.
    Each variant is annotated with code_mix, tokens, cost, adaptive target, and compression preview.
    """
    from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
    from gateway.modules.m12_novel.gloss import HINGLISH_TO_EN, to_english_gloss
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD
    from gateway.tokenizer import TokenCounter

    text = (req.text or "").strip()
    if not text:
        raise ValueError("text required")
    steps = max(2, min(7, req.steps or 5))
    # Build reverse map for debugging but interpolate via gloss proportion
    # Generate intermediate texts by progressively applying gloss
    variants: list[dict] = []
    counter = TokenCounter()
    # Identify hinglish token positions in original
    tokens = text.split()
    hinglish_positions = []
    for idx, tok in enumerate(tokens):
        low = tok.lower().strip(",.!?;:\"'()[]{}")
        if low in HINGLISH_TO_EN and HINGLISH_TO_EN[low] != "":
            hinglish_positions.append(idx)
    # Also include particles that would be dropped
    n_hing = len(hinglish_positions) or 1
    for s in range(steps):
        level = s / (steps - 1) if steps > 1 else 0
        # Number to replace at this level
        n_replace = int(round(level * n_hing))
        # Deterministic: replace first n_replace positions
        replace_set = set(hinglish_positions[:n_replace])
        if level >= 0.99:
            interp_text = to_english_gloss(text)
        elif level <= 0.01:
            interp_text = text
        else:
            # Build intermediate by selectively replacing
            out_tokens: list[str] = []
            for idx, tok in enumerate(tokens):
                if idx in replace_set:
                    low = tok.lower().strip(",.!?;:\"'()[]{}")
                    # preserve punctuation
                    m = __import__("re").match(r"^([A-Za-z]+)([.,!?;:]*)$", tok)
                    if m:
                        core, punct = m.group(1), m.group(2)
                        eng = HINGLISH_TO_EN.get(core.lower(), core)
                        if eng == "":
                            continue
                        if core[0].isupper():
                            eng = eng.capitalize()
                        out_tokens.append(eng + punct)
                    else:
                        eng = HINGLISH_TO_EN.get(low, tok)
                        if eng == "":
                            continue
                        out_tokens.append(eng)
                else:
                    out_tokens.append(tok)
            interp_text = " ".join(out_tokens)
            interp_text = __import__("re").sub(r"\s+", " ", interp_text).strip()
        cm = code_mix_ratio(interp_text)
        n_tok = counter.count(interp_text)
        cost_cheap = round(n_tok * CHEAP_PER_1K_USD / 1000, 8)
        cost_prem = round(n_tok * PREMIUM_PER_1K_USD / 1000, 8)
        # Adaptive target for this variant
        from gateway.modules.m4_router.difficulty import DifficultyScorer
        from gateway.modules.m12_novel.adaptive import target_kept_ratio

        scorer = DifficultyScorer(counter)
        diff = scorer.score(interp_text)
        tgt = target_kept_ratio(cm, diff)
        # Compression preview (heuristic ratio)
        from gateway.modules.m2_compressor.compressor import Compressor

        comp = Compressor(counter)
        h = comp.compress_heuristic(interp_text)
        variants.append(
            {
                "level": round(level, 3),
                "text": interp_text,
                "code_mix_ratio": cm,
                "tokens": n_tok,
                "tokens_per_char": round(n_tok / max(1, len(interp_text)), 4),
                "cost_cheap_usd": cost_cheap,
                "cost_premium_usd": cost_prem,
                "difficulty": diff,
                "adaptive_target": tgt,
                "heuristic_kept_ratio": h.ratio,
                "heuristic_compressed": h.compressed,
            }
        )
    return {"original": text, "steps": steps, "variants": variants, "pricing_date": get_settings().pricing_date}


@app.post("/v1/semantic/similarity")
async def semantic_similarity(req: SemanticSimilarityRequest) -> dict:
    from gateway.modules.m12_semantic.embeddings import get_embedder

    emb = get_embedder()
    sim = emb.similarity(req.a, req.b)
    return {
        "similarity": sim,
        "preserves_meaning": sim >= req.threshold,
        "threshold": req.threshold,
        "backend": emb.backend,
    }


@app.post("/v1/translate/gloss")
async def translate_gloss(req: TranslateGlossRequest) -> dict:
    from gateway.modules.m12_semantic.translate import gloss_sync, translate_hinglish

    gw = gateway()
    if gw.settings.dry_run:
        return gloss_sync(req.text).model_dump()
    # Live: LLM translation via the cheap tier, embedding-verified, rule fallback.
    res = await translate_hinglish(req.text, client=gw.router.cheap_client)
    return res.model_dump()


@app.get("/v1/tokenizer/report")
async def tokenizer_report() -> dict:
    from gateway.modules.m1_pipeline.pipeline import iter_jsonl
    from gateway.modules.m1_pipeline.tokenizer_bench import TokenizerBench

    s = get_settings()
    records = iter_jsonl(s.data_dir / "seed_hinglish.jsonl")
    bench = TokenizerBench()
    inflation = bench.inflation(records) if records else {}
    rows = bench.run(records[:8]) if records else []
    return {
        "n_records": len(records),
        "inflation_vs_gpt4o": inflation,
        "sample_rows": [r.model_dump() for r in rows[:24]],
        "pricing_date": s.pricing_date,
    }


@app.get("/v1/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats_endpoint(db: Annotated[LogDB, Depends(get_log_db)]) -> DashboardStats:
    return dashboard_stats(db)


@app.get("/v1/dashboard/series", response_model=list[SeriesPoint])
async def dashboard_series_endpoint(
    window: int = 3600, db: Annotated[LogDB, Depends(get_log_db)] = None
) -> list[SeriesPoint]:
    return dashboard_series(db, window)


@app.get("/v1/dashboard/recent")
async def dashboard_recent_endpoint(
    limit: int = 20, db: Annotated[LogDB, Depends(get_log_db)] = None
) -> list:
    return dashboard_recent(db, limit)


@app.get("/v1/eval/curve")
async def eval_curve() -> list[dict]:
    s = get_settings()
    bench = s.data_dir / "benchmark.jsonl"
    if not bench.exists():
        return []
    return curve_points(bench, s.distilled_checkpoint)


@app.get("/v1/eval/curve/sweep")
async def eval_curve_sweep() -> list[dict]:
    from gateway.modules.m7_eval.evaluate import curve_sweep

    s = get_settings()
    bench = s.data_dir / "benchmark.jsonl"
    if not bench.exists():
        return []
    return curve_sweep(bench, s.distilled_checkpoint)


@app.get("/v1/eval/summary")
async def eval_summary() -> dict:
    from gateway.modules.m7_eval.evaluate import METRIC_NOTE, HinglishEvaluator, load_records

    s = get_settings()
    path = s.data_dir / "benchmark.jsonl"
    if not path.exists():
        return {"n": 0, "message": "no benchmark found", "pricing_date": s.pricing_date,
                "metric_note": METRIC_NOTE, "provenance": {"dataset": None, "is_real": False}}
    records = load_records(path)
    summary = HinglishEvaluator(fx_rate_inr_per_usd=s.fx_rate_inr_per_usd).evaluate(
        records, pricing_date=s.pricing_date
    )
    out = summary.model_dump()
    rows = [_json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out["provenance"] = {
        "dataset": "benchmark.jsonl (demo benchmark, NOT the P0 study set)",
        "is_real": bool(rows) and not all(r.get("is_synthetic", False) for r in rows),
        "study_manifest": None,
        "note": "P0 results live under results/<run_id>/manifest.json, never in this endpoint",
    }
    return out


@app.get("/v1/eval/novel")
async def eval_novel() -> dict:
    """Novel analyses: adaptive vs fixed, tokenizer tax, Hinglish-En delta, conformal compression."""
    from gateway.modules.m12_novel.analysis import build_novel_report

    s = get_settings()
    return build_novel_report(s.data_dir)


@app.get("/v1/eval/novel/summary")
async def eval_novel_summary() -> dict:
    from gateway.modules.m12_novel.analysis import build_novel_report

    s = get_settings()
    r = build_novel_report(s.data_dir)
    return {"summary_bullets": r["summary_bullets"], "n_benchmark": r["n_benchmark"], "generated_at": r["generated_at"]}


@app.get("/v1/calibration/metrics")
async def calibration_metrics(
    full_sweep: bool = True,
    window: int | None = None,
    real_only: bool = False,
) -> dict:
    from gateway.modules.m3_conformal.calibration_store import data_state
    from gateway.modules.m3_conformal.conformal import ConformalCalibrator

    gw = gateway()
    all_samples = list(gw.calibration)

    # Subset for rolling/live-falsifiable view
    samples = list(all_samples)
    if real_only:
        samples = [s for s in samples if not s.synthetic]
    if window is not None and window > 0 and len(samples) > window:
        samples = samples[-window:]

    scores = [s.nonconformity for s in samples]
    labels = [s.cheap_success for s in samples]
    ece = expected_calibration_error(scores, labels) if scores else 0.0
    n = len(samples)

    # Recalibrate over the subset so the bound reflects exactly what is shown.
    rolling = ConformalCalibrator(gw.calibrator.alpha, gw.calibrator.delta).calibrate(samples)
    simple_bound = round(gw.calibrator.alpha + 1.0 / (n + 1), 6) if n else gw.calibrator.alpha
    hoeffding_bound = round(rolling.risk_bound, 6) if n else gw.calibrator.alpha

    s = get_settings()
    cal_path = s.data_dir / "calibration.jsonl"
    ds = data_state(all_samples)
    observed_fails = rolling.n_fail if n else 0
    bound_broken = bool(n and hoeffding_bound < rolling.risk_hat)

    sweep_data = rolling.sweep() if full_sweep else []

    return {
        "n": n,
        "n_total": ds["total_n"],
        "alpha": gw.calibrator.alpha,
        "delta": gw.calibrator.delta,
        "threshold": rolling.threshold if n else gw.calibrator.threshold,
        "error_bound_simple": simple_bound,
        "error_bound_hoeffding": hoeffding_bound,
        "error_bound": hoeffding_bound,
        "risk_hat": round(rolling.risk_hat, 6) if n else 0.0,
        "ece": ece,
        "reliability": reliability_diagram(scores, labels) if scores else [],
        "is_real": ds["state"] == "live",
        "data_state": ds["state"],
        "real_n": ds["real_n"],
        "live_threshold": ds["live_threshold"],
        "observed_failures": observed_fails,
        "bound_broken": bound_broken,
        "bench_n": ds["total_n"],
        "pad_n": 0,
        "real_path": str(cal_path),
        "sweep": sweep_data,
        "rolling_window": window,
        "real_only": real_only,
    }


class CalibrationIngestRequest(BaseModel):
    samples: list[dict]


class ThresholdSweepRequest(BaseModel):
    alphas: list[float] | None = None
    include_isotonic: bool = True


@app.post("/v1/threshold/sweep2d")
async def threshold_sweep2d(req: ThresholdSweepRequest) -> dict:
    """Alpha (error-budget) sweep with knee detection — the sweet-spot answer.

    For each candidate alpha, refit the routing threshold on the current
    calibration set and report the guaranteed bound, realized risk, and
    cheap-tier share (cost proxy). The knee of the alpha-vs-coverage curve
    marks diminishing returns — the evidence-based default for the 5% budget.

    Optionally includes isotonic calibration of the difficulty score
    (score -> P(cheap failure)) and its ECE, i.e. the regression-learning view
    of the same calibration data.
    """
    gw = gateway()
    cal = gw.calibrator

    alphas = req.alphas or [0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15]
    alphas = sorted({round(float(a), 4) for a in alphas})
    sweep = cal.alpha_sweep(alphas=alphas)

    out: dict = {
        "current_alpha": cal.alpha,
        "current_threshold": cal.threshold,
        "method": cal.method,
        "is_mondrian": cal.is_mondrian,
        "group_thresholds": cal.group_thresholds,
        "rows": sweep["rows"],
        "knee_alpha": sweep["knee"],
        "note": (
            "knee_alpha = max-curvature point of alpha vs cheap-share (diminishing "
            "returns); choose deployment alpha from this frontier, not by convention"
        ),
    }

    if req.include_isotonic and gw.calibration:
        from gateway.modules.m3_conformal.isotonic import IsotonicCalibrator

        scores = [c.nonconformity for c in gw.calibration]
        failures = [not c.cheap_success for c in gw.calibration]
        iso = IsotonicCalibrator().fit(scores, failures)
        ece = iso.ece(scores, failures)
        curve = iso.calibration_curve(scores, failures)
        # groupwise isotonic ECE when Mondrian strata present
        groups = sorted({c.group for c in gw.calibration})
        group_ece: dict[str, float] = {}
        for g in groups:
            sub = [(c.nonconformity, not c.cheap_success) for c in gw.calibration if c.group == g]
            if len(sub) >= 2:
                gs = [s for s, _ in sub]
                gf = [f for _, f in sub]
                group_ece[g] = IsotonicCalibrator().fit(gs, gf).ece(gs, gf)
        out["isotonic"] = {
            "fitted": iso.fitted,
            "n": len(scores),
            "ece": round(ece, 6),
            "group_ece": {k: round(v, 6) for k, v in group_ece.items()},
            "calibration_curve": curve,
            "predict_examples": {
                str(s): round(iso.predict(s), 4)
                for s in (0.1, 0.3, 0.5, 0.7, 0.9)
            },
        }
    return out


@app.post("/v1/calibration/ingest")
async def calibration_ingest(req: CalibrationIngestRequest) -> dict:
    from gateway.modules.m3_conformal.calibration_store import append_many
    from gateway.schemas import CalibSample

    s = get_settings()
    path = s.data_dir / "calibration.jsonl"
    parsed: list[CalibSample] = []
    for row in req.samples:
        try:
            parsed.append(CalibSample.model_validate(row))
        except Exception as e:
            raise ValueError(f"invalid sample {row}: {e}") from e
    with _calibration_lock:
        append_many(path, parsed)
        gw = gateway()
        from gateway.service import load_calibration

        gw.calibration = load_calibration(s.data_dir)
        gw.calibrator.calibrate(gw.calibration)
        # lineage for audit
        try:
            meta_path = s.data_dir / "calibration.meta.json"
            bench_n = sum(1 for c in gw.calibration if str(c.id).startswith("bench-"))
            pad_n = sum(1 for c in gw.calibration if str(c.id).startswith("pad-"))
            meta = {
                "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "n_total": len(gw.calibration),
                "bench_n": bench_n,
                "pad_n": pad_n,
                "alpha": gw.calibrator.alpha,
                "delta": gw.calibrator.delta,
                "threshold": gw.calibrator.threshold,
                "risk_hat": gw.calibrator.risk_hat,
                "risk_bound": gw.calibrator.risk_bound,
            }
            meta_path.write_text(_json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass
        return {"ingested": len(parsed), "n_total": len(gw.calibration), "threshold": gw.calibrator.threshold}


@app.get("/v1/receipt/{identifier}", response_model=ReceiptResponse)
@app.get("/receipt/{identifier}", response_model=ReceiptResponse)
async def receipt_endpoint(identifier: str) -> ReceiptResponse:
    db = get_log_db()
    r = db.get_receipt(identifier)
    if not r:
        raise ValueError(f"Receipt not found for '{identifier}'")
    return ReceiptResponse(
        id=r["id"],
        task_id=r["task_id"] or f"cmg-{r['id']}",
        ts=r["ts"],
        user_id=r["user_id"],
        original_tokens=r["original_tokens"],
        compressed_tokens=r["compressed_tokens"],
        model_routed=r["model_routed"],
        tier=r["tier"],
        difficulty_score=r["difficulty_score"],
        estimated_cost_savings=r["estimated_cost_savings"],
        compressed_prompt=r["compressed_prompt"],
        was_correct=r["was_correct"],
    )


@app.post("/v1/feedback")
async def feedback_endpoint(req: FeedbackRequest) -> dict:
    db = get_log_db()
    ok = db.record_feedback(req.task_id, req.was_correct)
    receipt = db.get_receipt(req.task_id)
    recalibrated = False
    if receipt and receipt.get("difficulty_score") is not None:
        from gateway.modules.m3_conformal.calibration_store import append_sample

        s = get_settings()
        path = s.data_dir / "calibration.jsonl"
        with _calibration_lock:
            sample_id = f"fb-{req.task_id}"
            append_sample(
                path, sample_id, float(receipt["difficulty_score"]), bool(req.was_correct)
            )
            gw = gateway()
            from gateway.service import load_calibration

            gw.calibration = load_calibration(s.data_dir)
            gw.calibrator.calibrate(gw.calibration)
            recalibrated = True
    return {
        "ok": ok,
        "task_id": req.task_id,
        "was_correct": req.was_correct,
        "recalibrated": recalibrated,
    }


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    import hmac as _hmac

    s = get_settings()
    expected = s.telegram_webhook_secret or (s.telegram_token[-8:] if s.telegram_token else "")
    header_secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    provided = header_secret or secret
    if not expected or not _hmac.compare_digest(provided, expected):
        return JSONResponse(status_code=403, content={"error": "invalid webhook secret"})
    if not s.telegram_token:
        return JSONResponse(status_code=503, content={"error": "telegram not configured"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid JSON"})
    msg = body.get("message") or body.get("edited_message") or {}
    text = (msg.get("text") or "").strip()
    from_user = msg.get("from") or {}
    chat = msg.get("chat") or {}
    user_id = str(from_user.get("id") or chat.get("id") or "unknown")
    chat_id = chat.get("id")
    if not text or not chat_id:
        return {"ok": True}
    if text.startswith("/start"):
        reply_text = (
            "namaste! apna sawal bhejo — Hinglish me bhi chalega.\n\n"
            "🔒 Transparency & Privacy: Queries are routed via Code-Mixed Gateway. "
            "Every response includes an audit receipt with tokens and cost savings. "
            "Type /receipt <task_id> to inspect any receipt."
        )
    elif text.startswith("/receipt"):
        parts = text.split()
        if len(parts) > 1:
            rec_id = parts[1]
            db = get_log_db()
            r = db.get_receipt(rec_id)
            if r:
                reply_text = (
                    f"🧾 Receipt {r['task_id'] or r['id']}:\n"
                    f"• Tier: {r['tier']} ({r['model_routed']})\n"
                    f"• Tokens: {r['original_tokens']} → {r['compressed_tokens']}\n"
                    f"• Savings: ${r['estimated_cost_savings']:.5f}\n"
                    f"• Difficulty: {r['difficulty_score']:.3f}\n"
                    f"• Feedback: {'Correct' if r['was_correct'] is True else 'Failed' if r['was_correct'] is False else 'None yet'}"
                )
            else:
                reply_text = f"Receipt '{rec_id}' not found."
        else:
            reply_text = "Please provide receipt ID: /receipt <id>"
    else:
        try:
            gw = gateway()
            from gateway.schemas import ChatCompletionRequest, ChatMessage

            req = ChatCompletionRequest(
                model="cascade",
                messages=[ChatMessage(role="user", content=text)],
                user=f"tg:{user_id}",
            )
            resp = await gw.handle(req)
            reply_text = resp.choices[0].message.content if resp.choices else ""
            if resp.id:
                reply_text += f"\n\n🧾 Receipt: /receipt {resp.id}"
        except Exception as exc:
            reply_text = f"sorry, gateway error: {exc}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{s.telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text},
            )
    except Exception:
        pass
    return {"ok": True}


@app.get("/telegram/webhook/{secret}")
async def telegram_webhook_info(secret: str):
    import hmac as _hmac

    s = get_settings()
    expected = s.telegram_webhook_secret or (s.telegram_token[-8:] if s.telegram_token else "")
    # Do not oracle secret via timing — constant-time but do not reveal
    ok = bool(expected and _hmac.compare_digest(secret, expected)) if expected else False
    return {"configured": bool(s.telegram_token), "secret_ok": ok}


@app.get("/v1/diagnostics/upstream")
async def diagnostics_upstream() -> dict:
    import time as _t

    s = get_settings()
    results: dict = {}
    for tier, cfg in [("cheap", s.cheap), ("premium", s.premium), ("local", s.local)]:
        start = _t.time()
        ok = False
        err: str | None = None
        try:
            import httpx as _httpx

            # cheap probe: try GET on base_url with short timeout; many providers return 404 but that's reachable
            async with _httpx.AsyncClient(timeout=3.0) as client:
                # try a GET on base_url/models or just base_url
                url = cfg.base_url.rstrip("/") + "/models"
                resp = await client.get(url, headers={"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {})
                ok = resp.status_code < 500
        except Exception as e:
            err = str(e)[:200]
        elapsed = round((_t.time() - start) * 1000, 1)
        results[tier] = {
            "model": cfg.model,
            "base_url": cfg.base_url,
            "reachable": ok,
            "latency_ms": elapsed,
            "error": err,
        }
    results["note"] = (
        "Ollama local expected at http://localhost:11434/v1 — "
        "run `ollama serve` and `ollama pull qwen3:0.6b` if not reachable."
    )
    return results


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get("/research", response_class=HTMLResponse)
async def research_page() -> HTMLResponse:
    """Real-data results page (reads /v1/research/summary)."""
    from gateway.modules.m8_dashboard import dashboard as _dash

    return HTMLResponse(Path(_dash.__file__).with_name("research.html").read_text(encoding="utf-8"))


def run() -> None:
    uvicorn.run("gateway.modules.m5_gateway.main:app", host="127.0.0.1", port=8000)