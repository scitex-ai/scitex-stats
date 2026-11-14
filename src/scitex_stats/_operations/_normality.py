"""Synchronous normality testing shared by Python and MCP."""

from __future__ import annotations

import numpy as np

__all__ = ["normality_test"]


class _NormalityInputError(ValueError):
    """A method's sample requirement was not met."""


class _NormalityDependencyError(ImportError):
    """An optional backend required by the selected method is unavailable."""


def normality_test(data: list[float], method: str = "shapiro") -> dict:
    """Test normality with Shapiro, D'Agostino, Anderson or Lilliefors.

    NaN observations are omitted from calculations. ``n`` counts input values,
    including NaNs. At least three valid observations are required; D'Agostino
    requires eight. Unsupported methods and insufficient samples raise
    ``ValueError``. Lilliefors requires statsmodels and raises ``ImportError``
    when unavailable. Return native statistics and interpretation fields;
    transport status and timestamps belong to the caller.
    """
    n = len(data)
    from scipy import stats as scipy_stats

    arr = np.array(data, dtype=float)
    arr = arr[~np.isnan(arr)]

    if len(arr) < 3:
        raise _NormalityInputError("Need at least 3 data points")

    result = {}

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
            raise _NormalityInputError("D'Agostino test requires at least 8 samples")
        stat, p_value = scipy_stats.normaltest(arr)
        result = {
            "test": "D'Agostino-Pearson",
            "statistic": float(stat),
            "statistic_name": "K2",
            "p_value": float(p_value),
        }

    elif method == "anderson":
        res = scipy_stats.anderson(arr, dist="norm")
        # Use 5% significance level
        idx = 2  # Index for 5% level
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

            stat, p_value = lilliefors(arr, dist="norm")
            result = {
                "test": "Lilliefors",
                "statistic": float(stat),
                "statistic_name": "D",
                "p_value": float(p_value),
            }
        except ImportError as exc:
            raise _NormalityDependencyError("statsmodels required for Lilliefors test") from exc

    else:
        raise ValueError(f"Unknown method: {method}")

    # Add interpretation
    if "p_value" in result:
        result["is_normal"] = result["p_value"] >= 0.05
        result["interpretation"] = (
            "Data appears normally distributed (p >= 0.05)"
            if result["is_normal"]
            else "Data deviates from normal distribution (p < 0.05)"
        )

    return {"method": method, "n": n, **result}
