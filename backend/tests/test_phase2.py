"""Phase 2 tests: CRC fidelity control, isotonic calibration, LTT/Mondrian, alpha sweep."""

import pytest

from gateway.modules.m3_conformal.conformal import (
    ConformalCalibrator,
    _binomial_ub,
    _fixed_sequence_threshold,
    _knee_detection,
)
from gateway.modules.m3_conformal.crc import ConformalFidelityControl, CRCSample, _monotone_envelope
from gateway.modules.m3_conformal.isotonic import IsotonicCalibrator, pava_isotonic
from gateway.schemas import CalibSample

# --- CRC fidelity control ----------------------------------------------------
#
# Inputs are per-prompt loss curves: losses[i][j] = loss of prompt i at
# lambdas[j]; n is the number of prompts. The CRC fixed point carries a
# B/(n+1) term, so certifying alpha=0.05 with B=1 needs n >= 20 prompts; small
# calibration sets correctly stay uncertified.

LAMS = [0.2, 0.4, 0.6, 0.8]


def test_crc_fixed_point_selects_max_aggressive_within_budget():
    # monotone loss family, 100 prompts with the same curve
    curves = [[0.01, 0.02, 0.03, 0.06]] * 100
    res = ConformalFidelityControl(alpha=0.05).calibrate(LAMS, curves)
    # bound(0.6) = (100/101)*0.03 + 1/101 = 0.0396 <= 0.05; bound(0.8) = 0.069
    assert res.lam_hat == pytest.approx(0.6)
    assert res.n == 100
    assert res.feasible is True
    assert res.monotone is True
    assert res.risk_bound <= 0.05 + 1e-9


def test_crc_n_counts_prompts_not_pairs():
    # 25 prompts x 4 lambdas = 100 pairs, but n must be 25: B/(n+1) = 0.0385
    curves = [[0.01, 0.02, 0.03, 0.06]] * 25
    res = ConformalFidelityControl(alpha=0.05).calibrate(LAMS, curves)
    assert res.n == 25
    # bound(0.2) = (25/26)*0.01 + 1/26 = 0.048; bound(0.4) = 0.058 -> only 0.2
    assert res.lam_hat == pytest.approx(0.2)
    flat = [
        CRCSample(lam=lam, loss=v, prompt_id=f"p{i}") for i in range(25) for lam, v in zip(LAMS, curves[i], strict=True)
    ]
    assert ConformalFidelityControl(alpha=0.05).calibrate_samples(flat).n == 25


def test_crc_infeasible_when_even_mildest_level_exceeds():
    res = ConformalFidelityControl(alpha=0.05).calibrate([0.1], [[0.4]] * 30)
    assert res.feasible is False
    assert res.lam_hat == 0.0


def test_crc_small_n_refuses_to_certify():
    # 4 prompts -> B/(n+1) = 0.2 floor > alpha -> correctly uncertified
    res = ConformalFidelityControl(alpha=0.05).calibrate(LAMS, [[0.0, 0.0, 0.0, 0.0]] * 4)
    assert res.feasible is False
    assert res.lam_hat == 0.0


def test_crc_loss_bound_parameter():
    curves = [[0.02, 0.04]] * 100
    lo = ConformalFidelityControl(alpha=0.05, loss_bound=1.0).calibrate([0.3, 0.6], curves)
    hi = ConformalFidelityControl(alpha=0.05, loss_bound=3.0).calibrate([0.3, 0.6], curves)
    # B=1: bound(0.6) = (100/101)*0.04 + 1/101 = 0.0495 -> certified
    assert lo.lam_hat == pytest.approx(0.6)
    # B=3: bound(0.3) = (100/101)*0.02 + 3/101 = 0.0495, bound(0.6) = 0.0693
    assert hi.lam_hat == pytest.approx(0.3)
    assert hi.per_lambda[0]["risk_bound"] == pytest.approx(100 / 101 * 0.02 + 3 / 101, abs=1e-6)
    with pytest.raises(ValueError):
        ConformalFidelityControl(alpha=0.05, loss_bound=0.5).calibrate([0.3], [[0.9]])


