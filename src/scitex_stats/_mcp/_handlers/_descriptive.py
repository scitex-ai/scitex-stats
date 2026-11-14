#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_descriptive.py

"""Descriptive statistics handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["describe_handler"]


async def describe_handler(
    data: list[float],
    percentiles: list[float] | None = None,
) -> dict:
    """Calculate descriptive statistics for data."""
    try:
        loop = asyncio.get_event_loop()

        from scitex_stats import summarize

        def do_describe():
            return summarize(data=data, percentiles=percentiles)

        result = await loop.run_in_executor(None, do_describe)

        return {
            "success": True,
            **result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
