"""Known-truth validity simulations for the m3_conformal risk-control guarantees.

Router model (per group g): score s ~ U(0, 1) and the cheap tier fails
independently of s with probability c_g, so the cheap-tier risk of the rule
"route cheap iff s < tau" is known in closed form, R_g(tau) = c_g * tau.
A calibration run *violates* when a certified threshold has true risk above its
alpha. LTT promises P(violation) <= delta; over N_SEEDS independent
calibration sets we check the violation frequency against
delta + 3 * sqrt(delta (1 - delta) / N) (binomial tolerance).

Compression model (CRC): prompt i has a latent tolerance t_i ~ U(0, 1) and
loss L_i(lambda) = 1{t_i < lambda}, so E[L(lambda)] = lambda. CRC promises
E[L_test(lambda_hat)] <= alpha; we average the exact conditional test risk
R(lambda_hat) over seeds and allow 3 standard errors.

Each check also reproduces the procedure this module used before the fix and
shows that it breaks the same bound. Set VALIDITY_SIM_SEEDS to change the
number of seeds (the guarantee checks require >= 2000 to be meaningful).
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

from gateway.modules.m3_conformal.conformal import (
    ConformalCalibrator,
    _fixed_sequence_threshold,
    _select_threshold,
)
from gateway.modules.m3_conformal.crc import ConformalFidelityControl
from gateway.schemas import CalibSample

N_SEEDS = int(os.environ.get("VALIDITY_SIM_SEEDS", "2000"))
ALPHAS = [0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15]  # default alpha_sweep grid

# Rates are collected here so `pytest -s` prints a before/after table.
RATES: dict[str, float] = {}


def _binom_tol(p: float, n: int) -> float:
    return 3.0 * math.sqrt(p * (1.0 - p) / n)


def _draw(rng: np.random.Generator, n: int, c: float) -> tuple[list[float], list[bool]]:
    return rng.random(n).tolist(), (rng.random(n) < c).tolist()


def _samples(scores: list[float], failures: list[bool], group: str) -> list[CalibSample]:
    # model_construct skips pydantic validation (inputs are in range by construction) — keeps 2,000 seeds fast
    return [
        CalibSample.model_construct(id="", nonconformity=s, cheap_success=not f, synthetic=True, group=group)
        for s, f in zip(scores, failures, strict=True)
    ]


def _report(name: str, rate: float, bound: float) -> None:
    RATES[name] = rate
    print(f"\n[validity-sim] {name}: {rate:.4f} (bound {bound:.4f}, seeds={N_SEEDS})")


# ----------------------------------------------------------------------------- (i) fixed sequence


@pytest.mark.parametrize("method", ["fixed_sequence", "hoeffding"])
def test_single_group_violation_rate_le_delta(method):
    n, c, alpha, delta = 1000, 0.3, 0.10, 0.10
    viol = 0
    for seed in range(N_SEEDS):
        scores, failures = _draw(np.random.default_rng(seed), n, c)
        tau, _, _ = _select_threshold(method, scores, failures, alpha, delta, None)
        viol += c * tau > alpha
    rate = viol / N_SEEDS
    _report(f"(i) {method} P(R(tau_hat) > alpha)", rate, delta)
    assert rate <= delta + _binom_tol(delta, N_SEEDS)


# ----------------------------------------------------------------------------- (ii) Mondrian


def test_mondrian_bonferroni_violation_rate_le_delta():
    """Any-group violation through ConformalCalibrator.calibrate (delta / G per group)."""
    sizes, risks, alpha, delta = (200, 400, 600), (0.15, 0.30, 0.60), 0.10, 0.10
    viol_bonf = viol_naive = 0
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(seed)
        rows: list[CalibSample] = []
        naive_bad = False
        for g, (n, c) in enumerate(zip(sizes, risks, strict=True)):
            scores, failures = _draw(rng, n, c)
            rows += _samples(scores, failures, f"g{g}")
            tau_naive, _, _ = _fixed_sequence_threshold(scores, failures, alpha, delta)  # no correction
            naive_bad |= c * tau_naive > alpha
        cal = ConformalCalibrator(alpha=alpha, delta=delta).calibrate(rows)
        assert cal.is_mondrian
        viol_bonf += any(risks[int(g[1:])] * t > alpha for g, t in cal.group_thresholds.items())
        viol_naive += naive_bad
    rate, naive = viol_bonf / N_SEEDS, viol_naive / N_SEEDS
    tol = _binom_tol(delta, N_SEEDS)
    _report("(ii) Mondrian, each group at delta (no correction)", naive, delta)
    _report("(ii) Mondrian, Bonferroni delta/G", rate, delta)
    assert rate <= delta + tol
    # why the correction is needed: per-group full delta breaks the simultaneous guarantee
    assert naive > delta + tol


# ----------------------------------------------------------------------------- (iii) post-hoc alpha


def test_posthoc_alpha_selection_grid_correction():
    """A worst-case post-hoc selector picks any alpha whose threshold violates.

    Simultaneous validity over the alpha grid is exactly what makes *every*
    post-hoc choice (knee, eyeballing, cost target) valid, so we check
    P(exists (g, alpha): R_g(tau_{g, alpha}) > alpha) <= delta.
    """
    n, risks, delta = 1600, (0.30, 0.60), 0.05
    viol_new = viol_old = 0
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(seed)
        groups = rng.integers(0, 2, n)
        scores = rng.random(n)
        failures = rng.random(n) < np.asarray(risks)[groups]
        rows = [
            CalibSample.model_construct(id="", nonconformity=s, cheap_success=not f, synthetic=True, group=f"g{g}")
            for s, f, g in zip(scores.tolist(), failures.tolist(), groups.tolist(), strict=True)
        ]
        cal = ConformalCalibrator(alpha=0.05, delta=delta).calibrate(rows)
        sweep = cal.alpha_sweep(ALPHAS, include_knee=False)
        assert sweep["delta_used"] == pytest.approx(delta / (2 * len(ALPHAS)))
        viol_new += any(
            risks[int(g[1:])] * t > row["alpha"] for row in sweep["rows"] for g, t in row["group_thresholds"].items()
        )

        # legacy alpha_sweep: pooled samples, every alpha refit at the full delta
        pooled_risk = float(np.mean(np.asarray(risks)[groups]))  # R_pooled(tau) = mean_i c_{g_i} * tau
        s_list, f_list = scores.tolist(), failures.tolist()
        viol_old += any(pooled_risk * _fixed_sequence_threshold(s_list, f_list, a, delta)[0] > a for a in ALPHAS)
    new, old = viol_new / N_SEEDS, viol_old / N_SEEDS
    tol = _binom_tol(delta, N_SEEDS)
    _report("(iii) post-hoc alpha, legacy per-alpha full delta", old, delta)
    _report("(iii) post-hoc alpha, delta/(G*A) grid correction", new, delta)
    assert new <= delta + tol
    assert old > delta + tol


# ----------------------------------------------------------------------------- CRC


def _legacy_crc_lam_hat(lams: list[float], curves: list[list[float]], alpha: float) -> float:
    """The pre-fix crc.py: pooled (prompt, lambda) pairs, n = #pairs, PAVA on averaged risks."""
    n = len(curves) * len(lams)  # the bug: counts pairs, not prompts
    risks = [sum(c[j] for c in curves) / len(curves) for j in range(len(lams))]
    blocks = [[r, 1] for r in risks]  # PAVA (no-op on monotone input)
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            w = blocks[i][1] + blocks[i + 1][1]
            blocks[i : i + 2] = [[(blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / w, w]]
            i = max(0, i - 1)
        else:
            i += 1
    risks = [v for v, w in blocks for _ in range(w)]
    lam_hat = 0.0
    for lam, r in zip(lams, risks, strict=True):
        if (n / (n + 1)) * r + 1 / (n + 1) <= alpha:
            lam_hat = lam
        else:
            break
    return lam_hat


def test_crc_expected_loss_le_alpha_and_legacy_n_inflation():
    n_prompts, alpha = 20, 0.12
    lams = [j / 200 for j in range(201)]
    lam_arr = np.asarray(lams)
    new_risk, old_risk = [], []
    crc = ConformalFidelityControl(alpha=alpha)
    for seed in range(N_SEEDS):
        t = np.random.default_rng(seed).random(n_prompts)
        curves = (t[:, None] < lam_arr[None, :]).astype(float).tolist()
        new_risk.append(crc.calibrate(lams, curves).lam_hat)  # E[L(lambda)] = lambda
        old_risk.append(_legacy_crc_lam_hat(lams, curves, alpha))
    new_mean, old_mean = float(np.mean(new_risk)), float(np.mean(old_risk))
    se_new = float(np.std(new_risk)) / math.sqrt(N_SEEDS)
    se_old = float(np.std(old_risk)) / math.sqrt(N_SEEDS)
    _report("CRC E[test loss], legacy n = #(prompt, lambda) pairs", old_mean, alpha)
    _report("CRC E[test loss], n = #prompts", new_mean, alpha)
    assert new_mean <= alpha + 3 * se_new
    assert old_mean > alpha + 3 * se_old


def test_crc_envelope_valid_on_non_monotone_curves():
    """Raw per-prompt curves with a transient blip: L_i = 1{t_i < lam} or 1{u_i <= lam < u_i + w}.

    E[L(lambda)] = lambda + (1 - lambda) * min(w, lambda) in closed form; the
    envelope makes the curves monotone and CRC must still give E[L(lambda_hat)] <= alpha.
    """
    n_prompts, alpha, w = 40, 0.15, 0.05
    lams = [j / 200 for j in range(201)]
    lam_arr = np.asarray(lams)
    crc = ConformalFidelityControl(alpha=alpha)
    risks = []
    any_non_monotone = False
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(seed)
        t, u = rng.random(n_prompts), rng.random(n_prompts)
        raw = (t[:, None] < lam_arr) | ((u[:, None] <= lam_arr) & (lam_arr < u[:, None] + w))
        res = crc.calibrate(lams, raw.astype(float).tolist())
        any_non_monotone |= not res.monotone
        lh = res.lam_hat
        risks.append(lh + (1 - lh) * min(w, lh))
    assert any_non_monotone
    mean = float(np.mean(risks))
    _report("CRC E[test loss], non-monotone curves + envelope", mean, alpha)
    assert mean <= alpha + 3 * float(np.std(risks)) / math.sqrt(N_SEEDS)
