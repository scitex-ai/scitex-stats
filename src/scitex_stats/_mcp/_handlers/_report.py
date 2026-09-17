#!/usr/bin/env python3
# File: src/scitex_stats/_mcp/_handlers/_report.py

"""MCP handler: bundled statistical report (PDF + HTML + Markdown)."""

from __future__ import annotations

import asyncio

__all__ = ["generate_report_handler"]


async def generate_report_handler(
    data: list | dict | None = None,
    data_file: str | None = None,
    output: str = "report.pdf",
    design: str = "between",
    group_names: list | None = None,
    alpha: float = 0.05,
    posthoc: str = "auto",
    formats: list | None = None,
    title: str = "Statistical report",
) -> dict:
    """Run :func:`scitex_stats.report` off the event loop; never raises."""
    try:
        if (data is None) == (data_file is None):
            raise ValueError("Provide exactly one of 'data' or 'data_file'")
        from scitex_stats.reporting._pdf import report

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: report(
                data if data is not None else data_file, design, output, formats=formats,
                group_names=group_names, alpha=alpha, posthoc=posthoc, title=title,
            ),
        )
        return {"success": True, "paths": result["paths"], "sections": result["sections"], "summary": result["summary"]}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


# EOF
