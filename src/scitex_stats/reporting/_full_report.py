#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_stats/reporting/_full_report.py

"""Six-stat report builder.

Functionalities:
  - Bundle the six mandatory fields of a complete statistical report
    (n, 95% CI, method, p-value, effect size, test statistic) from a
    `run_test()` / `test_*()`-style result dict
  - Derive a confidence interval analytically (scipy closed-form) for
    parametric mean-comparison tests, or via bootstrap resampling for
    anything without a closed form
  - Raise a clear error (or warn) when a required field cannot be
    determined, so partial reports never silently pass as complete

Dependencies:
  - packages: numpy, scipy

IO:
  - input: a `run_test()`/`test_*()` result dict, plus optionally the raw
    data array(s) or a precomputed CI tuple
  - output: a dict bundling all six fields plus a human-readable string
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

from scitex_stats._logging import getLogger
from scitex_stats._utils._formatters import fmt_sym_md

logger = getLogger(__name__)

# The six mandatory fields of the operator's six-stat reporting doctrine
# (2026-07-05): n, 95% CI, method, p-value, effect size, test statistic.
SIX_STAT_FIELDS: Tuple[str, ...] = (
    "n",
    "ci",
    "method",
    "pvalue",
    "effect_size",
    "statistic",
)

# Sample-size keys already emitted by the various `test_*()` functions.
# Collected as-is; this module does not attempt to relabel them to the
# N (subject-level) / n (window-level) convention because a generic
# array-based test function has no way to know which level its input
# represents — that judgement belongs to the caller.
_N_KEY_CANDIDATES: Tuple[str, ...] = (
    "n_x",
    "n_y",
    "n_1",
    "n_2",
    "n",
    "n_pairs",
    "n_groups",
    "n_samples",
    "N",
    "N_subjects",
    "n_windows",
)

# effect_size_metric string (as emitted by test_* functions) -> plain-text
# symbol used in the formatted six-stat string.
_EFFECT_SYMBOLS: Dict[str, str] = {
    "Cohen's d": "d",
    "Hedges' g": "g",
    "Glass's delta": "Δ",
    "Cliff's delta": "δ",
    "eta-squared": "η²",
    "eta squared": "η²",
    "epsilon-squared": "ε²",
    "epsilon squared": "ε²",
    "partial eta-squared": "η²_p",
    "probability of superiority": "P(X>Y)",
    "r": "r",
    "rho": "ρ",
    "tau": "τ",
}


class IncompleteReportError(ValueError):
    """Raised when a six-stat report cannot be assembled in full.

    Encodes "partial reporting is incomplete" as a checked invariant: this
    is raised (rather than silently returning a partial dict) whenever one
    of the six mandatory fields — n, 95% CI, method, p-value, effect size,
    test statistic — cannot be determined from the inputs given.
    """


def _extract_n(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Collect every sample-size-like key present in a test result dict."""
    found = {k: result[k] for k in _N_KEY_CANDIDATES if k in result}
    return found or None


def _analytic_ci(
    result: Dict[str, Any],
    data: Optional[np.ndarray],
    data2: Optional[np.ndarray],
    confidence: float,
) -> Optional[Tuple[float, float]]:
    """Closed-form CI for parametric mean-comparison tests via scipy.

    Reuses `scipy.stats.ttest_*(...).confidence_interval()` — the exact
    machinery the parametric `test_*()` functions already call internally
    — rather than re-deriving the formula. Returns None (falls through to
    bootstrap) for anything that isn't a recognised parametric t-test.
    """
    if data is None:
        return None

    from scipy import stats as scipy_stats

    method = (result.get("test_method") or "").lower()
    if "t-test" not in method:
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
        logger.debug(f"Analytic CI unavailable ({exc}); falling back to bootstrap.")
        return None

    return float(ci.low), float(ci.high)