def test_crc_averages_risk_over_prompts():
    samples = [CRCSample(lam=0.5, loss=loss) for loss in (0.01, 0.03, 0.05)] * 10
    res = ConformalFidelityControl(alpha=0.10).calibrate_samples(samples)
    assert res.n == 30
    assert res.lam_hat == pytest.approx(0.5)
    assert res.risk_hat == pytest.approx(0.03, abs=1e-6)


def test_crc_uses_per_prompt_monotone_envelope():
    # every prompt is non-monotone: 0.4 is worse than 0.6
    res = ConformalFidelityControl(alpha=0.05).calibrate([0.2, 0.4, 0.6], [[0.01, 0.20, 0.02]] * 100)
    assert res.monotone is False
    # envelope (0.01, 0.20, 0.20): only 0.2 passes
    assert res.lam_hat == pytest.approx(0.2)


def test_crc_envelope_is_stricter_than_averaged_isotonic():
    # Averaged risks (0, 0.1, 0.1) are already monotone, so PAVA on averages
    # would certify 0.6 at alpha=0.15. The per-prompt envelope is (0, 0.1, 0.2)
    # because half the prompts already failed at 0.4.
    curves = [[0.0, 0.2, 0.0]] * 50 + [[0.0, 0.0, 0.2]] * 50
    res = ConformalFidelityControl(alpha=0.15).calibrate([0.2, 0.4, 0.6], curves)
    assert [p["risk_hat"] for p in res.per_lambda] == pytest.approx([0.0, 0.1, 0.2])
    assert res.lam_hat == pytest.approx(0.4)


def test_crc_from_rewards_helper():
    rewards = [0.95, 0.90, 0.70]
    lambdas = [0.3, 0.5, 0.7] * 25
    ids = [f"p{i}" for i in range(25) for _ in range(3)]
    res = ConformalFidelityControl(alpha=0.10).calibrate_from_rewards(lambdas, rewards * 25, prompt_ids=ids)
    # 25 prompts with losses 0.05, 0.10, 0.30: bound(0.3) = (25/26)*0.05 + 1/26 = 0.0865,
    # bound(0.5) = 0.1346 > 0.10
    assert res.n == 25
    assert res.lam_hat == pytest.approx(0.3)
    assert res.risk_hat == pytest.approx(0.05, abs=1e-6)
    # without prompt ids, pairs at several lambdas cannot be turned into curves
    with pytest.raises(ValueError, match="prompt_id"):
        ConformalFidelityControl(alpha=0.10).calibrate_from_rewards(lambdas, rewards * 25)
    # single-lambda legacy call (m12 analysis): each pair is one prompt
    single = ConformalFidelityControl(alpha=0.10).calibrate_from_rewards([0.4] * 50, [0.98] * 50)
    assert single.n == 50
    assert single.lam_hat == pytest.approx(0.4)


def test_crc_empty_samples():
    res = ConformalFidelityControl(alpha=0.05).calibrate([], [])
    assert res.lam_hat == 0.0
    assert res.n == 0
    assert ConformalFidelityControl(alpha=0.05).calibrate_samples([]).n == 0


def test_monotone_envelope_running_max():
    assert _monotone_envelope([0.1, 0.2, 0.3]) == [0.1, 0.2, 0.3]
    assert _monotone_envelope([0.3, 0.1, 0.2, 0.5, 0.4]) == [0.3, 0.3, 0.3, 0.5, 0.5]


# --- isotonic calibration ------------------------------------------------------


def test_isotonic_fit_and_predict():
    scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    failures = [False, False, False, True, False, True, True, True]
    iso = IsotonicCalibrator().fit(scores, failures)
    assert iso.fitted
    assert iso.predict(0.05) == pytest.approx(iso.predict(0.1))
    assert iso.predict(0.95) >= iso.predict(0.15)  # non-decreasing
    mid = iso.predict(0.45)
    assert 0.0 <= mid <= 1.0


