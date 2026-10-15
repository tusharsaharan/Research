from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable, Iterable, Sequence
from functools import lru_cache

from gateway.schemas import CalibSample

_GRID_SIZE = 200

_DEFAULT_GROUPS = ("all",)

_DEFAULT_ALPHAS = (0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15)


# ---------------------------------------------------------------------- grids


def default_grid(size: int = _GRID_SIZE) -> list[float]:
    """The historical fixed grid: ``size + 1`` equally spaced taus on [0, 1]."""
    return [i / size for i in range(size + 1)]


def quantile_grid(scores: Iterable[float], n_points: int = _GRID_SIZE) -> list[float]:
    """Threshold grid from empirical quantiles of *held-out* scores.

    Build it from a split that is disjoint from the calibration set (e.g. a
    tuning split); a grid built from the calibration scores themselves is
    data-dependent and voids the fixed-sequence / Bonferroni accounting.
    ``0.0`` (all-premium, riskless start of the sequence) and ``1.0`` are
    always included.
    """
    xs = sorted(float(s) for s in scores)
    pts = {0.0, 1.0}
    if xs:
        for j in range(n_points + 1):
            pts.add(xs[min(len(xs) - 1, round(j * (len(xs) - 1) / n_points))])
    return sorted(pts)


def _normalize_grid(grid: Iterable[float] | None) -> list[float]:
    if grid is None:
        return default_grid()
    pts = sorted({float(t) for t in grid})
    if not pts or not all(math.isfinite(t) for t in pts):
        raise ValueError("threshold grid must be a non-empty set of finite values")
    return pts


def _failure_counts(scores: Sequence[float], failures: Sequence[bool], grid: Sequence[float]) -> list[int]:
    """k(tau) = #{i : score_i < tau and cheap failed} for every tau in the (sorted) grid."""
    fail_scores = sorted(s for s, f in zip(scores, failures, strict=True) if f)
    return [bisect_left(fail_scores, t) for t in grid]


# ---------------------------------------------------------------------- binomial tests


