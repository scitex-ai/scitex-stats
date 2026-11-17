"""Synchronous p-value adjustment shared by Python and MCP."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

__all__ = ["correct_pvalues"]


def correct_pvalues(
    pvalues: ArrayLike, method: str = "fdr_bh", alpha: float = 0.05
) -> dict:
    """Adjust a non-empty 1-D sequence of finite p-values in [0, 1].

    Alpha must be a finite scalar in [0, 1]. Supported methods are
    bonferroni, holm, fdr_bh, fdr_by and sidak. For compatibility with the
    existing MCP operation, unknown method names use fdr_bh; ``method``
    retains the request and ``method_used`` names the actual calculation.
    Invalid inputs raise ValueError before either backend runs. Results are
    native data without transport success/timestamp fields. The retained
    NumPy fallback is used when statsmodels raises ImportError.
    """
    return _correct_pvalues(pvalues, method, alpha, use_statsmodels=True)


def _correct_pvalues(pvalues, method, alpha, *, use_statsmodels):
    """Shared native path, including the retained backend-free adapter."""
    values = np.asarray(pvalues, dtype=float)
    if (
        values.ndim != 1
        or values.size == 0
        or not np.isfinite(values).all()
        or np.any(values < 0)
        or np.any(values > 1)
    ):
        raise ValueError(
            "pvalues must be a non-empty one-dimensional finite array in [0, 1]"
        )
    level = np.asarray(alpha, dtype=float)
    if level.ndim != 0 or not np.isfinite(level) or not 0 <= level <= 1:
        raise ValueError("alpha must be a finite scalar in [0, 1]")
    level = float(level)
    methods = ("bonferroni", "holm", "fdr_bh", "fdr_by", "sidak")
    method_used = method if method in methods else "fdr_bh"
    corrected = None
    if use_statsmodels:
        try:
            from statsmodels.stats.multitest import multipletests

            reject, corrected, _, _ = multipletests(
                values, alpha=level, method=method_used
            )
        except ImportError:
            pass
    if corrected is None:
        corrected = _adjust_without_statsmodels(values, method_used)
        reject = corrected <= level
    return {
        "method": method,
        "method_used": method_used,
        "alpha": level,
        "original_pvalues": values.tolist(),
        "corrected_pvalues": corrected.tolist(),
        "reject_null": reject.tolist(),
        "n_significant": int(reject.sum()),
        "n_tests": len(values),
    }


def _adjust_without_statsmodels(pvals: np.ndarray, correct_method: str) -> np.ndarray:
    """Retain the existing NumPy calculations on already validated values."""
    n = len(pvals)
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
    elif correct_method == "sidak":
        corrected = np.ones(n, dtype=float)
        not_one = pvals != 1.0
        corrected[not_one] = -np.expm1(n * np.log1p(-pvals[not_one]))
    else:
        raise ValueError(f"Unsupported correction method: {correct_method}")

    return corrected
