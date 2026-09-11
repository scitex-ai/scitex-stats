#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-07-03 00:00:00 (ywatanabe)"
# File: scitex_stats/resampling/_bootstrap_ci.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionalities:
  - Generic percentile-bootstrap confidence interval for any metric
  - Paired (row-wise) resampling across several aligned arrays
  - Optional stratified resampling to keep every group represented

Dependencies:
  - packages: numpy

IO:
  - input: A metric callable and one or more aligned sample arrays
  - output: dict with the point estimate, CI bounds, SE, and a formatted string
"""

"""Imports"""
from typing import Any, Callable, Dict, Optional, Sequence, Union

import numpy as np

from scitex_stats._logging import getLogger

logger = getLogger(__name__)

"""Functions"""


def bootstrap_ci(
    fn: Callable[..., float],
    *arrays: Union[np.ndarray, Sequence],
    n_boot: int = 2000,
    ci: float = 95.0,
    seed: int = 42,
    stratify: Optional[Union[np.ndarray, Sequence]] = None,
) -> Dict[str, Any]:
    """
    Percentile-bootstrap confidence interval for an arbitrary metric.

    Use this when a metric has no convenient analytic CI. Rows are
    resampled JOINTLY across all supplied arrays, so paired structure
    (e.g. labels alongside scores) is preserved in every resample.

    Parameters
    ----------
    fn : callable
        Metric computed as ``fn(*arrays) -> float``. Called once on the
        observed data for the point estimate and once per resample.
    *arrays : array
        One or more aligned arrays with the same length along axis 0.
    n_boot : int, default 2000
        Number of bootstrap resamples.
    ci : float, default 95.0
        Confidence level in percent (0 < ci < 100).
    seed : int, default 42
        Seed for the random generator, making the interval reproducible.
    stratify : array, optional
        Group labels resampled within-group, guaranteeing every group keeps
        its observed size in each resample. Pass the binary outcome for
        classification metrics such as AUC, which are undefined when a
        resample happens to contain a single class.

    Returns
    -------
    dict
        Keys: ``estimate``, ``ci_lower``, ``ci_upper``, ``ci_level``,
        ``se``, ``n_boot``, ``n_valid``, ``n``, ``method``, ``formatted``.
        ``se`` is the standard deviation of the bootstrap distribution and
        ``n_valid`` counts resamples on which ``fn`` returned a finite value.

    Raises
    ------
    ValueError
        If no arrays are given, the arrays differ in length, ``ci`` is out of
        range, ``n_boot`` is not positive, or every resample failed.

    Notes
    -----
    Without ``stratify``, a resample of a small or heavily imbalanced sample
    can be degenerate (e.g. one class only), and a metric may then raise or
    return a non-finite value. Such resamples are DISCARDED rather than
    silently coerced, counted in ``n_valid``, and warned about when they
    exceed 10% of ``n_boot`` — a wide gap between ``n_valid`` and ``n_boot``
    means the interval rests on fewer resamples than requested. Stratifying
    removes this failure mode for classification metrics.

    References
    ----------
    .. [1] Efron, B., & Tibshirani, R. J. (1993). An Introduction to the
           Bootstrap. Chapman & Hall.

    Examples
    --------
    >>> x = np.arange(100, dtype=float)
    >>> res = bootstrap_ci(np.mean, x, n_boot=1000, seed=0)
    >>> res["ci_lower"] < res["estimate"] < res["ci_upper"]
    True
    """
    if not arrays:
        raise ValueError("bootstrap_ci requires at least one array")
    if not 0.0 < ci < 100.0:
        raise ValueError(f"ci must be in (0, 100); got {ci}")
    if n_boot <= 0:
        raise ValueError(f"n_boot must be positive; got {n_boot}")

    materialized = [np.asarray(each) for each in arrays]
    n = materialized[0].shape[0]
    for index, each in enumerate(materialized):
        if each.shape[0] != n:
            raise ValueError(
                f"all arrays must share length along axis 0; array 0 has "
                f"{n} rows but array {index} has {each.shape[0]}"
            )

    estimate = float(fn(*materialized))

    if stratify is None:
        index_groups = [np.arange(n)]
    else:
        stratify_arr = np.asarray(stratify)
        if stratify_arr.shape[0] != n:
            raise ValueError(
                f"stratify has {stratify_arr.shape[0]} rows but the arrays "
                f"have {n}"
            )
        index_groups = [
            np.flatnonzero(stratify_arr == value)
            for value in np.unique(stratify_arr)
        ]

    rng = np.random.default_rng(seed)
    replicates = np.empty(n_boot, dtype=float)
    n_valid = 0
    for boot_index in range(n_boot):
        picks = np.concatenate(
            [rng.choice(group, size=group.size, replace=True) for group in index_groups]
        )
        try:
            value = float(fn(*[each[picks] for each in materialized]))
        except (ValueError, ZeroDivisionError, FloatingPointError):
            continue
        if np.isfinite(value):
            replicates[n_valid] = value
            n_valid += 1

    if n_valid == 0:
        raise ValueError(
            f"every one of the {n_boot} bootstrap resamples failed to yield a "
            f"finite value for {getattr(fn, '__name__', fn)!r}. Pass "
            f"stratify=<group labels> to keep each group present in every "
            f"resample, or check that fn tolerates repeated rows."
        )
    if n_valid < n_boot:
        logger.warning(
            f"{n_boot - n_valid} of {n_boot} bootstrap resamples were "
            f"discarded (non-finite metric); CI rests on {n_valid} resamples. "
            f"Consider stratify=<group labels>."
        )

    replicates = replicates[:n_valid]
    alpha = (100.0 - ci) / 2.0
    lower = float(np.percentile(replicates, alpha))
    upper = float(np.percentile(replicates, 100.0 - alpha))
    se = float(np.std(replicates, ddof=1)) if n_valid > 1 else float("nan")

    return {
        "estimate": estimate,
        "ci_lower": lower,
        "ci_upper": upper,
        "ci_level": float(ci),
        "se": se,
        "n_boot": int(n_boot),
        "n_valid": int(n_valid),
        "n": int(n),
        "method": "bootstrap",
        "formatted": (
            f"{estimate:.3f} ({ci:g}% CI [{lower:.3f}, {upper:.3f}], "
            f"{n_valid} bootstrap resamples)"
        ),
    }


# EOF
