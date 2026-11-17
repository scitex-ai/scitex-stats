"""P-value correction adapter; numerical behavior belongs to the native API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

__all__ = ["correct_pvalues_handler"]


async def correct_pvalues_handler(
    pvalues: list[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> dict:
    """Return explicit failures for unusable p-values or alpha."""
    try:
        from scitex_stats import correct_pvalues

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(correct_pvalues, pvalues, method=method, alpha=alpha),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as error:
        return {"success": False, "error": str(error)}


def _correct_without_statsmodels(
    pvalues: list[float], method: str, alpha: float
) -> dict:
    """Retain the backend-free adapter used by existing reference checks."""
    from scitex_stats.correct._correct_pvalues import _correct_pvalues

    result = _correct_pvalues(pvalues, method, alpha, use_statsmodels=False)
    return {"success": True, **result, "timestamp": datetime.now().isoformat()}
