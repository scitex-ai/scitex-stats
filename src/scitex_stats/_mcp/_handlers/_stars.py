#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_stars.py

"""P-value to stars conversion handler."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from numbers import Real

__all__ = ["p_to_stars_handler"]


def _is_probability(value):
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and 0 <= value <= 1
        and isfinite(value)
    )


def _validated_thresholds(p_value, thresholds):
    """Validate the probability and the three fixed star-level thresholds."""
    if not _is_probability(p_value):
        raise ValueError("p_value must be a finite number between 0 and 1")
    values = [0.001, 0.01, 0.05] if thresholds is None else thresholds
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError("thresholds must contain exactly three finite numbers")
    if not all(_is_probability(value) for value in values):
        raise ValueError("thresholds must be finite numbers between 0 and 1")
    if not values[0] < values[1] < values[2]:
        raise ValueError("thresholds must be strictly increasing")
    return values


async def p_to_stars_handler(
    p_value: float,
    thresholds: list[float] | None = None,
) -> dict:
    """Convert p-value to significance stars."""
    try:
        thresh = _validated_thresholds(p_value, thresholds)

        if p_value < thresh[0]:
            stars = "***"
            significance = f"p < {thresh[0]}"
        elif p_value < thresh[1]:
            stars = "**"
            significance = f"p < {thresh[1]}"
        elif p_value < thresh[2]:
            stars = "*"
            significance = f"p < {thresh[2]}"
        else:
            stars = "ns"
            significance = f"p >= {thresh[2]} (not significant)"

        return {
            "success": True,
            "p_value": p_value,
            "stars": stars,
            "significance": significance,
            "thresholds": thresh,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
