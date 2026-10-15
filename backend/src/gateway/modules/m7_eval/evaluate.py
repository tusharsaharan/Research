from __future__ import annotations

import json
import math
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from gateway.pricing import (
    CHEAP_OUT_PER_1K_USD,
    CHEAP_PER_1K_USD,
    FX_INR_PER_USD,
    PREMIUM_OUT_PER_1K_USD,
    PREMIUM_PER_1K_USD,
    estimate_cost_usd,
)
from gateway.schemas import EvalRecord, EvalResult, EvalSummary
from gateway.tokenizer import TokenCounter


def _load_metric_functions():
    try:
        from sacrebleu.metrics import BLEU

        metric = BLEU()

        def bleu(hyp: str, ref: str) -> float:
            return metric.sentence_score(hyp, [ref]).score / 100.0

    except Exception:

        def bleu(hyp: str, ref: str) -> float:
            return _fallback_bleu(hyp, ref)

    try:
        from rouge_score import rouge_scorer

        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)

        def rouge_l(hyp: str, ref: str) -> float:
            return scorer.score(ref, hyp)["rougeL"].fmeasure

    except Exception:

        def rouge_l(hyp: str, ref: str) -> float:
            return _fallback_rouge_l(hyp, ref)

    return bleu, rouge_l


def _fallback_bleu(hyp: str, ref: str) -> float:
    hyp_t = hyp.split()
    ref_t = ref.split()
    if not hyp_t or not ref_t:
        return 0.0
    ref_c = Counter(ref_t)
    overlap = sum(min(hyp_t.count(t), ref_c[t]) for t in set(hyp_t))
    precision = overlap / len(hyp_t)
    bp = 1.0 if len(hyp_t) >= len(ref_t) else math.exp(1 - len(ref_t) / len(hyp_t))
    return bp * precision


def _fallback_rouge_l(hyp: str, ref: str) -> float:
    if not hyp or not ref:
        return 0.0
    lcs = SequenceMatcher(None, ref, hyp).find_longest_match(0, len(ref), 0, len(hyp)).size
    r = lcs / len(ref)
    p = lcs / len(hyp)
    return 2 * r * p / (r + p) if (r + p) > 0 else 0.0


def _norm(text: str) -> str:
    return " ".join(text.split()).strip().lower()


#: Honesty label surfaced on every eval response. These scores are LEXICAL
#: proxies (overlap/fuzzy match), not task accuracy. P0-grade accuracy requires
#: structured scoring or blinded judgement (see experiments/token_study/).
METRIC_NOTE = (
    "task_success/bleu/rouge_l/reward are lexical similarity proxies, not task "
    "accuracy; semantic_sim is a meaning proxy. Do not present them as measured "
    "task correctness."
)


def _lexical_task_proxy(hyp: str, ref: str) -> float:
    """String-similarity diagnostic in [0, 1]. NOT task accuracy (plan §6)."""
    if _norm(hyp) == _norm(ref):
        return 1.0
    if not hyp or not ref:
        return 0.0
    return max(0.0, SequenceMatcher(None, _norm(ref), _norm(hyp)).ratio())


