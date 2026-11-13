"""MCP adapter for the public synchronous effect-size operation."""

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
    """Delegate calculation; reject unsupported pooling before scheduling work."""
    if pooled is not True:
        return {
            "success": False,
            "error": "pooled=False is not supported; choose an explicit effect-size measure",
        }
    try:
        from scitex_stats import effect_size

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: effect_size(group1=group1, group2=group2, measure=measure, pooled=pooled),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
