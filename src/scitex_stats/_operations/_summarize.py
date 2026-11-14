"""Dictionary summary operation shared by synchronous Python and MCP."""

from __future__ import annotations

import numpy as np

__all__ = ["summarize"]


def summarize(data: list[float], percentiles: list[float] | None = None) -> dict:
    """Summarize a numeric sample as a dictionary without transport metadata.

    Remove NaN values; reject empty cleaned samples and infinities with
    ValueError. Use sample standard deviation/variance (ddof=1), with zero
    std/var/SEM for a singleton. Percentiles default to 25/50/75 when None or
    an empty list is supplied; fractional labels are retained. SciPy adds
    skewness and excess kurtosis when available; constant/singleton moments
    can be NaN. Computation exceptions propagate to direct Python callers.

    This differs from describe, which returns axis-aware stacked statistics
    and their names. MCP describe adds success/timestamp or an error envelope.
    """
    arr = np.array(data, dtype=float)
    arr = arr[~np.isnan(arr)]  # Remove NaN

    if len(arr) == 0:
        raise ValueError("No valid data points")

    if not np.all(np.isfinite(arr)):
        raise ValueError("Data must contain only finite values after removing NaN")

    percs = percentiles or [25, 50, 75]
    percentile_values = np.percentile(arr, percs)

    result = {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "var": float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "sem": (
            float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
            if len(arr) > 1
            else 0.0
        ),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "range": float(np.max(arr) - np.min(arr)),
        "median": float(np.median(arr)),
        "percentiles": {
            (str(int(p)) if float(p).is_integer() else str(float(p))): float(v)
            for p, v in zip(percs, percentile_values)
        },
        "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
    }

    # Add skewness and kurtosis if scipy available
    try:
        from scipy import stats as scipy_stats

        result["skewness"] = float(scipy_stats.skew(arr))
        result["kurtosis"] = float(scipy_stats.kurtosis(arr))
    except ImportError:
        pass

    return result