def test_isotonic_ece_zero_on_perfectly_calibrated():
    # scores exactly equal realized failure rates in two strata
    scores = [0.2] * 10 + [0.8] * 10
    failures = [False] * 8 + [True] * 2 + [True] * 8 + [False] * 2
    iso = IsotonicCalibrator().fit(scores, failures)
    ece = iso.ece(scores, failures)
    assert ece <= 0.05


def test_pava_isotonic_ties_averaged():
    xs, ys = pava_isotonic([0.5, 0.5, 0.5, 1.0], [0.0, 1.0, 0.0, 1.0])
    assert len(xs) == 2
    assert xs[0] == 0.5 and xs[1] == 1.0
    assert ys[0] == pytest.approx(1.0 / 3.0)


# --- fixed-sequence LTT --------------------------------------------------------


def test_fixed_sequence_dominates_hoeffding():
    import random

    rng = random.Random(11)
    scores = [rng.uniform(0, 1) for _ in range(2000)]
    failures = [s > 0.70 for s in scores]  # cheap tier fails on the hardest 30%
    cheap_success = [not f for f in failures]
    alpha, delta = 0.10, 0.05
    tau_fs, risk_fs, bound_fs = _fixed_sequence_threshold(scores, failures, alpha, delta)
    cal_h = ConformalCalibrator.from_pairs(scores, cheap_success, alpha=alpha, delta=delta, method="hoeffding")
    assert cal_h.threshold > 0.70  # Hoeffding certifies something non-trivial here
    assert tau_fs > cal_h.threshold, "fixed-sequence must dominate Hoeffding"
    assert risk_fs <= bound_fs <= alpha + 1e-9
    assert cal_h.risk_bound <= alpha + 1e-9


def test_fixed_sequence_matches_calibrator_and_cp_bound():
    import random

    rng = random.Random(3)
    scores = [rng.uniform(0, 1) for _ in range(500)]
    ok = [not (s > 0.6 and rng.random() < 0.5) for s in scores]
    cal = ConformalCalibrator(alpha=0.10, delta=0.05).fit_pairs(scores, ok)
    k = sum(1 for s, o in zip(scores, ok, strict=True) if s < cal.threshold and not o)
    assert cal.risk_bound == pytest.approx(_binomial_ub(500, k, 0.05))
    assert cal.risk_bound <= 0.10 + 1e-9
    # the next grid point must have been rejected (CP bound > alpha)
    nxt = min(t for t in cal.grid if t > cal.threshold)
    k2 = sum(1 for s, o in zip(scores, ok, strict=True) if s < nxt and not o)
    assert _binomial_ub(500, k2, 0.05) > 0.10


def test_binomial_ub_exact_clopper_pearson():
    # n=100, k=0, delta=0.05 -> 1 - 0.05**(1/100) ~= 0.0295
    ub = _binomial_ub(100, 0.0, 0.05)
    assert ub == pytest.approx(1 - 0.05 ** (1 / 100), rel=1e-6)
    ub2 = _binomial_ub(100, 50.0, 0.05)
    assert 0.5 <= ub2 <= 1.0
    # larger n tightens the zero-count bound
    ub3 = _binomial_ub(10_000, 0.0, 0.05)
    assert ub3 < 0.02
    assert _binomial_ub(10, 10, 0.05) == 1.0


def test_binomial_ub_without_scipy_matches():
    from gateway.modules.m3_conformal.conformal import _cp_upper_bisect

    pytest.importorskip("scipy")
    cases = [(100, 0, 0.05), (400, 30, 0.01), (57, 9, 0.2)]
    with_scipy = [_binomial_ub(n, k, d) for n, k, d in cases]
    without = [_cp_upper_bisect(n, k, d) for n, k, d in cases]  # the no-scipy fallback
    assert without == pytest.approx(with_scipy, rel=1e-6)


