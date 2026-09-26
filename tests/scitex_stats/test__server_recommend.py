"""MCP tools: check_applicability / recommend_test / run_all_applicable."""

from __future__ import annotations

import asyncio
import json

import pytest

pytest.importorskip("fastmcp")

from scitex_stats import _server  # noqa: E402

SAMPLE = [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]]


def _call(name, **kwargs):
    fn = getattr(_server, name)
    fn = getattr(fn, "fn", fn)
    return json.loads(asyncio.run(fn(**kwargs)))


def test_recommend_test_tool_names_welch():
    # Arrange
    # Act
    out = _call("recommend_test", groups=SAMPLE, design="independent")
    # Assert
    assert out["primary"]["test_id"] == "ttest_welch"


def test_check_applicability_tool_returns_rows():
    # Arrange
    # Act
    out = _call("check_applicability", groups=SAMPLE, design="independent")
    # Assert
    assert len(out["applicability"]) == 13


def test_run_all_applicable_tool_warns():
    # Arrange
    # Act
    out = _call("run_all_applicable", groups=SAMPLE, design="independent")
    # Assert
    assert "p-hacking" in out["warning"]


def test_invalid_design_is_reported_not_raised():
    # Arrange
    # Act
    out = _call("recommend_test", groups=SAMPLE, design="sideways")
    # Assert
    assert out["success"] is False
