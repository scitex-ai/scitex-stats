#!/usr/bin/env python3
# File: scitex_stats/_utils/_group_descriptives.py
"""Per-group n, M, SD, Mdn and IQR for the data a test was run on."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

_PAIRED = {"ttest_rel", "ttest_paired", "wilcoxon", "pearson", "spearman", "kendall"}
_NO_DATA = {"chi2", "fisher"}


def describe(values: Any, name: str) -> Dict[str, Any]:
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    n = int(len(x))
    q1, q3 = (np.percentile(x, [25, 75]) if n else (np.nan, np.nan))
    return {
        "name": name,
        "n": n,
        "mean": float(np.mean(x)) if n else None,
        "sd": float(np.std(x, ddof=1)) if n > 1 else None,
        "median": float(np.median(x)) if n else None,
        "iqr": float(q3 - q1) if n else None,
    }


def group_descriptives(
    test_name: str,
    data: Any,
    data2: Any,
    groups: Optional[List[Any]],
    result: Dict[str, Any],
    names: Optional[List[str]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Descriptives per group, after the same NaN handling the test applies."""
    if test_name in _NO_DATA:
        return None
    arrays = [g for g in (groups if groups is not None else [data, data2]) if g is not None]
    if not arrays:
        return None
    try:
        arrays = [np.asarray(a, dtype=float).ravel() for a in arrays]
    except (TypeError, ValueError):
        return None
    if test_name in _PAIRED and len(arrays) == 2 and len(arrays[0]) == len(arrays[1]):
        keep = ~(np.isnan(arrays[0]) | np.isnan(arrays[1]))
        arrays = [a[keep] for a in arrays]
    default = result.get("var_names") or result.get("condition_names")
    if not default:
        default = [result.get(k) for k in ("var_x", "var_y") if result.get(k)]
    labels = list(names or default or [])
    if len(labels) < len(arrays):
        labels = [f"Group {i + 1}" for i in range(len(arrays))]
    return [describe(a, str(labels[i])) for i, a in enumerate(arrays)]


__all__ = ["describe", "group_descriptives"]

# EOF
