#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_corrections.py

"""P-value correction handler for multiple comparisons."""

from __future__ import annotations

import asyncio
from datetime import datetime

__all__ = ["correct_pvalues_handler"]


async def correct_pvalues_handler(
    pvalues: list[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> dict:
    """MCP shape over :func:`scitex_stats.correct_pvalues`; never raises."""
    try:
        from scitex_stats.correct import correct_pvalues

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: correct_pvalues(pvalues, method=method, alpha=alpha)
        )
        return {
            "success": True,
            **result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