def test_route_premium_monotone():
    scores = [0.1, 0.3, 0.5, 0.7, 0.9]
    labels = [True, True, True, False, False]
    cal = ConformalCalibrator(alpha=0.10).fit_pairs(scores, labels)
    t = cal.threshold
    assert not cal.route_premium(t - 0.01)
    assert cal.route_premium(t + 0.01)


def test_sweep_reports_the_bound_the_method_certifies():
    import random

    rng = random.Random(5)
    scores = [rng.uniform(0, 1) for _ in range(400)]
    ok = [not (s > 0.5 and rng.random() < 0.4) for s in scores]
    fs = ConformalCalibrator(alpha=0.10, delta=0.05).fit_pairs(scores, ok)
    pts = fs.sweep()
    sel = [p for p in pts if p["is_selected"]]
    assert len(sel) == 1
    assert sel[0]["risk_bound"] == pytest.approx(fs.risk_bound, abs=1e-6)  # Clopper-Pearson, not Hoeffding
    for p in pts:
        k = round(p["risk_hat"] * 400)
        assert p["risk_bound"] == pytest.approx(_binomial_ub(400, k, 0.05), abs=1e-6)
    # feasible = accepted prefix of the fixed sequence, ending at the selection
    feas = [p["tau"] for p in pts if p["feasible"]]
    assert max(feas) == sel[0]["tau"]

    h = ConformalCalibrator(alpha=0.10, delta=0.05, method="hoeffding").fit_pairs(scores, ok)
    hp = [p for p in h.sweep() if p["is_selected"]][0]
    assert hp["risk_bound"] == pytest.approx(h.risk_bound, abs=1e-6)


def test_custom_threshold_grid():
    import random

    from gateway.modules.m3_conformal.conformal import quantile_grid

    rng = random.Random(8)
    tune = [rng.uniform(0, 1) for _ in range(300)]  # separate split
    scores = [rng.uniform(0, 1) for _ in range(1000)]
    ok = [not (s > 0.7 and rng.random() < 0.5) for s in scores]
    grid = quantile_grid(tune, n_points=50)
    assert grid[0] == 0.0 and grid[-1] == 1.0
    cal = ConformalCalibrator(alpha=0.10, delta=0.05, grid=grid).fit_pairs(scores, ok)
    assert cal.threshold in grid
    assert len(cal.sweep()) == len(grid)
    assert len(ConformalCalibrator(alpha=0.10).fit_pairs(scores, ok).sweep()) == 201  # default unchanged


# --- Mondrian -------------------------------------------------------------------


def _mondrian_samples():
    # low-mix group: cheap tier is safe up to high difficulty
    # high-mix group: cheap tier fails earlier
    rows = []
    for i in range(40):
        rows.append(CalibSample(id=f"lo-{i}", nonconformity=i / 40, cheap_success=True, group="low"))
    for i in range(40):
        ok = i < 10
        rows.append(CalibSample(id=f"hi-{i}", nonconformity=i / 40, cheap_success=ok, group="high"))
    return rows


def test_mondrian_per_group_thresholds():
    rows = _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    assert cal.is_mondrian
    assert set(cal.group_thresholds) == {"low", "high"}
    # low group should tolerate a higher tau (cheap safe) than high group
    assert cal.group_thresholds["low"] >= cal.group_thresholds["high"]
    # per-group routing respects its own threshold
    assert cal.route_premium(0.5, group="low") is False or cal.group_thresholds["low"] <= 0.5
    assert cal.route_premium(0.5, group="high") is True  # tau_high <= 0.25-ish


def test_mondrian_sweep_by_group():
    rows = _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    sw = cal.sweep_by_group()
    assert set(sw) == {"low", "high"}
    assert len(sw["low"]) == 201 and len(sw["high"]) == 201
    for g, pts in sw.items():
        sel = [p for p in pts if p["is_selected"]]
        assert len(sel) == 1
        # each group's sweep reports its Clopper-Pearson bound at delta / G
        assert sel[0]["risk_bound"] == pytest.approx(cal.group_risk_bounds[g], abs=1e-6)


