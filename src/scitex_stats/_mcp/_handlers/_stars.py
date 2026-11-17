#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_stars.py

"""P-value to stars conversion handler."""

from __future__ import annotations

from datetime import datetime
from math import isfinite

__all__ = ["p_to_stars_handler"]


async def p_to_stars_handler(
    p_value: float,
    thresholds: list[float] | None = None,
) -> dict:
    """Convert a finite probability in [0, 1] to significance stars."""
    try:
        if not isfinite(p_value) or not 0 <= p_value <= 1:
            raise ValueError("p_value must be a finite probability between 0 and 1")
        thresh = [0.001, 0.01, 0.05] if thresholds is None else thresholds
        if (
            len(thresh) != 3
            or not all(isfinite(value) and 0 < value <= 1 for value in thresh)
            or not thresh[0] < thresh[1] < thresh[2]
        ):
            raise ValueError(
                "thresholds must contain exactly three strictly increasing "
                "finite probabilities in (0, 1]"
            )

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
