#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_posthoc.py

"""Post-hoc test handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["posthoc_test_handler"]


async def posthoc_test_handler(
    groups: list[list[float]],
    group_names: list[str] | None = None,
    method: str = "tukey",
    control_group: int = 0,
) -> dict:
    """MCP shape over :func:`scitex_stats.posthoc_test`; never raises."""
    try:
        from scitex_stats.posthoc import posthoc_test

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: posthoc_test(
                groups,
                group_names=group_names,
                method=method,
                control_group=control_group,
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
