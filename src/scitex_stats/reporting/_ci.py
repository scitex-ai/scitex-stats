#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_stats/reporting/_ci.py

"""Test-appropriate confidence intervals for the six-stat report.

Analytic t-test CIs, Fisher-z correlation CIs, and seeded percentile
bootstrap CIs (rank-biserial r for Mann-Whitney; Fisher-z fallback for tiny
correlations). Bootstraps draw from ``numpy.random.default_rng(seed)``
created per interval, never from global state.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

from scitex_stats._logging import getLogger

logger = getLogger(__name__)


def _seeded_rng(seed: int) -> Dict[str, Any]:
    """A fresh Generator per resampling call, under scipy's current keyword."""
    import inspect

    from scipy import stats as scipy_stats

    params = inspect.signature(scipy_stats.bootstrap).parameters
    key = "rng" if "rng" in params else "random_state"
    return {key: np.random.default_rng(seed)}


def _is_finite_num(x: Any) -> bool:
    """True when x is a real, finite number (rejects None/NaN/inf/non-numeric)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return np.isfinite(v)


def _valid_ci(low: Any, high: Any) -> bool:
    """A usable CI: both bounds finite AND correctly ordered (low <= high).

    Catches the two silent-corruption modes that would otherwise pass a
    report as "complete": NaN bounds and reversed (5, -5) bounds.
    """
    return _is_finite_num(low) and _is_finite_num(high) and float(low) <= float(high)


def _method_string(result: Dict[str, Any]) -> str:
    """The method name from `test_method`, falling back to `test`.

    Most families emit `test_method`; repeated-measures ANOVA and Friedman
    (and a few others) emit the name under `test` instead.
    """
    m = result.get("test_method")
    if not m:
        m = result.get("test")
    return m or ""


def _ci_kind(result: Dict[str, Any]) -> Optional[str]:
    """Classify a result into a CI-derivation strategy, or None.

    Returns one of "t", "correlation", "mann_whitney", or None (no defined
    CI semantics for this test -> caller must not emit a generic interval).
    """
    m = _method_string(result).lower()
    if "t-test" in m or "t test" in m or "ttest" in m or "student" in m or "welch" in m:
        return "t"
    if "spearman" in m or "pearson" in m:
        return "correlation"
    if "mann-whitney" in m or "mann whitney" in m or "mannwhitney" in m:
        return "mann_whitney"
    return None


def _analytic_ci(
    result: Dict[str, Any],
    data: Optional[np.ndarray],
    data2: Optional[np.ndarray],
    confidence: float,
) -> Optional[Tuple[float, float]]:
    """Closed-form CI for parametric mean-comparison tests via scipy.

    Reuses `scipy.stats.ttest_*(...).confidence_interval()` — the exact
    machinery the parametric `test_*()` functions already call internally —
    rather than re-deriving the formula. Returns None for anything that
    isn't a recognised parametric t-test (the caller then classifies it).
    """
    if data is None:
        return None

    from scipy import stats as scipy_stats

    method = _method_string(result).lower()
    if "t-test" not in method and "ttest" not in method and "student" not in method:
        return None

    try:
        if data2 is not None and "independent" in method:
            equal_var = "welch" not in method
            r = scipy_stats.ttest_ind(data, data2, equal_var=equal_var)
            ci = r.confidence_interval(confidence_level=confidence)
        elif data2 is not None:
            # Paired / related-samples t-test.
            r = scipy_stats.ttest_rel(data, data2)
            ci = r.confidence_interval(confidence_level=confidence)
        else:
            popmean = result.get("popmean", 0)
            r = scipy_stats.ttest_1samp(data, popmean=popmean)
            ci = r.confidence_interval(confidence_level=confidence)
    except Exception as exc:  # pragma: no cover - defensive, scipy-version guard
        logger.debug(f"Analytic CI unavailable ({exc}); no generic fallback.")
        return None

    low, high = float(ci.low), float(ci.high)
    return (low, high) if _valid_ci(low, high) else None


def _correlation_ci(
    result: Dict[str, Any],
    data: Optional[np.ndarray],
    data2: Optional[np.ndarray],
    confidence: float,
    n_bootstrap: int,
    seed: int,
) -> Optional[Tuple[float, float]]:
    """CI for Pearson r / Spearman rho, on the CORRELATION (not a mean diff).

    Prefers the analytic Fisher-z interval (arctanh(r) +/- se*crit, back-
    transformed with tanh) computed from the reported effect size and the
    sample size. Falls back to a percentile bootstrap of the Fisher-z
    transformed correlation when the analytic form is undefined (e.g. a
    perfect |r| = 1.0, where arctanh diverges) or the sample is tiny.
    Returns None when no data / cannot be computed.
    """
    if data is None or data2 is None:
        return None
    data = np.asarray(data, dtype=float)
    data2 = np.asarray(data2, dtype=float)
    if data.size != data2.size or data.size < 3:
        return None

    method = _method_string(result).lower()
    is_spearman = "spearman" in method

    from scipy import stats as scipy_stats

    def _corr(a: np.ndarray, b: np.ndarray) -> float:
        x, y = np.asarray(a, float), np.asarray(b, float)
        if is_spearman:
            x = scipy_stats.rankdata(x)
            y = scipy_stats.rankdata(y)
        return float(np.corrcoef(x, y)[0, 1])

    r = result.get("effect_size", result.get("statistic"))
    n = data.size

    # A perfect (or degenerate) correlation has no sampling variance: report a
    # degenerate CI [r, r] rather than a wide, misleading interval (arctanh
    # diverges at |r| = 1). This is the honest answer for rho = 1.0.
    # Unrounded r from the tests can land a hair below 1 (float noise).
    if _is_finite_num(r) and abs(float(r)) >= 1.0 - 1e-12:
        rv = float(np.sign(r))
        return (rv, rv)

    # Analytic Fisher-z from the reported r (finite, |r| < 1, n >= 4):
    # arctanh(r) +/- se*crit, back-transformed with tanh.
    if _is_finite_num(r) and abs(float(r)) < 1.0 and n >= 4:
        z = float(np.arctanh(float(r)))
        se = 1.0 / np.sqrt(n - 3)
        crit = float(scipy_stats.norm.ppf(1 - (1 - confidence) / 2.0))
        low = float(np.tanh(z - crit * se))
        high = float(np.tanh(z + crit * se))
        if _valid_ci(low, high):
            return (low, high)

    # Bootstrap the Fisher-z transformed correlation for the residual cases
    # (e.g. very small n). Resample the PAIRS together (paired=True) — an
    # independent resample of x and y destroys the correlation being estimated.
    def _stat(a, b) -> float:
        c = _corr(a, b)
        if not np.isfinite(c):
            return 0.0
        c = max(min(c, 1 - 1e-9), -(1 - 1e-9))
        return float(np.arctanh(c))

    try:
        res = scipy_stats.bootstrap(
            (data, data2),
            _stat,
            confidence_level=confidence,
            n_resamples=n_bootstrap,
            method="percentile",
            paired=True,
            **_seeded_rng(seed),
        )
        low = float(np.tanh(res.confidence_interval.low))
        high = float(np.tanh(res.confidence_interval.high))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Correlation bootstrap CI unavailable ({exc}).")
        return None
    return (low, high) if _valid_ci(low, high) else None


def _mann_whitney_ci(
    data: np.ndarray,
    data2: Optional[np.ndarray],
    confidence: float,
    n_bootstrap: int,
    seed: int,
) -> Optional[Tuple[float, float]]:
    """CI for the Mann-Whitney effect size (rank-biserial r), by bootstrap.

    The MWU statistic U has no simple analytic CI; the reportable effect
    size is the rank-biserial correlation r = 2U/(n1*n2) - 1, so we bootstrap
    THAT (bounded in [-1, 1]) rather than a mean difference. Returns None
    when it cannot be computed.
    """
    if data is None or data2 is None:
        return None
    data = np.asarray(data, dtype=float)
    data2 = np.asarray(data2, dtype=float)
    if data.size < 2 or data2.size < 2:
        return None

    from scipy import stats as scipy_stats

    def _stat(a, b) -> float:
        try:
            u = float(scipy_stats.mannwhitneyu(a, b, alternative="two-sided").statistic)
        except Exception:
            return 0.0
        return (2.0 * u) / (len(a) * len(b)) - 1.0

    try:
        res = scipy_stats.bootstrap(
            (data, data2),
            _stat,
            confidence_level=confidence,
            n_resamples=n_bootstrap,
            method="percentile",
            **_seeded_rng(seed),
        )
        low, high = float(res.confidence_interval.low), float(res.confidence_interval.high)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Mann-Whitney bootstrap CI unavailable ({exc}).")
        return None
    return (low, high) if _valid_ci(low, high) else None


def _derive_ci(
    result: Dict[str, Any],
    data: Optional[np.ndarray],
    data2: Optional[np.ndarray],
    ci: Optional[Tuple[float, float]],
    confidence: float,
    n_bootstrap: int,
    seed: int,
) -> Optional[Tuple[float, float]]:
    """Resolve the CI with test-appropriate semantics, or None (=> missing).

    Precedence: explicit `ci=` (validated) -> result-provided
    `ci_lower`/`ci_upper` (validated) -> derive by test kind -> None. A
    NaN or reversed interval is never passed through as valid.
    """
    if ci is not None:
        if len(ci) == 2 and _valid_ci(ci[0], ci[1]):
            return float(ci[0]), float(ci[1])
        return None  # invalid explicit CI -> treat as missing (fail loudly)

    if "ci_lower" in result and "ci_upper" in result:
        low, high = result["ci_lower"], result["ci_upper"]
        if _valid_ci(low, high):
            return float(low), float(high)
        return None  # NaN / reversed result CI -> treat as missing

    if data is None:
        return None

    kind = _ci_kind(result)
    if kind == "t":
        return _analytic_ci(result, data, data2, confidence)
    if kind == "correlation":
        return _correlation_ci(result, data, data2, confidence, n_bootstrap, seed)
    if kind == "mann_whitney":
        return _mann_whitney_ci(data, data2, confidence, n_bootstrap, seed)
    # No defined CI semantics for this test: do NOT emit a generic
    # mean/mean-difference interval (it would be meaningless for the
    # reported statistic). Return None so the report marks `ci` missing
    # and, under strict, fails loudly.
    return None


def _ci_method(result, data, ci, ci_tuple) -> Optional[str]:
    """How the reported CI was obtained: supplied / result / analytic / fisher_z / bootstrap."""
    if ci_tuple is None:
        return None
    if ci is not None:
        return "supplied"
    if "ci_lower" in result and "ci_upper" in result:
        return "result"
    kind = _ci_kind(result)
    if kind == "mann_whitney":
        return "bootstrap"
    if kind == "correlation":
        r = result.get("effect_size", result.get("statistic"))
        n = 0 if data is None else np.asarray(data).size
        closed_form = _is_finite_num(r) and (abs(float(r)) >= 1.0 - 1e-12 or n >= 4)
        return "fisher_z" if closed_form else "bootstrap"
    return "analytic"

# EOF
