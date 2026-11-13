"""MCP adapter for the public synchronous p-value correction operation."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["correct_pvalues_handler"]


async def correct_pvalues_handler(
    pvalues: list[float], method: str = "fdr_bh", alpha: float = 0.05,
) -> dict:
    """Run the owning Python operation off the event loop."""
    try:
        from scitex_stats import correct_pvalues

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: correct_pvalues(pvalues=pvalues, method=method, alpha=alpha),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _correct_without_statsmodels(pvalues: list[float], method: str, alpha: float) -> dict:
    """Preserve the private adapter entry point for the NumPy-only operation."""
    from scitex_stats._correction import _correct_pvalues_numpy

    result = _correct_pvalues_numpy(pvalues, method, alpha)
    return {"success": True, **result, "timestamp": datetime.now().isoformat()}
