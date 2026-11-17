"""Post-hoc transport adapter backed by the native leaf API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

__all__ = ["posthoc_test_handler"]


async def posthoc_test_handler(
    groups: list[list[float]],
    group_names: list[str] | None = None,
    method: str = "tukey",
    control_group: int = 0,
) -> dict:
    """Call native post-hoc dispatch and preserve the MCP response envelope."""
    try:
        from scitex_stats import posthoc_test

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(posthoc_test, groups, group_names=group_names,
                    method=method, control_group=control_group),
        )
        return {"success": True, **result, "timestamp": datetime.now().isoformat()}
    except Exception as error:
        return {"success": False, "error": str(error)}


def _tukey_hsd(group_arrays, names):
    """Forward the private compatibility entry point to the native expert."""
    from scitex_stats.posthoc._posthoc_test import _tukey_hsd as native

    return native(group_arrays, names)


def _dunnett(group_arrays, names, control_group):
    """Forward the private compatibility entry point to the native expert."""
    from scitex_stats.posthoc._posthoc_test import _dunnett as native

    return native(group_arrays, names, control_group)


def _games_howell(group_arrays, names):
    """Forward the private compatibility entry point to the native expert."""
    from scitex_stats.posthoc._posthoc_test import _games_howell as native

    return native(group_arrays, names)


def _dunn(group_arrays, names):
    """Forward the private compatibility entry point to the native expert."""
    from scitex_stats.posthoc._posthoc_test import _dunn as native

    return native(group_arrays, names)
