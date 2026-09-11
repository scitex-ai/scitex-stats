#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-07-03 00:00:00 (ywatanabe)"
# File: scitex_stats/resampling/_auc_ci.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionalities:
  - Confidence interval for a single ROC-AUC
  - Analytic DeLong CI (fast Sun & Xu midrank algorithm, numpy-only)
  - Stratified percentile-bootstrap CI as a distribution-free alternative

Dependencies:
  - packages: numpy, scipy

IO:
  - input: Binary labels (0/1) and a score vector
  - output: dict with the AUC, its CI bounds, SE, and a formatted string
"""

"""Imports"""
from typing import Any, Dict, Literal, Union

import numpy as np
from scipy import stats as _scipy_stats

from scitex_stats._logging import getLogger

from ._bootstrap_ci import bootstrap_ci
from ._delong_core import delong_covariance

logger = getLogger(__name__)

"""Functions"""


def auc_ci(
    y_true: Union[np.ndarray, list],
    y_score: Union[np.ndarray, list],
    method: Literal["delong", "bootstrap"] = "delong",
    ci: float = 95.0,
    n_boot: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Confidence interval for a single ROC-AUC.

    Parameters
    ----------
    y_true : array
        Binary ground-truth labels (0/1 or bool). Both classes must be present.
    y_score : array
        Continuous scores; higher values indicate the positive class.
    method : {'delong', 'bootstrap'}, default 'delong'
        - 'delong': analytic CI from the DeLong variance (Sun & Xu midrank
          algorithm). Fast and the standard choice for a single AUC.
        - 'bootstrap': stratified percentile bootstrap, resampling positives
          and negatives separately so every resample keeps both classes.
    ci : float, default 95.0
        Confidence level in percent (0 < ci < 100).
    n_boot : int, default 2000
        Bootstrap resamples. Ignored when ``method='delong'``.
    seed : int, default 42
        Seed for the bootstrap resampler. Ignored when ``method='delong'``.

    Returns
    -------
    dict
        Keys: ``auc``, ``ci_lower``, ``ci_upper``, ``ci_level``, ``se``,
        ``method``, ``n``, ``n_positive``, ``n_negative``, ``formatted``.
        ``se`` is the bootstrap standard deviation when
        ``method='bootstrap'``.

    Notes
    -----
    The DeLong interval is a Wald interval on the AUC scale,

    .. math::
        \\widehat{AUC} \\pm z_{1-\\alpha/2}\\, SE,

    clipped to [0, 1]. It is symmetric and therefore degenerate when the
    AUC is at a boundary (perfect separation gives SE = 0, so both bounds
    collapse onto the estimate); prefer ``method='bootstrap'`` for heavily
    skewed or near-perfect problems.

    References
    ----------
    .. [1] DeLong, E. R., DeLong, D. M., & Clarke-Pearson, D. L. (1988).
           Comparing the areas under two or more correlated receiver
           operating characteristic curves: a nonparametric approach.
           Biometrics, 44(3), 837-845.
    .. [2] Sun, X., & Xu, W. (2014). Fast implementation of DeLong's
           algorithm for comparing the areas under correlated receiver
           operating characteristic curves. IEEE Signal Processing
           Letters, 21(11), 1389-1393.

    Examples
    --------
    >>> y = np.array([0, 0, 1, 1])
    >>> s = np.array([0.1, 0.4, 0.35, 0.8])
    >>> res = auc_ci(y, s)
    >>> round(res["auc"], 3)
    0.75
    """
    if not 0.0 < ci < 100.0:
        raise ValueError(f"ci must be in (0, 100); got {ci}")
    if method not in ("delong", "bootstrap"):
        raise ValueError(
            f"method must be 'delong' or 'bootstrap'; got {method!r}"
        )

    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    if y_true.shape[0] != y_score.shape[0]:
        raise ValueError(
            f"y_true has {y_true.shape[0]} samples but y_score has "
            f"{y_score.shape[0]}"
        )

    n_positive = int(np.sum(y_true == 1))
    n_negative = int(np.sum(y_true == 0))

    if method == "delong":
        aucs, cov = delong_covariance(y_true, y_score)
        auc = float(aucs[0])
        variance = float(cov[0, 0])
        se = float(np.sqrt(variance)) if np.isfinite(variance) else float("nan")
        z = float(_scipy_stats.norm.ppf(0.5 + ci / 200.0))
        lower = float(np.clip(auc - z * se, 0.0, 1.0))
        upper = float(np.clip(auc + z * se, 0.0, 1.0))
    else:
        boot = bootstrap_ci(
            _auc_from_arrays,
            y_true,
            y_score,
            n_boot=n_boot,
            ci=ci,
            seed=seed,
            stratify=y_true,
        )
        auc = float(boot["estimate"])
        se = float(boot["se"])
        lower = float(np.clip(boot["ci_lower"], 0.0, 1.0))
        upper = float(np.clip(boot["ci_upper"], 0.0, 1.0))

    return {
        "auc": auc,
        "ci_lower": lower,
        "ci_upper": upper,
        "ci_level": float(ci),
        "se": se,
        "method": method,
        "n": int(y_true.shape[0]),
        "n_positive": n_positive,
        "n_negative": n_negative,
        "formatted": (
            f"AUC = {auc:.3f} "
            f"({ci:g}% CI [{lower:.3f}, {upper:.3f}], {method})"
        ),
    }


def _auc_from_arrays(
    y_true: np.ndarray, y_score: np.ndarray
) -> float:
    """Return the ROC-AUC of ``y_score`` against binary ``y_true``."""
    aucs, _ = delong_covariance(y_true, y_score)
    return float(aucs[0])


# EOF
