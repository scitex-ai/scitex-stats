#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_normality.py

"""Normality test handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["normality_test_handler"]


async def normality_test_handler(
    data: list[float],
    method: str = "shapiro",
) -> dict:
    """MCP shape over :func:`scitex_stats.normality_test`; never raises."""
    try:
        from scitex_stats.tests.normality._normality_test import normality_test

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: normality_test(data, method=method)
        )
        return {
            "success": True,
            **result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
