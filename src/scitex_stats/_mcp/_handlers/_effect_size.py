"""Effect-size transport adapter; numerical behavior belongs to effect_sizes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

__all__ = ["effect_size_handler"]


async def effect_size_handler(
    group1: list[float],
    group2: list[float],
    measure: str = "cohens_d",
    pooled: bool = True,
) -> dict:
    """Call the native API and retain the MCP result/error envelope."""
    try:
        from scitex_stats import effect_size

        loop = asyncio.get_event_loop()
        operation = partial(effect_size, group1, group2, measure=measure, pooled=pooled)
        result = await loop.run_in_executor(None, operation)
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as error:
        return {"success": False, "error": str(error)}
