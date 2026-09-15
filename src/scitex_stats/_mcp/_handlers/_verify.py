#!/usr/bin/env python3
# File: src/scitex_stats/_mcp/_handlers/_verify.py

"""MCP handler: verify a result against its provenance receipt."""

from __future__ import annotations

import asyncio

__all__ = ["verify_result_handler"]


async def verify_result_handler(
    result: dict | None = None,
    result_file: str | None = None,
    data: list | None = None,
    data2: list | None = None,
    groups: list | None = None,
) -> dict:
    """Run :func:`scitex_stats.verify` off the event loop; never raises."""
    try:
        if (result is None) == (result_file is None):
            raise ValueError("Provide exactly one of 'result' or 'result_file'")
        from scitex_stats._verify import verify

        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None,
            lambda: verify(result if result is not None else result_file, data, data2, groups),
        )
        return {"success": True, **report}
    except Exception as e:
        return {"success": False, "error": str(e)}


# EOF
