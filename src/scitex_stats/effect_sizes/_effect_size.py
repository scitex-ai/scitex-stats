#!/usr/bin/env python3
# File: src/scitex_stats/effect_sizes/_effect_size.py

"""Measure-dispatched two-group effect size with interpretation."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from ._cliffs_delta import cliffs_delta, interpret_cliffs_delta
from ._cohens_d import cohens_d, interpret_cohens_d

__all__ = ["effect_size"]

_STANDARDIZED = ("cohens_d", "hedges_g", "glass_delta")


def effect_size(
    group1: Sequence[float],
    group2: Sequence[float],
    measure: str = "cohens_d",
) -> dict:
    """Effect size of `group1` versus `group2` under one named measure.

    Parameters
    ----------
    group1, group2
        The two samples.
    measure
        ``"cohens_d"``, ``"hedges_g"`` (small-sample corrected d),
        ``"glass_delta"`` (difference over `group2`'s SD) or
        ``"cliffs_delta"`` (ordinal). Anything else raises ``ValueError``.

    Returns
    -------
    dict
        JSON-native: ``group1_n``, ``group2_n``, ``measure`` (display name),
        ``value`` and ``interpretation``; the three standardized-difference
        measures add an approximate 95% ``ci_lower`` / ``ci_upper``.
    """
    g1 = np.array(group1, dtype=float)
    g2 = np.array(group2, dtype=float)
    n1, n2 = len(g1), len(g2)

    if measure == "cohens_d":
        d = cohens_d(g1, g2)
        result = {
            "measure": "Cohen's d",
            "value": float(d),
            "interpretation": interpret_cohens_d(d),
        }
    elif measure == "hedges_g":
        g = cohens_d(g1, g2) * (1 - (3 / (4 * (n1 + n2) - 9)))
        result = {
            "measure": "Hedges' g",
            "value": float(g),
            "interpretation": interpret_cohens_d(g),  # same thresholds
        }
    elif measure == "glass_delta":
        delta = (np.mean(g1) - np.mean(g2)) / np.std(g2, ddof=1)
        result = {
            "measure": "Glass's delta",
            "value": float(delta),
            "interpretation": interpret_cohens_d(delta),
        }
    elif measure == "cliffs_delta":
        delta = cliffs_delta(g1, g2)
        result = {
            "measure": "Cliff's delta",
            "value": float(delta),
            "interpretation": interpret_cliffs_delta(delta),
        }
    else:
        raise ValueError(f"Unknown measure: {measure}")

    if measure in _STANDARDIZED:
        se = np.sqrt((n1 + n2) / (n1 * n2) + result["value"] ** 2 / (2 * (n1 + n2)))
        result["ci_lower"] = float(result["value"] - 1.96 * se)
        result["ci_upper"] = float(result["value"] + 1.96 * se)

    return {"group1_n": n1, "group2_n": n2, **result}


# EOF