def _bootstrap_ci(
    data: np.ndarray,
    data2: Optional[np.ndarray],
    confidence: float,
    n_bootstrap: int,
    random_state,
) -> Optional[Tuple[float, float]]:
    """Bootstrap CI fallback for tests without a closed-form interval.

    Prefers `scitex_stats.resampling.bootstrap_ci` when that (currently
    unmerged — see PR #66) module is importable, so this delegates rather
    than duplicates once it lands. Falls back to `scipy.stats.bootstrap`
    (already a hard dependency of this package) otherwise.
    """
    try:
        from scitex_stats.resampling import bootstrap_ci as _resampling_bootstrap_ci

        if data2 is not None:
            out = _resampling_bootstrap_ci(
                data,
                data2,
                statistic="mean_diff",
                confidence=confidence,
                n_bootstrap=n_bootstrap,
                random_state=random_state,
            )
        else:
            out = _resampling_bootstrap_ci(
                data,
                statistic="mean",
                confidence=confidence,
                n_bootstrap=n_bootstrap,
                random_state=random_state,
            )
        return float(out["ci_lower"]), float(out["ci_upper"])
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"scitex_stats.resampling.bootstrap_ci failed ({exc}); using scipy.stats.bootstrap.")

    from scipy import stats as scipy_stats

    data = np.asarray(data)
    if data2 is not None:
        data2 = np.asarray(data2)

        def _statistic(a, b):
            return np.mean(a) - np.mean(b)

        samples = (data, data2)
    else:

        def _statistic(a):
            return np.mean(a)

        samples = (data,)

    res = scipy_stats.bootstrap(
        samples,
        _statistic,
        confidence_level=confidence,
        n_resamples=n_bootstrap,
        method="percentile",
        random_state=random_state,
    )
    return float(res.confidence_interval.low), float(res.confidence_interval.high)


def _derive_ci(
    result: Dict[str, Any],
    data: Optional[np.ndarray],
    data2: Optional[np.ndarray],
    ci: Optional[Tuple[float, float]],
    confidence: float,
    n_bootstrap: int,
    random_state,
) -> Optional[Tuple[float, float]]:
    if ci is not None:
        return float(ci[0]), float(ci[1])

    if "ci_lower" in result and "ci_upper" in result:
        return float(result["ci_lower"]), float(result["ci_upper"])

    if data is None:
        return None

    analytic = _analytic_ci(result, data, data2, confidence)
    if analytic is not None:
        return analytic

    return _bootstrap_ci(data, data2, confidence, n_bootstrap, random_state)


def _format_pvalue(pvalue: float, stars: Optional[str]) -> str:
    p_str = "p < .001" if pvalue < 0.001 else f"p = {pvalue:.3f}".replace("0.", ".")
    if stars and stars != "ns":
        p_str += f" {stars}"
    return p_str


def _format_six_stat(
    *,
    method: Optional[str],
    stat_symbol: str,
    statistic: Optional[float],
    df: Optional[Any],
    pvalue: Optional[float],
    stars: Optional[str],
    effect_size_metric: Optional[str],
    effect_size: Optional[float],
    ci: Optional[Tuple[float, float]],
    confidence: float,
    n: Optional[Dict[str, Any]],
) -> str:
    """Render the six fields as one human-readable, markdown-italicized line."""
    segments = []

    sym = stat_symbol or "stat"
    sym_md = fmt_sym_md(sym)
    if statistic is None:
        stat_segment = f"{sym_md} = NA"
    elif df is not None:
        stat_segment = f"{sym_md}({df}) = {statistic:.2f}"
    else:
        stat_segment = f"{sym_md} = {statistic:.2f}"
    segments.append(stat_segment)

    if pvalue is not None:
        segments.append(_format_pvalue(pvalue, stars).replace("p ", f"{fmt_sym_md('p')} ", 1))

    if effect_size is not None:
        es_sym = _EFFECT_SYMBOLS.get(effect_size_metric or "", None)
        es_sym_md = fmt_sym_md(es_sym) if es_sym else (effect_size_metric or "effect size")
        segments.append(f"{es_sym_md} = {effect_size:.2f}")

    if ci is not None:
        level_pct = int(round(confidence * 100))
        segments.append(f"{level_pct}% CI [{ci[0]:.2f}, {ci[1]:.2f}]")

    if n:
        n_segments = []
        for key, value in n.items():
            n_segments.append(f"{fmt_sym_md(key)} = {value}")
        segments.append(", ".join(n_segments))

    body = ", ".join(segments)
    return f"{method}: {body}" if method else body


