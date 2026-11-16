"""Synchronous effect-size dispatch shared by Python and MCP."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from ._cliffs_delta import cliffs_delta, interpret_cliffs_delta
from ._cohens_d import cohens_d, interpret_cohens_d

__all__ = ["effect_size"]


def _numeric_group(values: ArrayLike, name: str, minimum: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < minimum or not np.isfinite(array).all():
        raise ValueError(
            f"{name} must be a one-dimensional finite numeric group with "
            f"at least {minimum} observation(s)"
        )
    return array


def effect_size(
    group1: ArrayLike,
    group2: ArrayLike,
    measure: str = "cohens_d",
    pooled: bool = True,
) -> dict:
    """Calculate a two-group effect size as native Python data.

    Measures are ``cohens_d``, ``hedges_g``, ``glass_delta`` (group2 is
    the control), and ``cliffs_delta``. Inputs must be finite 1-D arrays.
    Cohen/Hedges require two observations per group; Glass requires one
    treatment and two control observations; Cliff requires one per group.

    ``pooled=False`` is not implemented for Cohen/Hedges and raises instead
    of silently returning a pooled calculation. Pooling does not apply to
    Glass/Cliff. Parametric results retain the existing normal-approximation
    95% interval; Cliff results have no interval. Undefined effects raise.
    The returned dict contains group counts, measure, value, interpretation
    and applicable interval bounds, without transport status or timestamps.
    """
    labels = {
        "cohens_d": "Cohen's d",
        "hedges_g": "Hedges' g",
        "glass_delta": "Glass's delta",
        "cliffs_delta": "Cliff's delta",
    }
    if measure not in labels:
        raise ValueError(f"Unknown measure: {measure}")
    if measure in ("cohens_d", "hedges_g") and not pooled:
        raise ValueError(f"pooled=False is not implemented for {measure}")
    first_minimum = 2 if measure in ("cohens_d", "hedges_g") else 1
    second_minimum = 1 if measure == "cliffs_delta" else 2
    first = _numeric_group(group1, "group1", first_minimum)
    second = _numeric_group(group2, "group2", second_minimum)
    if measure == "cliffs_delta":
        value = float(cliffs_delta(first, second))
        interpretation = interpret_cliffs_delta(value)
    else:
        correction = {"cohens_d": None, "hedges_g": "hedges", "glass_delta": "glass"}[measure]
        value = float(cohens_d(first, second, correction=correction))
        interpretation = interpret_cohens_d(value)
    if not np.isfinite(value):
        raise ValueError("Effect size is undefined for the supplied groups")
    n1, n2 = len(first), len(second)
    result = {
        "group1_n": n1, "group2_n": n2,
        "measure": labels[measure], "value": value,
        "interpretation": interpretation,
    }
    if measure != "cliffs_delta":
        # Preserve the pre-existing MCP interval approximation.
        se = np.sqrt((n1 + n2) / (n1 * n2) + value ** 2 / (2 * (n1 + n2)))
        result["ci_lower"] = float(value - 1.96 * se)
        result["ci_upper"] = float(value + 1.96 * se)
    return result
