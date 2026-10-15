# ruff: noqa: E501
"""Minimal MCP server exposing the Code-Mixed Gateway tools over stdio.

Implements MCP 2024-11-05 JSON-RPC over stdio with tools:
- healthz
- compress
- chat
- reasoning_budget
- compare_budgets
- tokenizer_report
- dashboard_stats

Run: python -m gateway.mcp
Requires: pip install mcp (when MCP is needed). Falls back to plain stdio echo if mcp not installed.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

try:
    from mcp.server import Server  # type: ignore
    from mcp.types import TextContent, Tool  # type: ignore
    HAS_MCP = True
except Exception:
    HAS_MCP = False


def _gateway():
    from gateway.config import get_settings
    from gateway.service import Gateway
    return Gateway(get_settings())


async def _handle_tool(name: str, args: dict[str, Any]) -> str:
    gw = _gateway()
    if name == "healthz":
        from gateway.config import get_settings
        s = get_settings()
        return json.dumps({"status": "ok", "dry_run": s.dry_run, "calibration_n": len(gw.calibration), "threshold": gw.calibrator.threshold}, indent=2)
    if name == "compress":
        text = args.get("text", "")
        method = args.get("method", "auto")
        if method == "heuristic":
            r = gw.compressor.compress_heuristic(text)
        elif method == "crf":
            r = gw.compressor.compress_crf(text)
        elif method == "distilled":
            r = gw.compressor.compress_distilled(text)
        else:
            r = await gw.compressor.compress(text)
        return json.dumps(r.model_dump(), indent=2, ensure_ascii=False)
    if name == "chat":
        from gateway.schemas import ChatCompletionRequest, ChatMessage
        text = args.get("text", "")
        req = ChatCompletionRequest(model="cascade", messages=[ChatMessage(role="user", content=text)])
        resp = await gw.handle(req)
        return json.dumps(resp.model_dump(), indent=2, ensure_ascii=False)
    if name == "reasoning_budget":
        text = args.get("text", "")
        est = gw.budget_estimator.estimate(text)
        gloss = gw.budget_comparator.gloss_for(text)
        out: dict[str, Any] = est.model_dump()
        if gloss:
            out["english_gloss"] = gloss
            out["english_budget"] = gw.budget_estimator.estimate(gloss).reasoning_tokens
            out["delta"] = gw.budget_comparator.delta(text, gloss)
        return json.dumps(out, indent=2, ensure_ascii=False)
    if name == "compare_budgets":
        hi = args.get("hinglish", "")
        en = args.get("english", "")
        return json.dumps(gw.budget_comparator.compare(hi, en), indent=2, ensure_ascii=False)
    if name == "tokenizer_report":
        from gateway.config import get_settings
        from gateway.modules.m1_pipeline.pipeline import iter_jsonl
        from gateway.modules.m1_pipeline.tokenizer_bench import TokenizerBench
        s = get_settings()
        records = iter_jsonl(s.data_dir / "seed_hinglish.jsonl")
        bench = TokenizerBench()
        return json.dumps({"n": len(records), "inflation": bench.inflation(records) if records else {}}, indent=2)
    if name == "tokenizer_encode":
        text = args.get("text", "")
        tokenizer = args.get("tokenizer", "gpt4o_cl100k")
        from gateway.modules.m1_pipeline.tokenizer_bench import DEFAULT_TOKENIZERS
        from gateway.pricing import PREMIUM_PER_1K_USD
        from gateway.tokenizer import TokenCounter
        fn = DEFAULT_TOKENIZERS.get(tokenizer) or DEFAULT_TOKENIZERS.get("whitespace")  # type: ignore
        n = max(1, fn(text)) if text.strip() else 0  # type: ignore
        counter = TokenCounter()
        return json.dumps({"text": text, "tokenizer": tokenizer, "tokens": n, "chars": len(text), "tokens_per_char": round(n / max(1, len(text)), 6), "backend": counter.backend, "cost_premium_usd": round(n * PREMIUM_PER_1K_USD / 1000, 8)}, indent=2, ensure_ascii=False)
    if name == "code_mix_interpolate":
        text = args.get("text", "")
        steps = int(args.get("steps", 5))
        from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
        from gateway.modules.m12_novel.gloss import HINGLISH_TO_EN, to_english_gloss
        from gateway.tokenizer import TokenCounter
        tokens = text.split()
        hing_pos = [i for i, t in enumerate(tokens) if t.lower().strip(",.!?;:\"'()[]{}") in HINGLISH_TO_EN and HINGLISH_TO_EN[t.lower().strip(",.!?;:\"'()[]{}")] != ""]
        n_hing = len(hing_pos) or 1
        variants = []
        counter = TokenCounter()
        for s_idx in range(max(2, min(7, steps))):
            level = s_idx / (max(2, min(7, steps)) - 1)
            if level >= 0.99:
                interp = to_english_gloss(text)
            elif level <= 0.01:
                interp = text
            else:
                n_replace = int(round(level * n_hing))
                rep = set(hing_pos[:n_replace])
                out = []
                for idx, tok in enumerate(tokens):
                    if idx in rep:
                        low = tok.lower().strip(",.!?;:\"'()[]{}")
                        eng = HINGLISH_TO_EN.get(low, tok)
                        if eng == "":
                            continue
                        out.append(eng)
                    else:
                        out.append(tok)
                interp = " ".join(out)
            variants.append({"level": round(level, 3), "text": interp, "code_mix_ratio": code_mix_ratio(interp), "tokens": counter.count(interp)})
        return json.dumps({"original": text, "variants": variants}, indent=2, ensure_ascii=False)
    if name == "novel_report":
        from gateway.config import get_settings
        from gateway.modules.m12_novel.analysis import build_novel_report
        s = get_settings()
        return json.dumps(build_novel_report(s.data_dir), indent=2, ensure_ascii=False)
    if name == "dashboard_stats":
        from gateway.config import get_settings
        from gateway.modules.m6_telegram.db import LogDB
        from gateway.modules.m8_dashboard.dashboard import dashboard_stats
        db = LogDB(get_settings().pilot_db)
        stats = dashboard_stats(db)
        db.close()
        return json.dumps(stats.model_dump(), indent=2)
    return json.dumps({"error": f"unknown tool {name}"})


if HAS_MCP:
    server = Server("code-mixed-gateway")

    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:  # type: ignore
        return [
            Tool(name="healthz", description="Gateway health + dry_run flag", inputSchema={"type": "object", "properties": {}}),
            Tool(name="compress", description="Compress Hinglish text (heuristic/crf/distilled/adaptive/auto)", inputSchema={"type": "object", "properties": {"text": {"type": "string"}, "method": {"type": "string", "enum": ["heuristic", "crf", "distilled", "adaptive", "auto"]}}, "required": ["text"]}),
            Tool(name="chat", description="Run a prompt through the full gateway (compress+route)", inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
            Tool(name="reasoning_budget", description="Estimate reasoning budget for a Hinglish query", inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
            Tool(name="compare_budgets", description="Compare Hinglish vs English reasoning budgets", inputSchema={"type": "object", "properties": {"hinglish": {"type": "string"}, "english": {"type": "string"}}, "required": ["hinglish", "english"]}),
            Tool(name="tokenizer_report", description="Tokenizer inflation report vs gpt4o baseline", inputSchema={"type": "object", "properties": {}}),
            Tool(name="tokenizer_encode", description="Live token encode (gpt4o/whitespace/char4_proxy) with chips & cost", inputSchema={"type": "object", "properties": {"text": {"type": "string"}, "tokenizer": {"type": "string", "enum": ["gpt4o_cl100k", "whitespace", "char4_proxy"]}}, "required": ["text"]}),
            Tool(name="code_mix_interpolate", description="Interpolate Hinglish→English slider variants (5 levels) for code-switch visualizer", inputSchema={"type": "object", "properties": {"text": {"type": "string"}, "steps": {"type": "integer", "minimum": 2, "maximum": 7}}, "required": ["text"]}),
            Tool(name="novel_report", description="Full Hinglish novel report: adaptive vs fixed, tokenizer tax, reasoning delta, conformal bounds", inputSchema={"type": "object", "properties": {}}),
            Tool(name="dashboard_stats", description="Live pilot dashboard stats", inputSchema={"type": "object", "properties": {}}),
        ]

    @server.call_tool()  # type: ignore
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:  # type: ignore
        text = await _handle_tool(name, arguments or {})
        return [TextContent(type="text", text=text)]

    async def _run() -> None:
        from mcp.server.stdio import stdio_server  # type: ignore
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    def main() -> None:
        asyncio.run(_run())

else:
    # Fallback stdio JSON-RPC echo (so `python -m gateway.mcp` does not crash when mcp not installed)
    def main() -> None:
        sys.stderr.write("[gateway.mcp] mcp package not installed — running fallback stdio echo. Install with: pip install mcp\n")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}}) + "\n")
                sys.stdout.flush()
                continue
            # Minimal MCP initialize/tools echo
            method = req.get("method", "")
            rid = req.get("id")
            if method == "initialize":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "code-mixed-gateway", "version": "0.2.0"}}}
            elif method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
                    {"name": "healthz", "description": "Gateway health"},
                    {"name": "compress", "description": "Compress text"},
                    {"name": "chat", "description": "Chat via gateway"},
                ]}}
            elif method == "tools/call":
                name = req.get("params", {}).get("name", "")
                args = req.get("params", {}).get("arguments", {})
                try:
                    text = asyncio.run(_handle_tool(name, args))
                except Exception as e:
                    text = json.dumps({"error": str(e)})
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": rid, "result": {}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
