"""Normality transport adapter; numerical behavior belongs to the native API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

__all__ = ["normality_test_handler"]


async def normality_test_handler(data: list[float], method: str = "shapiro") -> dict:
    """Call the native API and report errors as unsuccessful MCP responses."""
    try:
        from scitex_stats import normality_test

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, partial(normality_test, data, method=method)
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as error:
        return {"success": False, "error": str(error)}
