"""Synchronous normality dispatch shared by the Python and MCP interfaces."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

__all__ = ["normality_test"]


def normality_test(data: ArrayLike, method: str = "shapiro") -> dict:
    """Test a one-dimensional sample, returning native numerical data.

    NaNs are omitted; ``n`` is the number tested, while ``n_input`` and
    ``n_omitted`` retain the input accounting. Infinite, constant, non-1D or
    undersized samples raise ValueError. Shapiro/Anderson require at least
    three usable observations, D'Agostino eight, and Lilliefors four.

    P-value methods use alpha=0.05 for the retained ``is_normal`` heuristic.
    Anderson instead returns a 5% critical value and ``normal`` decision,
    without a p-value. Failure to reject does not establish normality.
    No transport success or timestamp fields are included.
    """
    from scipy import stats

    minimums = {"shapiro": 3, "dagostino": 8, "anderson": 3, "lilliefors": 4}
    if method not in minimums:
        raise ValueError(f"Unknown method: {method}")
    array = np.asarray(data, dtype=float)
    if array.ndim != 1:
        raise ValueError("Data must be one-dimensional")
    n_input = len(array)
    array = array[~np.isnan(array)]
    if not np.isfinite(array).all():
        raise ValueError("Data must contain only finite values after omitting NaNs")
    minimum = minimums[method]
    if len(array) < minimum:
        if method == "dagostino":
            raise ValueError("D'Agostino test requires at least 8 samples")
        if method == "lilliefors":
            raise ValueError("Lilliefors test requires at least 4 samples")
        raise ValueError("Need at least 3 data points after omitting NaNs")
    if np.all(array == array[0]):
        raise ValueError("Normality testing requires non-constant data")
    result = {
        "method": method,
        "n": len(array),
        "n_input": n_input,
        "n_omitted": n_input - len(array),
    }
    if method == "anderson":
        test = stats.anderson(array, dist="norm")
        index = list(test.significance_level).index(5.0)
        result.update(
            test="Anderson-Darling",
            statistic=float(test.statistic),
            statistic_name="A2",
            critical_value_5pct=float(test.critical_values[index]),
            normal=bool(test.statistic < test.critical_values[index]),
        )
    else:
        if method == "shapiro":
            statistic, p_value = stats.shapiro(array)
            label, statistic_name = "Shapiro-Wilk", "W"
        elif method == "dagostino":
            statistic, p_value = stats.normaltest(array)
            label, statistic_name = "D'Agostino-Pearson", "K2"
        else:
            from statsmodels.stats.diagnostic import lilliefors

            statistic, p_value = lilliefors(array, dist="norm")
            label, statistic_name = "Lilliefors", "D"
        if not np.isfinite(p_value):
            raise ValueError("Normality test returned an undefined p-value")
        result.update(
            test=label,
            statistic=float(statistic),
            statistic_name=statistic_name,
            p_value=float(p_value),
            is_normal=bool(p_value >= 0.05),
            interpretation=(
                "Data appears normally distributed (p >= 0.05)"
                if p_value >= 0.05
                else "Data deviates from normal distribution (p < 0.05)"
            ),
        )
    if not np.isfinite(result["statistic"]):
        raise ValueError("Normality test returned an undefined statistic")
    return result