class HinglishEvaluator:
    """Scores compression quality + downstream task success + cost in USD/INR."""

    def __init__(
        self,
        counter: TokenCounter | None = None,
        premium_per_1k: float = PREMIUM_PER_1K_USD,
        cheap_per_1k: float = CHEAP_PER_1K_USD,
        fx_rate_inr_per_usd: float = FX_INR_PER_USD,
        embedder=None,
    ) -> None:
        self.counter = counter or TokenCounter()
        self.premium_per_1k = premium_per_1k
        self.cheap_per_1k = cheap_per_1k
        self.premium_out_per_1k = PREMIUM_OUT_PER_1K_USD
        self.cheap_out_per_1k = CHEAP_OUT_PER_1K_USD
        self.fx_rate_inr_per_usd = fx_rate_inr_per_usd
        self.bleu, self.rouge_l = _load_metric_functions()
        self._embedder = embedder  # lazy: resolved on first score() so eval never breaks offline

    def _sim(self, a: str, b: str) -> float:
        try:
            if self._embedder is None:
                from gateway.modules.m12_semantic.embeddings import get_embedder

                self._embedder = get_embedder()
            return self._embedder.similarity(a, b)
        except Exception:
            return 0.0

    def score(self, rec: EvalRecord) -> EvalResult:
        tok_orig = self.counter.count(rec.original)
        tok_comp = self.counter.count(rec.compressed)
        savings_ratio = max(0.0, 1.0 - tok_comp / max(1, tok_orig))

        baseline = estimate_cost_usd(
            tok_orig, self.counter.count(rec.reference_answer), self.premium_per_1k, self.premium_out_per_1k
        )
        actual = estimate_cost_usd(
            tok_comp, self.counter.count(rec.predicted_answer), self.cheap_per_1k, self.cheap_out_per_1k
        )
        savings = max(0.0, baseline - actual)

        span_preserved = all(p in rec.compressed for p in rec.protected)

        return EvalResult(
            id=rec.id,
            token_savings_ratio=round(savings_ratio, 6),
            bleu=round(self.bleu(rec.predicted_answer, rec.reference_answer), 6),
            rouge_l=round(self.rouge_l(rec.predicted_answer, rec.reference_answer), 6),
            task_success=round(_lexical_task_proxy(rec.predicted_answer, rec.reference_answer), 6),
            semantic_sim=self._sim(rec.predicted_answer, rec.reference_answer),
            prompt_sim=self._sim(rec.original, rec.compressed),
            span_preserved=span_preserved,
            cost_usd=round(actual, 8),
            baseline_cost_usd=round(baseline, 8),
            savings_usd=round(savings, 8),
            cost_inr=round(actual * self.fx_rate_inr_per_usd, 4),
        )

    def evaluate(
        self, records: list[EvalRecord], pricing_date: str = "2026-08-28"
    ) -> EvalSummary:
        results = [self.score(r) for r in records]
        n = len(results) or 1
        summary = EvalSummary(
            n=len(results),
            mean_token_savings_ratio=sum(r.token_savings_ratio for r in results) / n,
            mean_bleu=sum(r.bleu for r in results) / n,
            mean_rouge_l=sum(r.rouge_l for r in results) / n,
            mean_task_success=sum(r.task_success for r in results) / n,
            mean_semantic_sim=sum(r.semantic_sim for r in results) / n,
            mean_prompt_sim=sum(r.prompt_sim for r in results) / n,
            span_preserved_rate=sum(1 for r in results if r.span_preserved) / n,
            total_cost_usd=sum(r.cost_usd for r in results),
            total_baseline_usd=sum(r.baseline_cost_usd for r in results),
            total_savings_usd=sum(r.savings_usd for r in results),
            total_cost_inr=sum(r.cost_inr for r in results),
            total_savings_inr=sum(r.savings_usd * self.fx_rate_inr_per_usd for r in results),
            pricing_date=pricing_date,
            metric_note=METRIC_NOTE,
            results=results,
        )
        return summary


