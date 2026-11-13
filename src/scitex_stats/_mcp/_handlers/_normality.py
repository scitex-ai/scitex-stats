"""MCP adapter for the public synchronous normality operation."""

from __future__ import annotations

import asyncio
from datetime import datetime

from scitex_stats._normality import _NormalityDependencyError, _NormalityInputError

__all__ = ["normality_test_handler"]


async def normality_test_handler(
    data: list[float],
    method: str = "shapiro",
) -> dict:
    """Run the owning Python operation off the event loop."""
    try:
        from scitex_stats import normality_test

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: normality_test(data=data, method=method),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except (_NormalityInputError, _NormalityDependencyError) as exc:
        return {
            "success": False, "method": method, "n": len(data),
            "error": str(exc), "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
