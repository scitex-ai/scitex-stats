#!/usr/bin/env python3
# File: scitex_stats/descriptive/_bootstrap_ci.py

"""Seeded bootstrap confidence interval of a statistic.

The public entry point for "median [95% CI]"-style reporting. Wraps
``scipy.stats.bootstrap`` with a fresh ``numpy.random.default_rng(seed)`` per
call (never global state), validates the input explicitly (n < 2, NaNs,
constant input) and returns a JSON-native dict whose keys follow the rest of
the package (``ci_lower`` / ``ci_upper`` / ``ci_level``), so it can be saved
with ``scitex_io.save`` and rendered with the APA helpers unchanged.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np

__all__ = ["bootstrap_ci", "BOOTSTRAP_STATISTICS", "BOOTSTRAP_METHODS", "NAN_POLICIES"]

# Named one-sample statistics: name -> vectorised function (takes ``axis``).
BOOTSTRAP_STATISTICS: Dict[str, Callable[..., Any]] = {
    "median": np.median,
    "mean": np.mean,
}
BOOTSTRAP_METHODS: Tuple[str, ...] = ("percentile", "basic", "bca")
NAN_POLICIES: Tuple[str, ...] = ("raise", "omit")

_METHOD_LABELS = {
    "percentile": "percentile bootstrap",
    "basic": "basic bootstrap",
    "bca": "BCa bootstrap",
}


def _rng_kwarg(seed: int) -> Dict[str, Any]:
    """A fresh Generator under scipy's current keyword (``rng`` / ``random_state``)."""
    from scipy import stats as scipy_stats

    params = inspect.signature(scipy_stats.bootstrap).parameters
    key = "rng" if "rng" in params else "random_state"
    return {key: np.random.default_rng(seed)}


