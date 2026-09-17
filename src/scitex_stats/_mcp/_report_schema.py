#!/usr/bin/env python3
# File: src/scitex_stats/_mcp/_report_schema.py

"""Schema of the ``generate_report`` MCP tool."""

from __future__ import annotations

import mcp.types as types

__all__ = ["report_tool_schema"]


def report_tool_schema() -> types.Tool:
    return types.Tool(
        name="generate_report",
        description=(
            "Write one bundled statistical report (PDF plus HTML and Markdown) for "
            "2+ groups: data summary with exclusions, assumption checks, applicability "
            "table and rule-based primary test, APA result, sensitivity analyses with "
            "agreement, automatic post-hoc (Tukey/Games–Howell, Dunn–Holm, Nemenyi), "
            "figure with brackets, a methods paragraph and references."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "object", "description": "Group name -> list of numbers (or pass data_file)"},
                "data_file": {"type": "string", "description": "CSV/TSV, one column per group"},
                "output": {"type": "string", "default": "report.pdf"},
                "design": {"type": "string", "enum": ["between", "within", "paired"], "default": "between"},
                "group_names": {"type": "array", "items": {"type": "string"}},
                "alpha": {"type": "number", "default": 0.05},
                "posthoc": {"type": "string", "enum": ["auto", "always", "never"], "default": "auto"},
                "formats": {"type": "array", "items": {"type": "string", "enum": ["pdf", "html", "md"]}},
                "title": {"type": "string", "default": "Statistical report"},
            },
        },
    )


# EOF
