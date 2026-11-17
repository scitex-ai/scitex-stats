#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_format.py

"""Results formatting handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["format_results_handler"]


async def format_results_handler(
    test_name: str,
    statistic: float,
    p_value: float,
    df: float | None = None,
    effect_size: float | None = None,
    effect_size_name: str | None = None,
    style: str = "apa",
    ci_lower: float | None = None,
    ci_upper: float | None = None,
) -> dict:
    """Format statistical results in journal style."""
    try:
        loop = asyncio.get_event_loop()

        from scitex_stats.auto._format_results import format_results

        result = await loop.run_in_executor(
            None,
            lambda: format_results(
                test_name=test_name,
                statistic=statistic,
                p_value=p_value,
                df=df,
                effect_size=effect_size,
                effect_size_name=effect_size_name,
                style=style,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
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