def full_report(
    result: Dict[str, Any],
    *,
    data: Optional[Union[np.ndarray, Sequence[float]]] = None,
    data2: Optional[Union[np.ndarray, Sequence[float]]] = None,
    ci: Optional[Tuple[float, float]] = None,
    confidence: float = 0.95,
    n_bootstrap: int = 10_000,
    random_state: Optional[int] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """Bundle a `run_test()`/`test_*()` result into a complete six-stat report.

    Encodes the operator's six-stat reporting doctrine (2026-07-05): every
    reported statistic must carry all of (1) n, (2) 95% CI, (3) method, (4)
    p-value, (5) effect size, (6) test statistic. Partial reporting is
    treated as incomplete — by default this raises :class:`IncompleteReportError`
    rather than silently returning a partial dict.

    Parameters
    ----------
    result : dict
        A result dict as returned by `scitex_stats.run_test()` or any
        `scitex_stats.tests.test_*()` function. Expected to already carry
        `test_method`, `statistic`, `stat_symbol`, `pvalue`, `effect_size`,
        `effect_size_metric`, and one or more sample-size keys (`n_x`/`n_y`,
        `n`, `n_pairs`, ...).
    data, data2 : array-like, optional
        Raw sample(s) the test was run on. Used to derive a confidence
        interval when *result* and *ci* don't already carry one: an
        analytic mean-comparison CI (via `scipy.stats.ttest_*(...)
        .confidence_interval()`) for parametric t-tests, otherwise a
        percentile bootstrap CI.
    ci : tuple of (float, float), optional
        An already-computed `(lower, upper)` confidence interval. Takes
        precedence over deriving one from *data*/*data2*.
    confidence : float, default 0.95
        Confidence level for the interval (analytic or bootstrap).
    n_bootstrap : int, default 10000
        Bootstrap resamples, used only when falling back to bootstrap CI.
    random_state : int, optional
        Seed forwarded to the bootstrap resampler for reproducibility.
    strict : bool, default True
        If True (default), raise :class:`IncompleteReportError` when any of
        the six mandatory fields cannot be determined. If False, log a
        warning instead and return the partial report with a
        `missing_fields` list.

    Returns
    -------
    dict
        Keys: `method`, `statistic`, `stat_symbol`, `pvalue`, `effect_size`,
        `effect_size_metric`, `n`, `ci`, `ci_level`, `formatted`,
        `missing_fields`.

    Raises
    ------
    IncompleteReportError
        If `strict=True` and one or more of the six mandatory fields
        (n, ci, method, pvalue, effect_size, statistic) cannot be
        determined from *result* / *data* / *data2* / *ci*.

    Examples
    --------
    >>> import numpy as np
    >>> from scitex_stats import run_test, full_report
    >>> x = np.random.default_rng(0).normal(0, 1, 50)
    >>> y = np.random.default_rng(1).normal(0.5, 1, 50)
    >>> result = run_test("ttest_ind", data=x, data2=y)
    >>> report = full_report(result, data=x, data2=y)
    >>> report["ci"] is not None
    True
    """
    if data is not None:
        data = np.asarray(data, dtype=float)
    if data2 is not None:
        data2 = np.asarray(data2, dtype=float)

    missing = []

    method = result.get("test_method")
    if not method:
        missing.append("method")

    statistic = result.get("statistic")
    if statistic is None:
        missing.append("statistic")
    stat_symbol = result.get("stat_symbol", "")

    pvalue = result.get("pvalue")
    if pvalue is None:
        missing.append("pvalue")
    stars = result.get("stars")

    effect_size = result.get("effect_size")
    if effect_size is None:
        missing.append("effect_size")
    effect_size_metric = result.get("effect_size_metric")

    n = _extract_n(result)
    if n is None:
        missing.append("n")

    ci_tuple = _derive_ci(result, data, data2, ci, confidence, n_bootstrap, random_state)
    if ci_tuple is None:
        missing.append("ci")

    if missing:
        message = (
            "Incomplete six-stat report — missing required field(s): "
            f"{', '.join(missing)}. Under the six-stat reporting doctrine, n, "
            "95% CI, method, p-value, effect size, and test statistic are all "
            "required; partial reporting is not accepted. Pass `data=`/"
            "`data2=` (or an explicit `ci=(lower, upper)`) so a confidence "
            "interval can be derived, or extend the input result dict with "
            "the missing field(s)."
        )
        if strict:
            raise IncompleteReportError(message)
        logger.warning(message)

    formatted = _format_six_stat(
        method=method,
        stat_symbol=stat_symbol,
        statistic=statistic,
        df=result.get("df"),
        pvalue=pvalue,
        stars=stars,
        effect_size_metric=effect_size_metric,
        effect_size=effect_size,
        ci=ci_tuple,
        confidence=confidence,
        n=n,
    )

    return {
        "method": method,
        "statistic": statistic,
        "stat_symbol": stat_symbol,
        "pvalue": pvalue,
        "effect_size": effect_size,
        "effect_size_metric": effect_size_metric,
        "n": n,
        "ci": ci_tuple,
        "ci_level": confidence if ci_tuple is not None else None,
        "formatted": formatted,
        "missing_fields": missing,
    }


# EOF
