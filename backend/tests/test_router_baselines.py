import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
import certify  # noqa: E402
from router_baselines import thr_crc, thr_empirical  # noqa: E402


def _case():
    s = np.arange(10) / 10
    u = np.zeros(10)
    u[8] = 1  # one bad item at a high score
    return s, u, s.copy()


def test_empirical_and_crc():
    s, u, grid = _case()
    assert thr_empirical(s, u, grid, 0.05) == 0.7
    assert thr_empirical(s, u, grid, 0.10) == 0.9
    assert thr_crc(s, u, grid, 0.10) == 0.7  # (10R+1)/11 <= .1 needs R = 0
    assert thr_crc(s, u, grid, 0.20) == 0.9
    assert thr_crc(s, np.ones(10), grid, 0.05) == -np.inf


def test_ltt_more_conservative_than_empirical():
    s = np.linspace(0, 1, 200)
    u = np.zeros(200)
    grid = np.unique(np.quantile(s, np.linspace(0, 1, 101)))
    lam = certify.fixed_sequence(s, u, grid, 0.10, 0.10)
    assert lam > -np.inf
    assert thr_empirical(s, u, grid, 0.10) == grid[-1]
    assert lam <= thr_empirical(s, u, grid, 0.10)
