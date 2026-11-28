#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_power.py

"""Power analysis handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["power_analysis_handler"]


async def power_analysis_handler(
    test_type: str = "ttest",
    effect_size: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    n: int | None = None,
    n_groups: int = 2,
    ratio: float = 1.0,
) -> dict:
    """MCP shape over :func:`scitex_stats.power_analysis`; never raises."""
    try:
        from scitex_stats.power import power_analysis

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: power_analysis(
                test_type=test_type,
                effect_size=effect_size,
                alpha=alpha,
                power=power,
                n=n,
                n_groups=n_groups,
                ratio=ratio,
            ),
        )
        return {
            "success": True,
            **result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
