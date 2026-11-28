#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_effect_size.py

"""Effect size calculation handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["effect_size_handler"]


async def effect_size_handler(
    group1: list[float],
    group2: list[float],
    measure: str = "cohens_d",
    pooled: bool = True,
) -> dict:
    """MCP shape over :func:`scitex_stats.effect_size`; never raises.

    ``pooled`` is accepted for backward compatibility of the MCP signature
    and has never changed the result.
    """
    try:
        from scitex_stats.effect_sizes import effect_size

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: effect_size(group1, group2, measure=measure)
        )
        return {
            "success": True,
            **result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
