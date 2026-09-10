#!/usr/bin/env python3
# File: scitex_stats/_app_info.py

"""Read-only app-identity descriptor for the hub Statistics app.

A single, dependency-free, *synchronous* surface the hub's Apps-list code
can import instead of scraping three files (``pyproject.toml``,
``_server.py``, README). Everything returned is a fact about the package
itself (name, version, the two compass-sanctioned display names, the
MCP server's own description, the capability list, and the MCP tool list)
— no new product decisions are encoded here.

Deliberately NOT included (kept the hub's call, per compass §12):
  - where the App is placed (standalone vs "under Tools")
  - whether it is treated as a self-contained capability
  - how it renders in the Apps list

Those are product/UI decisions owned by scitex-hub; this module only
supplies the identity the hub needs to make and display them. The
hub is the single consumer, so the display names mirror the two
compass-sanctioned spellings ("Statistics" / "Stats Calculator").
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _pkg_version

# ---------------------------------------------------------------------------
# Compass-sanctioned identity (scitex_ai_ux_product_compass §12 L450,
# §22 Idea 8). The hub is the single consumer of this package.
# ---------------------------------------------------------------------------
_NAME = "scitex-stats"
_DISPLAY_NAME = "Statistics"
_DISPLAY_NAME_ALT = "Stats Calculator"

# The six compass-named statistical capabilities exposed by the package
# (each is a top-level namespace on ``scitex_stats``). Order matches the
# compass: descriptive, tests, effect-size, power, post-hoc, corrections.
_CAPABILITIES = (
    "descriptive",
    "tests",
    "effect-size",
    "power",
    "post-hoc",
    "corrections",
)

# The MCP tool names, as registered in scitex_stats._server (one per
# @mcp.tool()). Kept in sync by TestAppInfoToolsMatchMcpServer (the
# contract test) — add a tool there and the descriptor here together.
_MCP_TOOLS = (
    "recommend_tests",
    "run_test",
    "format_results",
    "power_analysis",
    "correct_pvalues",
    "describe",
    "effect_size",
    "normality_test",
    "posthoc_test",
    "p_to_stars",
    "skills_list",
    "skills_get",
)


def _version() -> str:
    """Package version from installed metadata, falling back to pyproject."""
    try:
        return _pkg_version(_NAME)
    except _PackageNotFoundError:
        # Not installed (e.g. running from a source checkout without an
        # editable install) — read the declared version from pyproject.
        from pathlib import Path as _Path

        _pyproject = _Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        if _pyproject.exists():
            for _line in _pyproject.read_text().splitlines():
                if _line.startswith("version"):
                    return _line.split("=", 1)[1].strip().strip('"')
        return "0.0.0+local"


def app_info() -> dict:
    """Return the read-only app-identity descriptor.

    Synchronous, no new dependencies, safe to call from any context
    (including an async hub app). Returns a fresh dict each call; do not
    mutate it. ``description`` and ``mcp_server`` are read live from the
    installed FastMCP server so they track the MCP surface; the rest are
    stable package facts.

    Keys
    ----
    name : str
        Distribution / entry-point name (``"scitex-stats"``).
    display_name : str
        Primary Apps-list label (compass: "Statistics").
    display_name_alt : str
        Alternate Apps-list label (compass: "Stats Calculator").
    description : str
        The MCP server's own instruction string — a ready display blurb.
    capabilities : tuple[str, ...]
        The six compass-named statistical capabilities.
    mcp_server : str
        The FastMCP server name the hub connects to.
    tools : tuple[str, ...]
        The MCP tool names the server exposes (see _server.py).
    version : str
        Installed package version.
    """
    from scitex_stats._server import mcp  # local import: keeps top-level light

    return {
        "name": _NAME,
        "display_name": _DISPLAY_NAME,
        "display_name_alt": _DISPLAY_NAME_ALT,
        "description": mcp.instructions,
        "capabilities": _CAPABILITIES,
        "mcp_server": mcp.name,
        "tools": _MCP_TOOLS,
        "version": _version(),
    }