def _hoeffding_correction(grid: int, delta: float, n: int) -> float:
    return math.sqrt(math.log(grid / delta) / (2 * n)) if n else math.inf


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(Bin(n, p) <= k), pure Python (no scipy dependency)."""
    if k < 0:
        return 0.0
    if k >= n or p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    log_nf = math.lgamma(n + 1)
    total = 0.0
    for j in range(k + 1):
        total += math.exp(log_nf - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * lp + (n - j) * lq)
    return min(1.0, total)


@lru_cache(maxsize=4096)
def _max_certified_count(n: int, alpha: float, delta: float) -> int:
    """Largest failure count k with binomial p-value P(Bin(n, alpha) <= k) <= delta.

    Rejecting H: R > alpha at count k is equivalent to the Clopper-Pearson
    upper bound UB(k) <= alpha. Returns -1 when even k = 0 cannot be certified
    (n too small for (alpha, delta)).
    """
    if n <= 0:
        return -1
    if alpha >= 1.0:
        return n
    lp, lq = math.log(alpha), math.log1p(-alpha)
    log_nf = math.lgamma(n + 1)
    cdf = 0.0
    for k in range(n + 1):
        cdf += math.exp(log_nf - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
        if cdf > delta:
            return k - 1
    return n


@lru_cache(maxsize=65536)
def _binomial_ub(n: int, k: float, delta: float) -> float:
    """Exact Clopper-Pearson upper confidence bound for a binomial proportion.

    ub = Beta^{-1}(1 - delta; k + 1, n - k), i.e. the p solving
    P(Bin(n, p) <= k) = delta. Uses scipy when available, otherwise bisection
    on the pure-Python binomial CDF — both give the same exact bound.
    """
    if n <= 0:
        return 1.0
    kk = max(0.0, min(float(n), k))
    if kk >= n:
        return 1.0
    try:
        from scipy.special import betaincinv

        return float(betaincinv(kk + 1.0, n - kk, 1.0 - delta))
    except ImportError:
        pass
    return _cp_upper_bisect(n, int(math.floor(kk + 1e-9)), delta)


def _cp_upper_bisect(n: int, ki: int, delta: float) -> float:
    """Pure-Python Clopper-Pearson upper bound: bisection for P(Bin(n, p) <= ki) = delta."""
    if ki >= n:
        return 1.0
    lo, hi = ki / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _binom_cdf(ki, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return hi


# ---------------------------------------------------------------------- threshold selection


def _fixed_sequence_threshold(
    scores: list[float],
    failures: list[bool],
    alpha: float,
    delta: float,
    grid: Iterable[float] | None = None,
) -> tuple[float, float, float]:
    """Fixed-sequence Learn-Then-Test (Angelopoulos et al., 2110.01052).

    The deferral rule 'route premium iff score >= tau' is monotone: raising
    tau routes more traffic to the cheap tier, so the cheap-tier failure risk
    R(tau) = P(score < tau, cheap fails) is non-decreasing in tau.

    For each grid point the LTT null is H_tau: R(tau) > alpha (tau is *unsafe*).
    The nulls are tested in the fixed order of increasing tau, starting from
    the riskless end (tau = 0, all premium), each at the full level delta with
    the exact binomial p-value P(Bin(n, alpha) <= k(tau)) — equivalently,
    H_tau is rejected iff the Clopper-Pearson upper bound on R(tau) is
    <= alpha. Testing stops at the first null that is *not* rejected; the
    selection is the largest tau whose null was rejected. Fixed-sequence
    testing controls the family-wise error rate at delta, so

        P( R(tau_hat) > alpha ) <= delta,

    with no Bonferroni / log(m) penalty. If no grid point is certified the
    fallback is tau = 0 (everything routed premium, cheap-tier risk exactly 0).

    Returns (tau_hat, empirical risk at tau_hat, Clopper-Pearson bound at tau_hat).
    """
    pts = _normalize_grid(grid)
    n = len(scores)
    if n == 0:
        return 0.0, 0.0, 0.0
    counts = _failure_counts(scores, failures, pts)
    k_max = _max_certified_count(n, alpha, delta)
    selected: tuple[float, int] | None = None
    for tau, k in zip(pts, counts, strict=True):
        if k > k_max:
            break
        selected = (tau, k)
    if selected is None:
        return 0.0, 0.0, 0.0
    tau, k = selected
    return tau, k / n, _binomial_ub(n, k, delta)


def _hoeffding_threshold(
    scores: list[float],
    failures: list[bool],
    alpha: float,
    delta: float,
    grid: Iterable[float] | None = None,
) -> tuple[float, float, float]:
    """Bonferroni-over-grid Hoeffding UCB: largest tau with R_hat + sqrt(log(m/delta)/2n) <= alpha."""
    pts = _normalize_grid(grid)
    n = len(scores)
    if n == 0:
        return 0.0, 0.0, 0.0
    correction = _hoeffding_correction(len(pts), delta, n)
    counts = _failure_counts(scores, failures, pts)
    best, best_k = 0.0, 0
    for tau, k in zip(pts, counts, strict=True):
        if k / n + correction <= alpha:
            best, best_k = tau, k
    return best, best_k / n, best_k / n + correction


def _select_threshold(
    method: str,
    scores: list[float],
    failures: list[bool],
    alpha: float,
    delta: float,
    grid: Iterable[float] | None,
) -> tuple[float, float, float]:
    if method == "fixed_sequence":
        return _fixed_sequence_threshold(scores, failures, alpha, delta, grid)
    return _hoeffding_threshold(scores, failures, alpha, delta, grid)


class _ClassOnly:
    """Descriptor: callable on the class, refuses to run when accessed via an instance."""

    def __init__(self, fn: Callable, hint: str) -> None:
        self.fn = fn
        self.hint = hint

    def __get__(self, obj: object, owner: type) -> Callable:
        if obj is None:
            return self.fn.__get__(owner, owner)

        def _refuse(*_args: object, **_kwargs: object) -> None:
            raise TypeError(self.hint)

        return _refuse


class ConformalCalibrator:
    """Conformal risk control (CRC) + Learn-Then-Test for the cascade error rate.

    Chooses a difficulty threshold ``tau`` for a monotone deferral rule
    ``route to premium iff score >= tau`` so the *unconditional* error rate
    (queries routed to the cheap tier that would have been handled incorrectly)
    is bounded by ``alpha`` with confidence ``1 - delta``.

    Methods:
    - ``fixed_sequence`` (default): sequential LTT over an ascending tau grid
      with exact binomial (Clopper-Pearson) tests — no multiplicity penalty.
    - ``hoeffding``: Bonferroni-corrected Hoeffding UCB over the grid
      (R_hat + sqrt(log(m/delta)/2n), m = grid size) — the original
      implementation, kept for comparison and continuity with the published
      sweep.

    ``grid``: candidate thresholds. Defaults to the historical 201-point grid
    on [0, 1]. A caller-supplied grid (e.g. ``quantile_grid`` of a separate
    split) must not be derived from the calibration samples.

    Mondrian mode: when calibration samples carry strata labels in
    ``CalibSample.group`` (e.g. code-mix buckets), a separate threshold is
    fitted per group with Bonferroni correction across groups (delta / G), so
    all group guarantees hold simultaneously at 1 - delta. Samples without a
    group label fall in "all". The pooled ``threshold`` (fallback for unknown
    groups) carries its own marginal guarantee at delta.
    """

    def __init__(
        self,
        alpha: float = 0.05,
        delta: float = 0.05,
        method: str = "fixed_sequence",
        grid: Iterable[float] | None = None,
    ) -> None:
        if method not in ("fixed_sequence", "hoeffding"):
            raise ValueError(f"unknown method: {method}")
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if not 0.0 < delta < 1.0:
            raise ValueError("delta must be in (0, 1)")
        self.alpha = alpha
        self.delta = delta
        self.method = method
        self.grid: list[float] = _normalize_grid(grid)
        self.threshold: float = 0.0
        self.n_calib: int = 0
        self.n_fail: int = 0
        self.risk_hat: float = 0.0
        self.risk_bound: float = 0.0
        self.samples: list[CalibSample] = []
        self.group_thresholds: dict[str, float] = {}
        self.group_risk_bounds: dict[str, float] = {}
        self.is_mondrian: bool = False

    # ------------------------------------------------------------------ core

    def _fit_all(self, rows: list[CalibSample], delta: float) -> None:
        if not rows:
            self.threshold = 0.0
            return
        scores = [s.nonconformity for s in rows]
        failures = [not s.cheap_success for s in rows]
        tau, risk, bound = _select_threshold(self.method, scores, failures, self.alpha, delta, self.grid)
        self.threshold = tau
        self.risk_hat = risk
        self.risk_bound = bound

    def calibrate(self, samples: Iterable[CalibSample]) -> ConformalCalibrator:
        rows = list(samples)
        self.samples = rows
        self.n_calib = len(rows)
        self.n_fail = sum(1 for s in rows if not s.cheap_success)
        if self.n_calib == 0:
            self.threshold = 0.0
            self.group_thresholds = {}
            return self

        groups = {s.group for s in rows}
        # Mondrian only when there is more than one distinct stratum label
        mondrian = len(groups) > 1
        self.is_mondrian = mondrian

        if not mondrian:
            self._fit_all(rows, self.delta)
            self.group_thresholds = {}
            self.group_risk_bounds = {}
            return self

        # Bonferroni across G groups: each tested at delta/G
        delta_g = self.delta / len(groups)
        self.group_thresholds = {}
        self.group_risk_bounds = {}
        for g in sorted(groups):
            sub = [s for s in rows if s.group == g]
            tau, _, bound = _select_threshold(
                self.method,
                [s.nonconformity for s in sub],
                [not s.cheap_success for s in sub],
                self.alpha,
                delta_g,
                self.grid,
            )
            self.group_thresholds[g] = tau
            self.group_risk_bounds[g] = bound
        # global threshold = pooled fallback (used when group unknown)
        self._fit_all(rows, self.delta)
        # report the group-level guarantee as the worst group's bound
        self.risk_bound = max(self.group_risk_bounds.values()) if self.group_risk_bounds else self.risk_bound
        return self

    def fit_pairs(
        self,
        scores: list[float],
        cheap_success: list[bool],
        groups: list[str] | None = None,
    ) -> ConformalCalibrator:
        """Calibrate this instance (its alpha / delta / method / grid) on parallel lists."""
        return self.calibrate(_pairs_to_samples(scores, cheap_success, groups))

    def _from_pairs(
        cls,
        scores: list[float],
        cheap_success: list[bool],
        *,
        alpha: float,
        delta: float,
        method: str,
        groups: list[str] | None = None,
        grid: Iterable[float] | None = None,
    ) -> ConformalCalibrator:
        """Class constructor: ``ConformalCalibrator.from_pairs(s, ok, alpha=..., delta=..., method=...)``.

        All risk parameters are required keywords. Calling it on an instance
        raises — use ``instance.fit_pairs(...)`` to fit with the instance's own
        parameters.
        """
        return cls(alpha=alpha, delta=delta, method=method, grid=grid).fit_pairs(scores, cheap_success, groups)

    from_pairs = _ClassOnly(
        _from_pairs,
        "ConformalCalibrator.from_pairs is a class constructor and ignores instance settings; "
        "call instance.fit_pairs(scores, cheap_success) to use this instance's alpha/delta/method",
    )
    del _from_pairs

    # ------------------------------------------------------------------ query

    def _sweep_points(self, rows: list[CalibSample], delta: float, selected: float) -> list[dict]:
        """R_hat(tau) and the bound the configured method certifies, at level delta, over the grid.

        fixed_sequence: per-tau Clopper-Pearson UCB at delta; ``feasible`` marks
        the accepted prefix of the fixed sequence (the bounds are pointwise; the
        selection is valid because the sequence is fixed in advance).
        hoeffding: R_hat + sqrt(log(m/delta)/2n), simultaneously valid over the grid.
        """
        n = len(rows)
        if n == 0:
            return []
        scores = [s.nonconformity for s in rows]
        failures = [not s.cheap_success for s in rows]
        counts = _failure_counts(scores, failures, self.grid)
        points: list[dict] = []
        if self.method == "fixed_sequence":
            k_max = _max_certified_count(n, self.alpha, delta)
            in_prefix = True
            ub_cache: dict[int, float] = {}
            for tau, k in zip(self.grid, counts, strict=True):
                in_prefix = in_prefix and k <= k_max
                if k not in ub_cache:
                    ub_cache[k] = _binomial_ub(n, k, delta)
                points.append(_point(tau, k / n, ub_cache[k], in_prefix, tau == selected))
        else:
            correction = _hoeffding_correction(len(self.grid), delta, n)
            for tau, k in zip(self.grid, counts, strict=True):
                bound = k / n + correction
                points.append(_point(tau, k / n, bound, bound <= self.alpha, tau == selected))
        return points

    def sweep(self) -> list[dict]:
        """Evaluate R_hat(tau) and the method's R_ub(tau) across the grid (pooled samples, level delta)."""
        if self.n_calib == 0 or not self.samples:
            return []
        return self._sweep_points(self.samples, self.delta, self.threshold)

    def sweep_by_group(self) -> dict[str, list[dict]]:
        """Per-group threshold sweeps (Mondrian visualization), each at delta / G."""
        out: dict[str, list[dict]] = {}
        if not self.samples:
            return out
        groups = sorted({s.group for s in self.samples})
        delta_g = self.delta / len(groups) if len(groups) > 1 else self.delta
        for g in groups:
            sub = [s for s in self.samples if s.group == g]
            selected = self.group_thresholds.get(g, self.threshold) if self.is_mondrian else self.threshold
            out[g] = self._sweep_points(sub, delta_g, selected)
        return out

    def route_premium(self, score: float, group: str | None = None) -> bool:
        if group is not None and self.is_mondrian and group in self.group_thresholds:
            return score >= self.group_thresholds[group]
        return score >= self.threshold

    def tier(self, score: float, group: str | None = None) -> str:
        return "premium" if self.route_premium(score, group) else "cheap"

    # ------------------------------------------------------------------ alpha sweep

    def alpha_sweep(
        self,
        alphas: Iterable[float] | None = None,
        include_knee: bool = True,
    ) -> dict:
        """Sweep alpha (the SLA error budget) → threshold / bound / cheap share, simultaneously valid.

        Every (group, alpha) cell is calibrated at

            delta_used = delta / (n_groups * n_alphas)

        (Bonferroni over the Mondrian groups and the alpha grid), so with
        probability >= 1 - delta *every* row's guarantee holds at once. Any
        alpha chosen after looking at this table — by eye, by cost, or by the
        knee — therefore keeps its guarantee R(tau_alpha) <= alpha. Refitting
        each alpha at the full delta and then picking one post hoc does not.

        Mondrian groups (when the calibration set has >1 group) get their own
        threshold per alpha; ``threshold`` then reports the most conservative
        (minimum) group threshold and ``group_thresholds`` has all of them.
        ``risk_hat`` / ``cheap_share`` are realized on the calibration set under
        the group-wise rule; ``risk_bound`` is the worst group's certified bound.

        ``knee`` (Kneedle max-curvature point of alpha vs cheap share) is a
        descriptive reporting helper only; it carries no guarantee of its own —
        the validity of choosing it comes from the grid correction above.
        """
        if not self.samples:
            return {"rows": [], "knee": None, "delta_used": self.delta, "n_tests": 0, "groups": []}
        alpha_list = list(dict.fromkeys(float(a) for a in (alphas if alphas is not None else _DEFAULT_ALPHAS)))
        if not alpha_list:
            return {"rows": [], "knee": None, "delta_used": self.delta, "n_tests": 0, "groups": []}
        groups = sorted({s.group for s in self.samples}) if self.is_mondrian else list(_DEFAULT_GROUPS)
        n_tests = len(groups) * len(alpha_list)
        delta_used = self.delta / n_tests

        by_group: dict[str, tuple[list[float], list[bool]]] = {}
        for g in groups:
            sub = [s for s in self.samples if not self.is_mondrian or s.group == g]
            by_group[g] = ([s.nonconformity for s in sub], [not s.cheap_success for s in sub])

        n = self.n_calib
        rows: list[dict] = []
        for a in alpha_list:
            taus: dict[str, float] = {}
            bounds: dict[str, float] = {}
            for g in groups:
                scores, failures = by_group[g]
                tau, _, bound = _select_threshold(self.method, scores, failures, a, delta_used, self.grid)
                taus[g] = tau
                bounds[g] = bound
            cheap_n = 0
            fail_n = 0
            for s in self.samples:
                tau = taus[s.group] if self.is_mondrian else taus[groups[0]]
                if s.nonconformity < tau:
                    cheap_n += 1
                    fail_n += not s.cheap_success
            row = {
                "alpha": round(a, 4),
                "threshold": round(min(taus.values()), 4),
                "risk_hat": round(fail_n / max(1, n), 4),
                "risk_bound": round(min(1.0, max(bounds.values())), 4),
                "cheap_share": round(cheap_n / max(1, n), 4),
            }
            if self.is_mondrian:
                row["group_thresholds"] = {g: round(t, 4) for g, t in taus.items()}
                row["group_risk_bounds"] = {g: round(min(1.0, b), 4) for g, b in bounds.items()}
            rows.append(row)
        knee = _knee_detection([r["alpha"] for r in rows], [r["cheap_share"] for r in rows]) if include_knee else None
        return {
            "rows": rows,
            "knee": knee,
            "delta_used": delta_used,
            "n_tests": n_tests,
            "groups": groups,
            "method": self.method,
        }