def test_single_group_is_not_mondrian():
    rows = [CalibSample(id=f"a{i}", nonconformity=i / 10, cheap_success=i < 5) for i in range(10)]
    cal = ConformalCalibrator(alpha=0.2).calibrate(rows)
    assert not cal.is_mondrian
    assert cal.group_thresholds == {}


# --- alpha sweep / knee -----------------------------------------------------------


def test_alpha_sweep_rows_and_knee():
    rows = _mondrian_samples() + _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    sweep = cal.alpha_sweep(alphas=[0.05, 0.10, 0.20, 0.40])
    assert len(sweep["rows"]) == 4
    # simultaneous validity: Bonferroni over 2 Mondrian groups x 4 alphas
    assert sweep["groups"] == ["high", "low"]
    assert sweep["n_tests"] == 8
    assert sweep["delta_used"] == pytest.approx(0.10 / 8)
    for r in sweep["rows"]:
        assert 0 <= r["threshold"] <= 1.0
        assert 0 <= r["risk_hat"] <= 1.0
        assert r["risk_bound"] >= r["risk_hat"] - 1e-9
        assert set(r["group_thresholds"]) == {"low", "high"}
        assert r["threshold"] == min(r["group_thresholds"].values())
    # monotone: larger alpha permits weakly more cheap routing
    shares = [r["cheap_share"] for r in sweep["rows"]]
    assert all(a <= b + 1e-9 for a, b in zip(shares, shares[1:], strict=False))
    # at generous alpha=0.40 the low group must be routable cheap
    assert sweep["rows"][-1]["cheap_share"] > 0.0
    assert sweep["rows"][-1]["group_thresholds"]["low"] == 1.0
    assert "knee" in sweep
    assert cal.alpha_sweep(alphas=[0.05, 0.10, 0.20, 0.40], include_knee=False)["knee"] is None


def test_alpha_sweep_cells_match_direct_fit_at_corrected_delta():
    import random

    rng = random.Random(21)
    scores = [rng.uniform(0, 1) for _ in range(800)]
    ok = [not (s > 0.5 and rng.random() < 0.4) for s in scores]
    cal = ConformalCalibrator(alpha=0.05, delta=0.05).fit_pairs(scores, ok)
    alphas = [0.02, 0.05, 0.10]
    sweep = cal.alpha_sweep(alphas=alphas)
    assert sweep["groups"] == ["all"]
    assert sweep["delta_used"] == pytest.approx(0.05 / 3)
    for a, row in zip(alphas, sweep["rows"], strict=True):
        direct = ConformalCalibrator(alpha=a, delta=0.05 / 3).fit_pairs(scores, ok)
        assert row["threshold"] == pytest.approx(round(direct.threshold, 4))
        assert row["risk_bound"] <= a + 1e-4
        assert "group_thresholds" not in row


def test_knee_detection_basic():
    # concave curve with knee at x=0.5
    xs = [0.0, 0.25, 0.5, 0.75, 1.0]
    ys = [0.0, 0.45, 0.7, 0.85, 1.0]
    knee = _knee_detection(xs, ys)
    assert knee is not None
    assert 0.25 <= knee <= 0.75


# --- endpoint ----------------------------------------------------------------------


def test_threshold_sweep2d_endpoint():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/threshold/sweep2d", json={})
        assert r.status_code == 200
        body = r.json()
        assert "rows" in body
        assert "knee_alpha" in body
        assert "isotonic" in body
        assert "current_alpha" in body
        for row in body["rows"]:
            assert {"alpha", "threshold", "risk_hat", "risk_bound", "cheap_share"} <= set(row)
        iso = body["isotonic"]
        assert "ece" in iso
        assert "calibration_curve" in iso


def test_threshold_sweep2d_custom_alphas():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/threshold/sweep2d", json={"alphas": [0.02, 0.08], "include_isotonic": False})
        assert r.status_code == 200
        body = r.json()
        assert [row["alpha"] for row in body["rows"]] == [0.02, 0.08]
        assert "isotonic" not in body