def _as_1d(x: Any, name: str) -> np.ndarray:
    try:
        arr = np.asarray(x, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric array-like: {exc}") from exc
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional; got shape {arr.shape}.")
    if np.isinf(arr).any():
        raise ValueError(
            f"{name} contains infinite values; a bootstrap CI is undefined."
        )
    return arr


def _apply_nan_policy(
    samples: Sequence[np.ndarray], paired: bool, nan_policy: str
) -> Tuple[Tuple[np.ndarray, ...], int]:
    """NaN-free samples and the number dropped (pairs when ``paired``)."""
    masks = [np.isnan(s) for s in samples]
    n_nan = int(sum(m.sum() for m in masks))
    if n_nan == 0:
        return tuple(samples), 0
    if nan_policy == "raise":
        raise ValueError(
            f"Input contains {n_nan} NaN value(s). Pass nan_policy='omit' to drop "
            "them explicitly (the number dropped is reported as n_nan_omitted)."
        )
    if paired:
        keep = ~np.logical_or.reduce(masks)
        return tuple(s[keep] for s in samples), int((~keep).sum())
    return tuple(s[~m] for s, m in zip(samples, masks)), n_nan


def bootstrap_ci(
    data: Any,
    statistic: Union[str, Callable[..., float]] = "median",
    *,
    data2: Optional[Any] = None,
    paired: bool = False,
    confidence: float = 0.95,
    n_resamples: int = 10_000,
    method: str = "percentile",
    seed: int = 42,
    nan_policy: str = "raise",
) -> Dict[str, Any]:
    """Seeded bootstrap confidence interval of a statistic.

    Parameters
    ----------
    data : array-like
        One-dimensional numeric sample.
    statistic : {"median", "mean"} or callable, default "median"
        Named statistic, or a callable ``f(sample)`` (``f(sample, sample2)``
        when ``data2`` is given) returning a scalar. Named statistics are
        one-sample only.
    data2 : array-like, optional
        Second sample for a two-sample callable statistic.
    paired : bool, default False
        Resample ``data`` and ``data2`` together (same indices), preserving
        pairing, e.g. for a correlation. Requires equal lengths.
    confidence : float, default 0.95
        Confidence level, strictly between 0 and 1.
    n_resamples : int, default 10000
        Number of bootstrap resamples (>= 1).
    method : {"percentile", "basic", "bca"}, default "percentile"
        Interval construction passed to ``scipy.stats.bootstrap``.
    seed : int, default 42
        Seed for ``numpy.random.default_rng``; equal seeds give equal intervals.
    nan_policy : {"raise", "omit"}, default "raise"
        ``"raise"`` rejects any NaN; ``"omit"`` drops NaNs (whole pairs when
        ``paired``) and reports the count in ``n_nan_omitted`` (observations,
        or pairs when ``paired``).

    Returns
    -------
    dict
        JSON-native values: ``statistic``, ``estimate``, ``ci_lower``,
        ``ci_upper``, ``ci_level``, ``method``, ``ci_method``, ``n`` (and
        ``n2`` for two samples), ``n_resamples``, ``seed``, ``nan_policy``,
        ``n_nan_omitted`` and ``ci_apa`` (``"95% CI [lo, hi]"``).

    Raises
    ------
    ValueError
        Fewer than two observations (per sample), NaNs under
        ``nan_policy="raise"``, infinite values, constant input (zero-width
        resampling distribution), invalid parameters, or a non-finite
        interval from the resampler.
    TypeError
        Non-numeric data or an unsupported ``statistic`` type.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.random.default_rng(0).lognormal(size=50)
    >>> res = bootstrap_ci(x, "median", seed=1)
    >>> res["ci_lower"] <= res["estimate"] <= res["ci_upper"]
    True
    >>> res == bootstrap_ci(x, "median", seed=1)
    True
    """
    from scipy import stats as scipy_stats

    from scitex_stats._utils._apa import format_ci

    # --- parameters -------------------------------------------------------
    if nan_policy not in NAN_POLICIES:
        raise ValueError(
            f"nan_policy must be one of {NAN_POLICIES}; got {nan_policy!r}."
        )
    if method not in BOOTSTRAP_METHODS:
        raise ValueError(f"method must be one of {BOOTSTRAP_METHODS}; got {method!r}.")
    if isinstance(confidence, bool) or not (
        isinstance(confidence, (int, float)) and 0 < confidence < 1
    ):
        raise ValueError(f"confidence must be a number in (0, 1); got {confidence!r}.")
    if (
        isinstance(n_resamples, bool)
        or not isinstance(n_resamples, (int, np.integer))
        or n_resamples < 1
    ):
        raise ValueError(
            f"n_resamples must be a positive integer; got {n_resamples!r}."
        )
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError(f"seed must be an integer; got {seed!r}.")
    if paired and data2 is None:
        raise ValueError("paired=True requires data2.")

    if isinstance(statistic, str):
        if statistic not in BOOTSTRAP_STATISTICS:
            raise ValueError(
                f"statistic must be one of {tuple(BOOTSTRAP_STATISTICS)} or a callable; got {statistic!r}."
            )
        if data2 is not None:
            raise ValueError(
                f"Named statistic {statistic!r} is one-sample; pass a callable for two samples."
            )
        fn = BOOTSTRAP_STATISTICS[statistic]
        stat_name = statistic
        vectorized = True

        def stat_fn(a, axis=-1):
            return fn(a, axis=axis)

    elif callable(statistic):
        stat_name = getattr(statistic, "__name__", type(statistic).__name__)
        vectorized = False
        stat_fn = statistic
    else:
        raise TypeError(
            f"statistic must be a name or a callable; got {type(statistic).__name__}."
        )

    # --- data ---------------------------------------------------------------
    samples = [_as_1d(data, "data")]
    if data2 is not None:
        samples.append(_as_1d(data2, "data2"))
        if paired and samples[0].size != samples[1].size:
            raise ValueError(
                f"paired=True requires equal lengths; got {samples[0].size} and {samples[1].size}."
            )
    clean, n_omitted = _apply_nan_policy(samples, paired, nan_policy)
    for label, s in zip(("data", "data2"), clean):
        if s.size < 2:
            raise ValueError(
                f"{label} needs at least 2 non-NaN observations for a bootstrap CI; got {s.size}."
            )
    if all(np.ptp(s) == 0 for s in clean):
        raise ValueError(
            "Input is constant: every resample is identical, so the bootstrap CI is "
            "degenerate. Report the value without an interval instead."
        )

    # --- compute ------------------------------------------------------------
    estimate = float(stat_fn(*clean))
    if not np.isfinite(estimate):
        raise ValueError(
            f"statistic {stat_name!r} is not finite on the input ({estimate})."
        )
    res = scipy_stats.bootstrap(
        clean,
        stat_fn,
        n_resamples=int(n_resamples),
        confidence_level=float(confidence),
        method=method,
        vectorized=vectorized,
        paired=bool(paired),
        **_rng_kwarg(int(seed)),
    )
    lo, hi = float(res.confidence_interval.low), float(res.confidence_interval.high)
    if not (np.isfinite(lo) and np.isfinite(hi)) or lo > hi:
        raise ValueError(
            f"The {method} bootstrap returned an unusable interval ({lo}, {hi}); "
            "the resampling distribution is degenerate for this input."
        )

    out: Dict[str, Any] = {
        "statistic": stat_name,
        "estimate": estimate,
        "ci_lower": lo,
        "ci_upper": hi,
        "ci_level": float(confidence),
        "method": method,
        "ci_method": f"{_METHOD_LABELS[method]} ({int(n_resamples)} resamples, seed {int(seed)})",
        "n": int(clean[0].size),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "nan_policy": nan_policy,
        "n_nan_omitted": int(n_omitted),
        "ci_apa": format_ci(lo, hi, confidence),
    }
    if len(clean) == 2:
        out["n2"] = int(clean[1].size)
        out["paired"] = bool(paired)
    return out


# EOF
