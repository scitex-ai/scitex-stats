#!/usr/bin/env python3
# File: src/scitex_stats/tests/normality/_normality_test.py

"""Method-dispatched one-sample normality test with interpretation."""

from __future__ import annotations

from typing import Sequence

import numpy as np

__all__ = ["normality_test"]


def normality_test(data: Sequence[float], method: str = "shapiro") -> dict:
    """Test whether `data` is drawn from a normal distribution.

    Parameters
    ----------
    data
        One sample; NaNs are dropped. At least 3 values are required
        (8 for ``"dagostino"``).
    method
        ``"shapiro"`` (Shapiro-Wilk), ``"dagostino"`` (D'Agostino-Pearson),
        ``"anderson"`` (Anderson-Darling at the 5% level) or
        ``"lilliefors"`` (needs statsmodels).

    Returns
    -------
    dict
        JSON-native: ``method``, ``n`` (input length), ``test``,
        ``statistic``, ``statistic_name`` and either ``p_value`` with
        ``is_normal`` / ``interpretation`` (alpha 0.05) or, for Anderson,
        ``critical_value_5pct`` and ``normal``.

    Raises
    ------
    ValueError
        Too few values, or an unknown `method`.
    ImportError
        ``"lilliefors"`` without statsmodels installed.
    """
    from scipy import stats as scipy_stats

    arr = np.array(data, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 3:
        raise ValueError("Need at least 3 data points")

    if method == "shapiro":
        stat, p_value = scipy_stats.shapiro(arr)
        result = {
            "test": "Shapiro-Wilk",
            "statistic": float(stat),
            "statistic_name": "W",
            "p_value": float(p_value),
        }
    elif method == "dagostino":
        if len(arr) < 8:
            raise ValueError("D'Agostino test requires at least 8 samples")
        stat, p_value = scipy_stats.normaltest(arr)
        result = {
            "test": "D'Agostino-Pearson",
            "statistic": float(stat),
            "statistic_name": "K2",
            "p_value": float(p_value),
        }
    elif method == "anderson":
        res = scipy_stats.anderson(arr, dist="norm")
        idx = 2  # the 5% significance level
        result = {
            "test": "Anderson-Darling",
            "statistic": float(res.statistic),
            "statistic_name": "A2",
            "critical_value_5pct": float(res.critical_values[idx]),
            "normal": bool(res.statistic < res.critical_values[idx]),
        }
    elif method == "lilliefors":
        try:
            from statsmodels.stats.diagnostic import lilliefors
        except ImportError as exc:
            raise ImportError("statsmodels required for Lilliefors test") from exc
        stat, p_value = lilliefors(arr, dist="norm")
        result = {
            "test": "Lilliefors",
            "statistic": float(stat),
            "statistic_name": "D",
            "p_value": float(p_value),
        }
    else:
        raise ValueError(f"Unknown method: {method}")

    if "p_value" in result:
        result["is_normal"] = result["p_value"] >= 0.05
        result["interpretation"] = (
            "Data appears normally distributed (p >= 0.05)"
            if result["is_normal"]
            else "Data deviates from normal distribution (p < 0.05)"
        )
    return {"method": method, "n": len(data), **result}


# EOF
