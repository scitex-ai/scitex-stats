#!/usr/bin/env python3
"""Tests for scitex_stats.app_info — the read-only app-identity descriptor.

Contract (compass §12, Stats Calculator items #207-#209): the hub's
Apps-list code imports ONE descriptor instead of scraping pyproject.toml /
_server.py / README. This suite pins that surface and, critically, proves
it does NOT encode Hub placement decisions (standalone vs under-Tools is
the hub's call, not the package's).
"""

from __future__ import annotations

import asyncio

import pytest

import scitex_stats as ss

_EXPECTED_KEYS = {
    "name",
    "display_name",
    "display_name_alt",
    "description",
    "capabilities",
    "mcp_server",
    "tools",
    "version",
}

_EXPECTED_CAPABILITIES = (
    "descriptive",
    "tests",
    "effect-size",
    "power",
    "post-hoc",
    "corrections",
)


def test_app_info_importable_and_callable():
    # Arrange
    # Act
    assert callable(ss.app_info)
    info = ss.app_info()
    # Assert
    assert isinstance(info, dict)


def test_app_info_key_set_exact():
    # Arrange
    # Act
    info = ss.app_info()
    # Assert
    assert set(info.keys()) == _EXPECTED_KEYS


def test_app_info_name_and_version():
    # Arrange
    # Act
    info = ss.app_info()
    # Assert
    assert info["name"] == "scitex-stats"
    assert isinstance(info["version"], str)
    assert info["version"]
    assert info["version"] == ss.__version__


def test_app_info_display_names_compass():
    # Arrange — the two compass-sanctioned Apps-list spellings
    # Act
    info = ss.app_info()
    # Assert
    assert info["display_name"] == "Statistics"
    assert info["display_name_alt"] == "Stats Calculator"


def test_app_info_capabilities_six_in_order():
    # Arrange
    # Act
    info = ss.app_info()
    # Assert
    assert tuple(info["capabilities"]) == _EXPECTED_CAPABILITIES


def test_app_info_does_not_encode_hub_placement_decisions():
    """#207/#208 are the hub's call — the descriptor must not decide them.

    Guards the 'do not encode Hub placement decisions' requirement: no
    standalone/placement/under-tools flag may leak into the identity.
    """
    # Arrange
    # Act
    info = ss.app_info()
    # Assert
    forbidden = {
        "placement",
        "standalone",
        "is_standalone",
        "under_tools",
        "app_placement",
        "self_contained",
        "is_self_contained",
    }
    leaked = forbidden & set(info.keys())
    assert not leaked, f"descriptor leaked hub placement decisions: {leaked}"
    # And no key merely hints at it by name.
    assert not any("placement" in k for k in info)


def test_app_info_tools_tuple():
    # Arrange
    # Act
    info = ss.app_info()
    # Assert
    tools = info["tools"]
    assert isinstance(tools, tuple)
    assert len(tools) >= 1
    # All tool names are valid identifiers.
    for t in tools:
        assert isinstance(t, str) and t.isidentifier()


# ---------------------------------------------------------------------------
# Drift guards vs the live FastMCP server — description, mcp_server name,
# and the tool list must track scitex_stats._server (no manual re-sync).
# ---------------------------------------------------------------------------
def _live_tool_names() -> set:
    from scitex_stats._server import mcp

    async def _run():
        res = await mcp.list_tools()
        return res

    res = asyncio.run(_run())
    return {getattr(t, "name", str(t)) for t in res}


def test_app_info_description_matches_live_mcp_server():
    # Arrange
    from scitex_stats._server import mcp
    # Act
    info = ss.app_info()
    # Assert
    assert info["description"] == mcp.instructions
    assert isinstance(info["description"], str)
    assert info["description"].strip()


def test_app_info_mcp_server_name_matches_live():
    # Arrange
    from scitex_stats._server import mcp
    # Act
    info = ss.app_info()
    # Assert
    assert info["mcp_server"] == mcp.name
    assert info["mcp_server"] == "scitex-stats"


def test_app_info_tools_match_live_mcp_server():
    # Arrange
    # Act
    info = ss.app_info()
    live = _live_tool_names()
    # Assert
    assert set(info["tools"]) == live, (
        f"descriptor tools out of sync with _server. "
        f"missing={live - set(info['tools'])} extra={set(info['tools']) - live}"
    )


# EOF
