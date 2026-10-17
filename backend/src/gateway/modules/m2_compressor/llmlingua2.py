from __future__ import annotations

import threading
from functools import lru_cache

#: Small multilingual LLMLingua-2 checkpoint (BERT-base, 110M params).
#: CPU-runnable, multilingual by construction (Appendix J of the paper), and
#: the right size for free-tier/Kaggle use. The xlm-roberta-large variant is
#: more faithful but 3x heavier — override via LLMLingua2Compressor(model_name=...).
DEFAULT_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"

# Upper bound for force-preserved markers per call (library default is 100).
MAX_FORCE_MARKERS = 90


def is_available() -> bool:
    """True when the `llmlingua` package is importable (pip install -e ".[compression]")."""
    try:
        import llmlingua  # noqa: F401

        return True
    except Exception:
        return False


class _CachedForward:
    """Memoise the token-classifier forward pass.

    LLMLingua-2's per-token keep probabilities depend only on the input ids,
    not on the keep-rate (the rate is a percentile threshold applied after).
    Compressing the same prompt at several rates therefore repeats an
    identical forward pass; this cache makes every rate after the first free.
    Small LRU keyed on (ids, mask) bytes, so memory stays bounded.
    """

    def __init__(self, model, size: int = 64) -> None:
        from collections import OrderedDict

        self._model = model
        self._cache: OrderedDict = OrderedDict()
        self._size = size
        self.hits = 0
        self.misses = 0

    def __call__(self, input_ids, attention_mask):
        key = (input_ids.cpu().numpy().tobytes(), attention_mask.cpu().numpy().tobytes(), tuple(input_ids.shape))
        out = self._cache.get(key)
        if out is not None:
            self._cache.move_to_end(key)
            self.hits += 1
            return out
        self.misses += 1
        out = self._model(input_ids=input_ids, attention_mask=attention_mask)
        self._cache[key] = out
        if len(self._cache) > self._size:
            self._cache.popitem(last=False)
        return out

    def __getattr__(self, name):  # .eval(), .to(), .config, ... pass through
        return getattr(self._model, name)


class LLMLingua2Compressor:
    """Trained token-classifier compressor with code-mix-safe guards.

    Two findings from live probing on Hinglish (CPU, bert-base-multilingual)
    are baked in here, not left as caller folklore:

    1. Raw output mangles protected spans (``user@example.com`` →
       ``user example com``). Callers must mask spans to ``[[PSi]]`` markers
       first and pass them as ``force_tokens`` — plain calls fail reinjection
       and would fall back to uncompressed text on every entity-bearing
       message.
    2. The default context-level filter silently *drops* whole segments from
       batched calls (4 in → 3 out, misaligned). It is a multi-doc RAG
       feature and is always disabled here; every batch call asserts
       output/input alignment and reports per-row failure instead of
       shifting rows.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._lock = threading.Lock()
        self._comp = None

    def _ensure(self):  # type: ignore[no-untyped-def]
        if self._comp is None:
            with self._lock:
                if self._comp is None:
                    from llmlingua import PromptCompressor

                    self._comp = PromptCompressor(
                        model_name=self.model_name,
                        use_llmlingua2=True,
                        device_map=self.device,
                    )
                    self._comp.model = _CachedForward(self._comp.model)
        return self._comp

    @property
    def loaded(self) -> bool:
        return self._comp is not None

    def compress_masked(
        self,
        masked_texts: list[str],
        markers_per_text: list[list[str]],
        rate: float = 0.5,
        extra_force: list[str] | None = None,
    ) -> list[str | None]:
        """Compress pre-masked texts. Returns compressed strings or None per row.

        ``None`` means "this row failed, caller should fall back" — never
        raises for model/inference problems, but raises ImportError when the
        `llmlingua` package itself is missing so callers can label the
        baseline `is_simulated` honestly.
        """
        if not is_available():
            raise ImportError("llmlingua not installed (pip install -e \".[compression]\")")
        rate = min(0.95, max(0.05, float(rate)))
        try:
            comp = self._ensure()
            # Union of markers across the batch; preservation is token-string
            # based so shared [[PSi]] names are safe across rows.
            force = sorted({m for markers in markers_per_text for m in markers} | set(extra_force or []))[:MAX_FORCE_MARKERS]
            out = comp.compress_prompt(
                masked_texts,
                rate=rate,
                force_tokens=force,
                force_reserve_digit=True,
                use_context_level_filter=False,
            )
            compressed_list = out.get("compressed_prompt_list") or []
            if len(compressed_list) != len(masked_texts):
                return [None] * len(masked_texts)
            return [c if isinstance(c, str) and c.strip() else None for c in compressed_list]
        except Exception:
            return [None] * len(masked_texts)


@lru_cache(maxsize=2)
def get_compressor(model_name: str = DEFAULT_MODEL) -> LLMLingua2Compressor:
    return LLMLingua2Compressor(model_name=model_name)
