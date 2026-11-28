#!/usr/bin/env python3
# File: src/scitex_stats/correct/_correct_pvalues.py

"""Method-dispatched multiple-comparison correction of a p-value list."""

from __future__ import annotations

from typing import Sequence

import numpy as np

__all__ = ["correct_pvalues"]

_METHODS = ("bonferroni", "fdr_bh", "fdr_by", "holm", "sidak")


def correct_pvalues(
    pvalues: Sequence[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> dict:
    """Correct `pvalues` for multiple comparisons with one named method.

    Parameters
    ----------
    pvalues
        Raw p-values, one per test.
    method
        ``"bonferroni"``, ``"holm"``, ``"sidak"``, ``"fdr_bh"`` or
        ``"fdr_by"``. Any other name falls back to ``"fdr_bh"``; the
        requested name is still echoed as ``method``.
    alpha
        Family-wise (or false-discovery) level for ``reject_null``.

    Returns
    -------
    dict
        JSON-native: ``method``, ``alpha``, ``original_pvalues``,
        ``corrected_pvalues``, ``reject_null``, ``n_significant``,
        ``n_tests``. Uses statsmodels when installed, else an equivalent
        NumPy implementation.
    """
    pvalues = list(pvalues)
    sm_method = method if method in _METHODS else "fdr_bh"
    try:
        # statsmodels imports parts of itself lazily, so an ImportError can
        # surface from the call as well as from the import.
        from statsmodels.stats.multitest import multipletests

        reject, corrected, _, _ = multipletests(
            np.array(pvalues), alpha=alpha, method=sm_method
        )
    except ImportError:
        return _correct_without_statsmodels(pvalues, method, alpha)

    return {
        "method": method,
        "alpha": alpha,
        "original_pvalues": pvalues,
        "corrected_pvalues": corrected.tolist(),
        "reject_null": reject.tolist(),
        "n_significant": int(reject.sum()),
        "n_tests": len(pvalues),
    }


def _correct_without_statsmodels(
    pvalues: list[float], method: str, alpha: float
) -> dict:
    """Apply the retained NumPy-only corrections without importing a backend."""
    n = len(pvalues)
    pvals = np.array(pvalues)

    # Unknown methods fall back to fdr_bh, mirroring the statsmodels path.
    # The requested name is still echoed in the output's "method" field.
    correct_method = method if method in _METHODS else "fdr_bh"

    if correct_method == "bonferroni":
        corrected = np.minimum(pvals * n, 1.0)
    elif correct_method == "holm":
        sorted_idx = np.argsort(pvals)
        corrected = np.empty(n)
        cummax = 0.0
        for rank, idx in enumerate(sorted_idx, start=1):
            adj = min((n - rank + 1) * pvals[idx], 1.0)
            adj = max(adj, cummax)
            corrected[idx] = adj
            cummax = adj
    elif correct_method in ("fdr_bh", "fdr_by"):
        factor = (
            np.sum(1.0 / np.arange(1, n + 1)) if correct_method == "fdr_by" else 1.0
        )
        sorted_idx = np.argsort(pvals)
        corrected = np.empty(n)
        prev = 1.0
        for rank in range(n, 0, -1):
            idx = sorted_idx[rank - 1]
            bh = pvals[idx] * n / rank * factor
            val = min(bh, prev, 1.0)
            corrected[idx] = val
            prev = val
    else:  # sidak
        corrected = np.ones(n, dtype=float)
        not_one = pvals != 1.0
        corrected[not_one] = -np.expm1(n * np.log1p(-pvals[not_one]))

    reject_null = corrected <= alpha
    return {
        "method": method,
        "alpha": alpha,
        "original_pvalues": pvalues,
        "corrected_pvalues": corrected.tolist(),
        "reject_null": reject_null.tolist(),
        "n_significant": int(reject_null.sum()),
        "n_tests": n,
    }


# EOF