def _pairs_to_samples(
    scores: list[float],
    cheap_success: list[bool],
    groups: list[str] | None,
) -> list[CalibSample]:
    return [
        CalibSample(
            id=str(i),
            nonconformity=s,
            cheap_success=ok,
            group=groups[i] if groups else "all",
        )
        for i, (s, ok) in enumerate(zip(scores, cheap_success, strict=True))
    ]


def _point(tau: float, risk: float, bound: float, feasible: bool, selected: bool) -> dict:
    return {
        "tau": round(tau, 6),
        "risk_hat": round(risk, 6),
        "risk_bound": round(bound, 6),
        "feasible": feasible,
        "is_selected": selected,
    }


def _knee_detection(x: list[float], y: list[float]) -> float | None:
    """Kneedle-style knee: max distance from the (x,y) chord (normalized)."""
    if len(x) < 3 or len(x) != len(y):
        return None
    xs, ys = x, y
    xmin, xmax = min(xs), max(xs)
    if xmax == xmin:
        return None
    ymin, ymax = min(ys), max(ys)
    yspan = ymax - ymin
    nx = [(v - xmin) / (xmax - xmin) for v in xs]
    ny = [(v - ymin) / (yspan or 1.0) for v in ys]
    best_i, best_d = 0, -1.0
    for i in range(len(nx)):
        t = nx[i]
        chord = ny[0] + t * (ny[-1] - ny[0])
        d = abs(ny[i] - chord)
        if d > best_d:
            best_d, best_i = d, i
    return xs[best_i] if best_d > 0 else None