def load_records(path: Path) -> list[EvalRecord]:
    return [
        EvalRecord.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def save_report(summary: EvalSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")


def _real_llmlingua2_batch(originals: list[str], rate: float) -> list[str] | None:
    """Compress rows with the trained LLMLingua-2 classifier (batched, one model call).

    Returns compressed strings aligned with `originals`, or None when the
    library is not installed (caller labels the point `is_simulated`).
    Per-row failures fall back to the heuristic individually — never shifts rows.
    """
    try:
        from gateway.modules.m2_compressor.llmlingua2 import get_compressor, is_available
        from gateway.modules.m2_compressor.safety_span import mask, reinject
    except Exception:
        return None
    if not is_available():
        return None
    try:
        masked_list: list[str] = []
        spans_list: list = []
        for t in originals:
            m, s = mask(t)
            masked_list.append(m)
            spans_list.append(s)
        markers = [[f"[[PS{i}]]" for i in range(len(s))] for s in spans_list]
        got = get_compressor().compress_masked(masked_list, markers, rate=rate)
    except Exception:
        return None
    from gateway.modules.m2_compressor.compressor import _heuristic_compress

    out: list[str] = []
    for orig, m, spans, c in zip(originals, masked_list, spans_list, got):
        if c is None:
            out.append(_heuristic_compress(m))
            continue
        final, ok = reinject(c, spans)
        out.append(final if ok else _heuristic_compress(m))
    return out


def curve_points(
    benchmark: Path,
    checkpoint: Path | None = None,
) -> list[dict]:
    """Return Fig-1 ratio-vs-accuracy points for heuristic / distilled / llmlingua2.

    Heuristic and distilled are measured; llmlingua2 is measured with the
    trained classifier whenever the `compression` extra is installed, else a
    honestly-labelled simulated baseline (heuristic − 0.06) so the chart
    always has three methods.
    """
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m10_train.distill import load_mapping
    from gateway.modules.m10_train.reward import reward as reward_fn

    records = [
        json.loads(line)
        for line in benchmark.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counter = TokenCounter()
    distilled_map = load_mapping(checkpoint or Path("data/checkpoints/distilled.json"))
    comp = Compressor(counter, distilled_map=distilled_map)

    originals = [rec.get("original", "") for rec in records]
    llm2_batch = _real_llmlingua2_batch(originals, rate=0.5)

    methods: list[tuple[str, callable]] = [
        ("heuristic", lambda t: comp.compress_heuristic(t).compressed),
        ("distilled", lambda t: comp.compress_distilled(t).compressed),
        ("llmlingua2", lambda t: comp.compress_heuristic(t).compressed),
    ]
    points: list[dict] = []
    for method, fn in methods:
        ratios: list[float] = []
        rewards: list[float] = []
        comped_list = llm2_batch if (method == "llmlingua2" and llm2_batch is not None) else None
        for idx, rec in enumerate(records):
            orig = rec.get("original", "")
            ref = rec.get("reference_answer", "")
            pred = rec.get("predicted_answer", ref)
            if comped_list is not None:
                comped = comped_list[idx]
            else:
                comped = fn(orig)
            if method == "llmlingua2" and comped_list is None:
                r = max(0.0, reward_fn(orig, comped, ref, pred) - 0.06)
            else:
                r = reward_fn(orig, comped, ref, pred)
            tok_o = counter.count(orig)
            tok_c = counter.count(comped)
            ratio = tok_c / max(1, tok_o)
            ratios.append(ratio)
            rewards.append(r)
        avg_ratio = sum(ratios) / max(1, len(ratios))
        avg_reward = sum(rewards) / max(1, len(rewards))
        points.append(
            {
                "method": method,
                "ratio": round(avg_ratio, 4),
                "kept_pct": round(avg_ratio * 100, 1),
                "accuracy": round(avg_reward, 4),
                "is_simulated": method == "llmlingua2" and comped_list is None,
            }
        )
    return points


def curve_sweep(
    benchmark: Path,
    checkpoint: Path | None = None,
    targets: tuple[float, ...] = (0.3, 0.5, 0.7, 0.9),
) -> list[dict]:
    """Sweep of target kept-ratio vs accuracy per method (for Fig-1 curve)."""
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.modules.m10_train.distill import load_mapping
    from gateway.modules.m10_train.reward import reward as reward_fn

    records = [
        json.loads(line)
        for line in benchmark.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counter = TokenCounter()
    distilled_map = load_mapping(checkpoint or Path("data/checkpoints/distilled.json"))
    comp = Compressor(counter, distilled_map=distilled_map)
    originals = [rec.get("original", "") for rec in records]

    def _to_target(text: str, target: float, base_fn):
        base = base_fn(text)
        tok_o = max(1, counter.count(text))
        tok_c = counter.count(base)
        ratio = tok_c / tok_o
        if ratio <= target + 0.02:
            return base
        # truncate to target ratio (word-level, preserves order)
        words = base.split()
        keep = max(1, int(len(words) * (target / max(ratio, 0.01))))
        keep = min(len(words), keep)
        return " ".join(words[:keep]) if keep < len(words) else base

    points: list[dict] = []
    for target in targets:
        # LLMLingua-2 supports native ratio control: rate IS the kept
        # fraction, so no truncation hack — one batched model call per target.
        llm2_batch = _real_llmlingua2_batch(originals, rate=target)
        for method, fn in [
            ("heuristic", lambda t: comp.compress_heuristic(t).compressed),
            ("distilled", lambda t: comp.compress_distilled(t).compressed),
            ("llmlingua2", lambda t: comp.compress_heuristic(t).compressed),
        ]:
            ratios: list[float] = []
            rewards: list[float] = []
            comped_list = llm2_batch if (method == "llmlingua2" and llm2_batch is not None) else None
            for idx, rec in enumerate(records):
                orig = rec.get("original", "")
                ref = rec.get("reference_answer", "")
                pred = rec.get("predicted_answer", ref)
                if comped_list is not None:
                    comped = comped_list[idx]
                else:
                    comped = _to_target(orig, target, fn)
                r = reward_fn(orig, comped, ref, pred)
                if method == "llmlingua2" and comped_list is None:
                    r = max(0.0, r - 0.06)
                tok_o = counter.count(orig)
                tok_c = counter.count(comped)
                ratios.append(tok_c / max(1, tok_o))
                rewards.append(r)
            points.append(
                {
                    "method": method,
                    "target": target,
                    "ratio": round(sum(ratios) / max(1, len(ratios)), 4),
                    "accuracy": round(sum(rewards) / max(1, len(rewards)), 4),
                    "is_simulated": method == "llmlingua2" and comped_list is None,
                }
            )
    return points


def run_evaluation(benchmark: Path, report: Path, fx_rate: float = 83.5) -> EvalSummary:
    evaluator = HinglishEvaluator(fx_rate_inr_per_usd=fx_rate)
    summary = evaluator.evaluate(load_records(benchmark))
    save_report(summary, report)
    return summary