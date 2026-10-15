"""Conformal Risk Control for compression fidelity (Phase 2, novel).

Replaces the hard-coded ``reward < 0.85`` failure constant with a learned,
statistically-guaranteed aggressiveness level. Following Angelopoulos et al.,
"Conformal Risk Control" (2208.02814).

Input: one *loss curve per calibration prompt*, ``L_i(lambda_j)`` for a fixed
grid of aggressiveness levels ``lambda_1 < ... < lambda_m`` (higher lambda =
more aggressive compression). CRC needs each L_i to be non-decreasing in
lambda; observed curves need not be, so each is replaced by its monotone
envelope

    L~_i(lambda) = max_{lambda' <= lambda} L_i(lambda')      (>= L_i, monotone)

and, with n = number of calibration *prompts* and B an upper bound on the loss,

    lambda_hat = max { lambda_j : (n / (n + 1)) * R_hat(lambda_j) + B / (n + 1) <= alpha },
    R_hat(lambda) = (1/n) * sum_i L~_i(lambda).

On an exchangeable test prompt this guarantees
``E[L_{n+1}(lambda_hat)] <= E[L~_{n+1}(lambda_hat)] <= alpha``. If no grid
level qualifies, ``lambda_hat = 0`` (no compression), which is assumed to be
lossless.

The loss must measure answer *quality* only (e.g. 1 - task score of the
answer produced from the compressed prompt, relative to the uncompressed
answer). ``1 - reward`` from ``m10_train/reward.py`` is NOT a valid CRC loss:
its 0.3-weighted "faithfulness" term is an LCS recall of the original prompt,
i.e. it penalises compression itself, so the "risk" grows with lambda even when
answers are unaffected and the certified level is not a quality guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class CRCSample:
    """Loss of one calibration prompt compressed at one aggressiveness level."""

    lam: float  # aggressiveness in [0, 1] (kept-ratio complement)
    loss: float  # quality loss in [0, B]
    prompt_id: str | None = None  # groups samples into per-prompt curves


@dataclass
class CRCResult:
    lam_hat: float
    alpha: float
    n: int  # number of calibration prompts
    risk_hat: float
    risk_bound: float
    feasible: bool
    monotone: bool  # True iff every observed per-prompt curve was already non-decreasing
    per_lambda: list[dict] = field(default_factory=list)
    loss_bound: float = 1.0


class ConformalFidelityControl:
    """Calibrate the compression aggressiveness lambda under an alpha budget.

    ``loss_bound`` is B, an a-priori upper bound on every loss value (1.0 for
    losses in [0, 1]); it enters the CRC correction B / (n + 1).
    """

    def __init__(self, alpha: float = 0.05, loss_bound: float = 1.0) -> None:
        if alpha <= 0.0:
            raise ValueError("alpha must be > 0")
        if loss_bound <= 0.0:
            raise ValueError("loss_bound must be > 0")
        self.alpha = alpha
        self.loss_bound = loss_bound

    def calibrate(self, lambdas: Sequence[float], losses: Sequence[Sequence[float]]) -> CRCResult:
        """``losses[i][j]`` = loss of calibration prompt i at aggressiveness ``lambdas[j]``."""
        B = self.loss_bound
        n = len(losses)
        if n == 0 or not lambdas:
            return CRCResult(0.0, self.alpha, 0, 0.0, self.alpha, False, True, loss_bound=B)
        if len(set(lambdas)) != len(lambdas):
            raise ValueError("lambdas must be distinct")
        order = sorted(range(len(lambdas)), key=lambda j: lambdas[j])
        lams = [float(lambdas[j]) for j in order]

        sums = [0.0] * len(lams)
        monotone = True
        for row in losses:
            if len(row) != len(lams):
                raise ValueError("every prompt needs one loss per lambda")
            curve = [float(row[j]) for j in order]
            if any(v > B + 1e-12 for v in curve):
                raise ValueError(f"loss exceeds loss_bound B={B}")
            env = _monotone_envelope(curve)
            if env != curve:
                monotone = False
            for j, v in enumerate(env):
                sums[j] += v
        risks = [s / n for s in sums]

        def _bound(r: float) -> float:
            return (n / (n + 1)) * r + B / (n + 1)

        lam_hat = 0.0
        risk_hat = 0.0
        selected = -1
        for j, r in enumerate(risks):
            if _bound(r) > self.alpha:
                break
            lam_hat, risk_hat, selected = lams[j], r, j
        feasible = selected >= 0
        bound_sel = _bound(risk_hat)

        per_lambda = [
            {
                "lambda": lam,
                "risk_hat": round(r, 6),
                "risk_bound": round(_bound(r), 6),
                "feasible": _bound(r) <= self.alpha,
                "is_selected": j == selected,
            }
            for j, (lam, r) in enumerate(zip(lams, risks, strict=True))
        ]
        return CRCResult(
            lam_hat=lam_hat,
            alpha=self.alpha,
            n=n,
            risk_hat=round(risk_hat, 6),
            risk_bound=round(bound_sel, 6),
            feasible=feasible,
            monotone=monotone,
            per_lambda=per_lambda,
            loss_bound=B,
        )

    def calibrate_samples(self, samples: Sequence[CRCSample]) -> CRCResult:
        """Adapter for flat ``(lambda, loss)`` records; ``prompt_id`` groups them into curves.

        Records without ``prompt_id`` are accepted only when they all share one
        lambda (each record is then its own prompt). n is always the number of
        prompts, never the number of (prompt, lambda) pairs.
        """
        if not samples:
            return self.calibrate([], [])
        lams = sorted({float(s.lam) for s in samples})
        if any(s.prompt_id is None for s in samples):
            if len(lams) > 1:
                raise ValueError(
                    "records at several lambdas need prompt_id: CRC's n counts prompts, "
                    "and each prompt must contribute a full loss curve"
                )
            return self.calibrate(lams, [[float(s.loss)] for s in samples])
        col = {lam: j for j, lam in enumerate(lams)}
        curves: dict[str, list[float | None]] = {}
        for s in samples:
            curve = curves.setdefault(s.prompt_id, [None] * len(lams))
            j = col[float(s.lam)]
            if curve[j] is not None:
                raise ValueError(f"duplicate loss for prompt {s.prompt_id!r} at lambda={s.lam}")
            curve[j] = float(s.loss)
        for pid, curve in curves.items():
            if any(v is None for v in curve):
                raise ValueError(f"prompt {pid!r} is missing losses at some lambdas")
        return self.calibrate(lams, list(curves.values()))  # type: ignore[arg-type]

    def calibrate_from_rewards(
        self,
        lambdas: list[float],
        rewards: list[float],
        prompt_ids: list[str] | None = None,
    ) -> CRCResult:
        """Legacy adapter: loss = 1 - reward, clipped to [0, B].

        Warning: with ``m10_train.reward.reward`` this loss is not quality-only
        (its faithfulness term penalises compression itself; see module
        docstring), so the result is not a fidelity guarantee. Prefer
        ``calibrate`` with a quality-only loss.
        """
        ids = prompt_ids if prompt_ids is not None else [None] * len(lambdas)
        samples = [
            CRCSample(lam=lam, loss=max(0.0, min(self.loss_bound, 1.0 - r)), prompt_id=pid)
            for lam, r, pid in zip(lambdas, rewards, ids, strict=True)
        ]
        return self.calibrate_samples(samples)


def _monotone_envelope(curve: list[float]) -> list[float]:
    """Running maximum: L~(lambda_j) = max_{j' <= j} L(lambda_j')."""
    out: list[float] = []
    m = float("-inf")
    for v in curve:
        m = max(m, v)
        out.append(m)
    return out
