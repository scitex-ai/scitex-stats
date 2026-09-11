#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-07-03 00:00:00 (ywatanabe)"
# File: scitex_stats/resampling/_delta_auc_ci.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionalities:
  - CI and significance test for the DIFFERENCE of two correlated ROC-AUCs
  - Uses the DeLong covariance of two scorers evaluated on the SAME samples

Dependencies:
  - packages: numpy, scipy

IO:
  - input: Binary labels and two score vectors over the same samples
  - output: dict with delta AUC, CI bounds, SE, z, p, and a formatted string
"""

"""Imports"""
from typing import Any, Dict, Union

import numpy as np
from scipy import stats as _scipy_stats

from scitex_stats._logging import getLogger

from ._delong_core import delong_covariance

logger = getLogger(__name__)

"""Functions"""


def delta_auc_ci(
    y_true: Union[np.ndarray, list],
    y_score_a: Union[np.ndarray, list],
    y_score_b: Union[np.ndarray, list],
    ci: float = 95.0,
) -> Dict[str, Any]:
    """
    DeLong CI and test for the difference of two CORRELATED ROC-AUCs.

    Both scorers must be evaluated on the SAME samples, so their AUCs are
    correlated; the DeLong covariance accounts for that correlation, which a
    naive two-independent-AUCs comparison does not. This is the correct test
    for "does model A discriminate better than model B on this cohort?".

    Parameters
    ----------
    y_true : array
        Binary ground-truth labels (0/1 or bool). Both classes must be present.
    y_score_a : array
        Scores from the first scorer; higher means positive class.
    y_score_b : array
        Scores from the second scorer, over the same samples as ``y_score_a``.
    ci : float, default 95.0
        Confidence level in percent (0 < ci < 100).

    Returns
    -------
    dict
        Keys: ``delta_auc`` (AUC_a - AUC_b), ``auc_a``, ``auc_b``,
        ``ci_lower``, ``ci_upper``, ``ci_level``, ``se``, ``z``, ``p_value``,
        ``method``, ``n``, ``n_positive``, ``n_negative``, ``formatted``.

    Notes
    -----
    With the DeLong covariance matrix :math:`S` of the two AUCs,

    .. math::
        SE(\\Delta) = \\sqrt{S_{11} + S_{22} - 2 S_{12}}, \\qquad
        z = \\Delta / SE(\\Delta),

    and the two-sided p-value is :math:`2(1 - \\Phi(|z|))`. When the two
    scorers are identical the difference is exactly zero with zero variance;
    that degenerate case is reported as ``z = 0`` and ``p_value = 1.0``
    rather than as a division by zero.

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
    >>> res = delta_auc_ci(y, s, s)
    >>> res["delta_auc"], res["p_value"]
    (0.0, 1.0)
    """
    if not 0.0 < ci < 100.0:
        raise ValueError(f"ci must be in (0, 100); got {ci}")

    y_true = np.asarray(y_true)
    score_a = np.asarray(y_score_a, dtype=float)
    score_b = np.asarray(y_score_b, dtype=float)
    if score_a.shape[0] != score_b.shape[0]:
        raise ValueError(
            f"y_score_a has {score_a.shape[0]} samples but y_score_b has "
            f"{score_b.shape[0]}; correlated AUCs require the same samples"
        )
    if y_true.shape[0] != score_a.shape[0]:
        raise ValueError(
            f"y_true has {y_true.shape[0]} samples but the scores have "
            f"{score_a.shape[0]}"
        )

    aucs, cov = delong_covariance(y_true, np.vstack([score_a, score_b]))
    auc_a = float(aucs[0])
    auc_b = float(aucs[1])
    delta = auc_a - auc_b

    variance = float(cov[0, 0] + cov[1, 1] - 2.0 * cov[0, 1])
    variance = max(variance, 0.0)
    se = float(np.sqrt(variance))

    if se > 0.0:
        z = float(delta / se)
        p_value = float(2.0 * _scipy_stats.norm.sf(abs(z)))
    else:
        # Identical (or perfectly concordant) scorers: no evidence of a
        # difference rather than an undefined ratio.
        z = 0.0
        p_value = 1.0

    z_crit = float(_scipy_stats.norm.ppf(0.5 + ci / 200.0))
    lower = float(delta - z_crit * se)
    upper = float(delta + z_crit * se)

    return {
        "delta_auc": float(delta),
        "auc_a": auc_a,
        "auc_b": auc_b,
        "ci_lower": lower,
        "ci_upper": upper,
        "ci_level": float(ci),
        "se": se,
        "z": z,
        "p_value": p_value,
        "method": "delong",
        "n": int(y_true.shape[0]),
        "n_positive": int(np.sum(y_true == 1)),
        "n_negative": int(np.sum(y_true == 0)),
        "formatted": (
            f"dAUC = {delta:+.3f} "
            f"({ci:g}% CI [{lower:+.3f}, {upper:+.3f}], "
            f"z = {z:.2f}, p = {p_value:.3g})"
        ),
    }


# EOF
