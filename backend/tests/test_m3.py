import numpy as np

from gateway.modules.m3_conformal.conformal import ConformalCalibrator


def _synthetic(n, seed):
    rng = np.random.default_rng(seed)
    scores, labels = [], []
    for _ in range(n):
        fail = rng.random() < 0.3
        s = rng.uniform(0.35, 0.95) if fail else rng.uniform(0.05, 0.60)
        scores.append(float(s))
        labels.append(not fail)
    return scores, labels


def test_calibrate_empty_failures_routes_all_cheap():
    scores, _ = _synthetic(2000, seed=3)
    cal = ConformalCalibrator(alpha=0.10).fit_pairs(scores, [True] * len(scores))
    assert cal.threshold == 1.0
    assert not cal.route_premium(0.9)


def test_route_premium_is_monotone_in_score():
    scores, labels = _synthetic(2000, seed=5)
    cal = ConformalCalibrator(alpha=0.10).fit_pairs(scores, labels)
    assert 0.0 < cal.threshold < 1.0
    assert not cal.route_premium(0.0)
    assert cal.route_premium(1.0)


def test_empirical_error_rate_within_bound():
    scores, labels = _synthetic(6000, seed=7)
    cal = ConformalCalibrator(alpha=0.10).fit_pairs(scores[:2000], labels[:2000])
    val_s = scores[2000:]
    val_l = labels[2000:]
    errors = sum(1 for s, ok in zip(val_s, val_l, strict=True) if not cal.route_premium(s) and not ok)
    empirical = errors / len(val_s)
    assert empirical <= 0.10 + 0.02


def test_calibration_records_risk():
    scores, labels = _synthetic(2000, seed=9)
    cal = ConformalCalibrator(alpha=0.10).fit_pairs(scores, labels)
    assert cal.risk_hat <= cal.risk_bound <= 0.10 + 1e-9


def test_from_pairs_on_instance_refuses_instead_of_silently_resetting_alpha():
    import pytest

    scores, labels = _synthetic(200, seed=1)
    with pytest.raises(TypeError, match="fit_pairs"):
        ConformalCalibrator(alpha=0.10, method="hoeffding").from_pairs(scores, labels)
    with pytest.raises(TypeError):
        ConformalCalibrator.from_pairs(scores, labels)  # alpha/delta/method are required keywords
    cal = ConformalCalibrator.from_pairs(scores, labels, alpha=0.10, delta=0.05, method="hoeffding")
    assert (cal.alpha, cal.delta, cal.method) == (0.10, 0.05, "hoeffding")


def test_fit_pairs_uses_instance_settings():
    scores, labels = _synthetic(2000, seed=11)
    cal = ConformalCalibrator(alpha=0.10, delta=0.10, method="hoeffding").fit_pairs(scores, labels)
    ref = ConformalCalibrator.from_pairs(scores, labels, alpha=0.10, delta=0.10, method="hoeffding")
    assert cal.threshold == ref.threshold
    assert cal.risk_bound == ref.risk_bound
    assert cal.risk_bound <= 0.10 + 1e-9
