from __future__ import annotations

from gateway.lexicons import prune
from gateway.llm import BaseLLMClient
from gateway.modules.m2_compressor.prompts import compression_messages, rewrite_messages
from gateway.modules.m2_compressor.safety_span import mask, reinject
from gateway.modules.m10_train.reward import reward
from gateway.schemas import CompressResult, SafetySpan
from gateway.tokenizer import TokenCounter

#: Provisional acceptance bar for rewrite candidates (fidelity of the
#: rewrite against the reference). FINAL bar is fit to human_check.csv
#: before freezing — see DECISION_importance.json.
REWRITE_BAR = 0.6


class Compressor:
    """Hinglish prompt compressor (distilled → llmlingua2 → model → heuristic).

    Heuristic fast path is the canonical lexicon-based prune (gateway.lexicons):
    guarded filler/vocative removal with per-drop audit records. LLMLingua-2 is
    the trained baseline: a distilled token-classifier (BERT-base multilingual,
    CPU-runnable); protected spans are masked to [[PSi]] markers and
    force-preserved because raw classifier output mangles entities
    (user@example.com → "user example com"). Optional local-model path
    (Ollama) and distilled-checkpoint path are unchanged.
    """

    def __init__(
        self,
        counter: TokenCounter,
        client: BaseLLMClient | None = None,
        use_model: bool = False,
        distilled_map: dict[str, str] | None = None,
        use_llmlingua2: bool = False,
        llmlingua2_rate: float = 0.5,
        use_crf: bool = False,
        crf_model_path=None,
        tfidf_path=None,
    ) -> None:
        self.counter = counter
        self.client = client
        self.use_model = use_model and client is not None
        self.distilled_map = distilled_map or {}
        self.use_llmlingua2 = use_llmlingua2
        self.llmlingua2_rate = llmlingua2_rate
        self.use_crf = use_crf
        self._linguistic = None
        if use_crf:
            try:
                from gateway.modules.m2_compressor.linguistic import LinguisticCompressor

                self._linguistic = LinguisticCompressor(
                    counter,
                    crf_model_path=crf_model_path,
                    tfidf_path=tfidf_path,
                )
            except Exception:
                self._linguistic = None

    def _result(
        self,
        original: str,
        compressed: str,
        spans: list[SafetySpan],
        method: str,
        drops: list | None = None,
    ) -> CompressResult:
        tok_orig = self.counter.count(original)
        tok_comp = self.counter.count(compressed)
        tok_comp = max(1, tok_comp)
        return CompressResult(
            original=original,
            compressed=compressed,
            spans=spans,
            drops=drops or [],
            token_original=tok_orig,
            token_compressed=tok_comp,
            ratio=round(tok_comp / max(1, tok_orig), 6),
            method=method,
        )

    def compress_distilled(self, text: str) -> CompressResult:
        if text in self.distilled_map:
            masked, spans = mask(text)
            distilled = self.distilled_map[text]
            if not spans:
                return self._result(text, distilled, spans, "distilled")
            if "[[PS" in distilled:
                final, ok = reinject(distilled, spans)
                if not ok:
                    final = text
                return self._result(text, final, spans, "distilled")
            # distilled checkpoint stores raw text (no markers) — ensure
            # protected spans are still present verbatim, otherwise fall back
            # to heuristic which preserves spans via masking.
            if all(sp.text in distilled for sp in spans):
                return self._result(text, distilled, spans, "distilled")
            return self.compress_heuristic(text)
        return self.compress_heuristic(text)

    def compress_heuristic(self, text: str) -> CompressResult:
        masked, spans = mask(text)
        compressed_masked, drops = prune(masked)
        final, ok = reinject(compressed_masked, spans)
        if not ok or not final.strip():
            final = text
        return self._result(text, final, spans, "heuristic", drops)

    def compress_llmlingua2(self, text: str, rate: float | None = None) -> CompressResult:
        """Trained-baseline compression. Falls back to heuristic (honestly
        labelled) when the library/weights are unavailable or a row fails."""
        from gateway.modules.m2_compressor.llmlingua2 import get_compressor, is_available

        rate = self.llmlingua2_rate if rate is None else rate
        # Explicit call: always try the real classifier when installed.
        # (The auto path below separately respects use_llmlingua2.)
        if not is_available():
            return self.compress_heuristic(text)
        masked, spans = mask(text)
        markers = [f"[[PS{i}]]" for i in range(len(spans))]
        try:
            got = get_compressor().compress_masked([masked], [markers], rate=rate)[0]
        except ImportError:
            return self.compress_heuristic(text)
        if got is None:
            return self.compress_heuristic(text)
        final, ok = reinject(got, spans)
        if not ok:
            return self.compress_heuristic(text)
        return self._result(text, final, spans, "llmlingua2")

    def compress_crf(self, text: str) -> CompressResult:
        """CRF linguistic compression. Falls back to heuristic (honestly
        labelled) when the model file/weights are unavailable."""
        if self._linguistic is None:
            return self.compress_heuristic(text)
        try:
            res = self._linguistic.compress(text)
        except Exception:
            return self.compress_heuristic(text)
        if res.ratio >= 1.0 and res.compressed == text:
            # No compression achieved (or fail-closed) -> heuristic label.
            heur = self.compress_heuristic(text)
            return heur
        return res

    def select_best(
        self, original: str, candidates: list[str], reference: str, bar: float = REWRITE_BAR,
        brevity_lambda: float = 0.3,
    ) -> tuple[str, float, bool]:
        """Pick max (reward - lambda*ratio) candidate; accepted iff reward >= bar.

        Joint score forces real compression: a longer rewrite must earn its
        tokens with proportionally higher fidelity. Returns (text, reward,
        accepted). Rejected selections fall back down the chain.
        """
        scored = []
        tok_o = max(1, self.counter.count(original))
        for c in candidates:
            if not c or not c.strip():
                continue
            r = reward(original, c, reference, c)
            ratio = max(1, self.counter.count(c)) / tok_o
            scored.append((c, r, r - brevity_lambda * ratio))
        if not scored:
            return original, 0.0, False
        best, best_r, _ = max(scored, key=lambda kv: kv[2])
        return best, round(best_r, 6), bool(best_r >= bar)

    async def compress_rewrite(
        self, text: str, protected: list[str] | None = None, temperature: float = 0.3
    ) -> CompressResult:
        """Single LLM rewrite with Judge-A protected-term constraints."""
        masked, spans = mask(text)
        if self.client is None:
            return self.compress_heuristic(text)
        result = await self.client.chat(rewrite_messages(masked, protected), temperature=temperature)
        raw = result.content.strip()
        # Clean any surrounding markdown block or quotes that LLMs might add
        if raw.startswith("```") and raw.endswith("```"):
            lines = raw.splitlines()
            if len(lines) >= 3:
                raw = "\n".join(lines[1:-1]).strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1].strip()
        final, ok = reinject(raw, spans)
        if not ok:
            final = text
        return self._result(text, final, spans, "rewrite")

    async def compress_model(self, text: str) -> CompressResult:
        masked, spans = mask(text)
        if self.client is None:
            compressed_masked, drops = prune(masked)
            method = "heuristic"
        else:
            result = await self.client.chat(compression_messages(masked), temperature=0.0)
            raw = result.content.strip()
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                raw = raw[1:-1].strip()
            final, ok = reinject(raw, spans)
            method = "model"
            if not ok:
                final = text
            return self._result(text, final, spans, method)
        final, ok = reinject(compressed_masked, spans)
        if not ok:
            final = text
        return self._result(text, final, spans, method, drops)

    async def compress(self, text: str) -> CompressResult:
        if not text or not text.strip():
            return self._result(text, text, [], "heuristic")

        # 1. Distilled pre-computed checkpoint
        if text in self.distilled_map:
            return self.compress_distilled(text)

        # Skip model rewrite for minimal 1-2 token messages (e.g. 'hello', 'namaste')
        tokens = text.split()
        if len(tokens) <= 2:
            if self.use_crf and self._linguistic is not None:
                res = self.compress_crf(text)
                if res.method == "crf" and res.ratio < 1.0:
                    return res
            return self.compress_heuristic(text)

        # 2. Intelligent model rewrite path (runs when live / not dry_run)
        if self.use_model:
            try:
                from gateway.modules.m2_compressor.safety_span import detect_spans as _spans

                prot = [sp.text for sp in _spans(text)]
                prot += [
                    t
                    for t in text.split()
                    if t.lower().strip(",.!?")
                    in {
                        "nahi",
                        "nahin",
                        "nhi",
                        "nai",
                        "ni",
                        "not",
                        "never",
                        "n't",
                        "mat",
                        "kya",
                        "kahan",
                        "kidhar",
                        "kaise",
                        "kab",
                        "kyun",
                        "kyu",
                        "kaun",
                    }
                ]
                rw = await self.compress_rewrite(text, prot)
                if rw.method == "rewrite" and rw.ratio < 1.0:
                    return rw
            except Exception:
                pass
            try:
                m = await self.compress_model(text)
                if m.method == "model" and m.ratio < 1.0:
                    return m
            except Exception:
                pass

        # 3. CRF linguistic compressor (offline / dry-run / fallback)
        if self.use_crf and self._linguistic is not None:
            res = self.compress_crf(text)
            if res.method == "crf" and res.ratio < 1.0:
                return res

        # 4. LLMLingua-2 trained baseline
        if self.use_llmlingua2:
            res = self.compress_llmlingua2(text)
            if res.method == "llmlingua2":
                return res

        # 5. Heuristic fallback
        return self.compress_heuristic(text)
