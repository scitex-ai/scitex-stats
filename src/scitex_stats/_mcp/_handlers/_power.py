#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_power.py

"""Power analysis handler."""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

__all__ = ["power_analysis_handler"]


async def power_analysis_handler(
    test_type: str = "ttest",
    effect_size: float | None = None,
    alpha: float = 0.05,
    power: float = 0.8,
    n: int | None = None,
    n_groups: int = 2,
    ratio: float = 1.0,
) -> dict:
    """Call the native API and retain the existing MCP response envelope."""
    try:
        from scitex_stats import power_analysis

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                power_analysis, test_type=test_type, effect_size=effect_size,
                alpha=alpha, power=power, n=n, n_groups=n_groups, ratio=ratio,
            ),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as error:
        return {"success": False, "error": str(error)}


def _power_anova(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
    n_groups: int,
) -> dict:
    """Delegate to the leaf-owned bounded power calculation."""
    from scitex_stats.power._omnibus import _power_anova as native

    return native(effect_size, alpha, power, n, n_groups)


def _power_correlation(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
) -> dict:
    """Delegate to the native correlation-power implementation."""
    from scitex_stats.power._power_analysis import _power_correlation as native

    return native(effect_size, alpha, power, n)


def _power_chi2(
    effect_size: float | None,
    alpha: float,
    power: float,
    n: int | None,
    n_groups: int,
) -> dict:
    """Delegate to the leaf-owned bounded power calculation."""
    from scitex_stats.power._omnibus import _power_chi2 as native

    return native(effect_size, alpha, power, n, n_groups)


# EOF
