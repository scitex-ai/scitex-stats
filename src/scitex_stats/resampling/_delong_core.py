#!/usr/bin/env python3
# Timestamp: "2026-07-03 00:00:00 (ywatanabe)"
# File: scitex_stats/resampling/_delong_core.py
# ----------------------------------------
from __future__ import annotations

"""
Functionalities:
  - Midrank computation (tie-aware ranks) for the fast DeLong algorithm
  - Fast DeLong AUC variance/covariance estimation for one or more
    correlated ROC-AUCs measured on the same samples (Sun & Xu 2014,
    O(n log n) instead of the naive O(n^2))

Dependencies:
  - packages: numpy

IO:
  - input: Binary labels (0/1) and one or more score vectors
  - output: AUC point estimates and their DeLong covariance matrix
"""

import os
from typing import Tuple, Union

import numpy as np

from scitex_stats._logging import getLogger

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

logger = getLogger(__name__)

"""Functions"""


def compute_midrank(x: np.ndarray) -> np.ndarray:
    """Compute midranks (tie-aware ranks) of a 1-D array.

    Tied values all receive the average of the ranks they span, which
    is what makes the DeLong estimator (and the equivalent
    Mann-Whitney AUC) correct in the presence of tied scores.

    Parameters
    ----------
    x : array
        1-D array of scores.

    Returns
    -------
    np.ndarray
        Midranks (1-based, float) in the original order of ``x``.

    References
    ----------
    .. [1] Sun, X., & Xu, W. (2014). Fast implementation of DeLong's
           algorithm for comparing the areas under correlated receiver
           operating characteristic curves. IEEE Signal Processing
           Letters, 21(11), 1389-1393.

    Examples
    --------
    >>> compute_midrank(np.array([0.1, 0.4, 0.4, 0.8]))
    array([1. , 2.5, 2.5, 4. ])
    """
    x = np.asarray(x, dtype=float)
    sorter = np.argsort(x, kind="mergesort")
    sorted_x = x[sorter]
    n = len(x)

    midranks_sorted = np.zeros(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j < n and sorted_x[j] == sorted_x[i]:
            j += 1
        midranks_sorted[i:j] = 0.5 * (i + j - 1) + 1.0
        i = j

    midranks = np.empty(n, dtype=float)
    midranks[sorter] = midranks_sorted
    return midranks


def delong_covariance(
    y_true: Union[np.ndarray, list],
    scores: Union[np.ndarray, list],
) -> Tuple[np.ndarray, np.ndarray]:
    """Fast DeLong AUCs + covariance for k correlated scorers.

    Computes the ROC-AUC of each score vector via midranks (equivalent
    to the Mann-Whitney U statistic, so no sklearn dependency) and the
    DeLong covariance matrix of the k AUCs from the empirical
    covariances of the structural components v01/v10.

    Parameters
    ----------
    y_true : array
        Binary ground-truth labels (0/1 or bool). Both classes must be
        present.
    scores : array, shape (k, n) or (n,)
        One row per scorer; each row scores the SAME n samples
        (correlated AUCs).

    Returns
    -------
    aucs : np.ndarray, shape (k,)
        AUC point estimate per scorer.
    cov : np.ndarray, shape (k, k)
        DeLong covariance matrix of the AUC estimates. Diagonal entries
        are the squared standard errors. Entries are NaN when a class
        has a single sample (empirical covariance undefined).

    Notes
    -----
    With m positives (midranks ``tx``), n negatives (midranks ``ty``)
    and pooled midranks ``tz``:

    .. math::
        \\widehat{AUC} = \\frac{\\sum_{i \\le m} tz_i}{mn}
                         - \\frac{m+1}{2n}

    Structural components: ``v01 = (tz[:m] - tx) / n`` and
    ``v10 = 1 - (tz[m:] - ty) / m``; then
    ``cov = S01/m + S10/n`` with ``S01``/``S10`` the empirical
    covariance matrices across scorers (DeLong et al. 1988, eq. 6).

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
    """
    y_true = np.asarray(y_true)
    scores = np.atleast_2d(np.asarray(scores, dtype=float))

    if scores.shape[1] != y_true.shape[0]:
        raise ValueError(
            f"scores has {scores.shape[1]} columns but y_true has "
            f"{y_true.shape[0]} samples"
        )
    unique_labels = np.unique(y_true)
    if not np.isin(unique_labels, [0, 1]).all():
        raise ValueError(
            f"y_true must be binary (0/1); got values {unique_labels}"
        )
    if len(unique_labels) < 2:
        raise ValueError("y_true must contain both classes (0 and 1)")

    pos_mask = y_true == 1
    positive_scores = scores[:, pos_mask]
    negative_scores = scores[:, ~pos_mask]
    m = positive_scores.shape[1]
    n = negative_scores.shape[1]
    k = scores.shape[0]

    tx = np.empty((k, m), dtype=float)
    ty = np.empty((k, n), dtype=float)
    tz = np.empty((k, m + n), dtype=float)
    for r in range(k):
        tx[r, :] = compute_midrank(positive_scores[r, :])
        ty[r, :] = compute_midrank(negative_scores[r, :])
        tz[r, :] = compute_midrank(
            np.concatenate([positive_scores[r, :], negative_scores[r, :]])
        )

    aucs = tz[:, :m].sum(axis=1) / (m * n) - (m + 1.0) / (2.0 * n)
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m

    s01 = np.atleast_2d(np.cov(v01, ddof=1))
    s10 = np.atleast_2d(np.cov(v10, ddof=1))
    cov = s01 / m + s10 / n

    return aucs, cov

# EOF
