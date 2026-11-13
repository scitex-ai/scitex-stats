#!/usr/bin/env python3
# File: tests/test_server.py

"""Tests for the MCP server creation and tool listing.

Verifies that the FastMCP server is properly configured with
all expected tools and that tools have correct signatures.
"""

import asyncio

import pytest

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    return loop.run_until_complete(coro)


@pytest.fixture(scope="module")
def mcp_server():
    """Return the FastMCP server instance."""
    from scitex_stats._server import mcp

    return mcp


async def _client_list_tools(mcp_server):
    """Enumerate tools via the in-memory FastMCP client.

    FastMCP 2.12 removed the public ``FastMCP.list_tools()`` coroutine;
    the supported enumeration path is the in-memory ``Client`` transport.
    """
    from fastmcp import Client

    async with Client(mcp_server) as client:
        return await client.list_tools()


@pytest.fixture(scope="module")
def tool_names(mcp_server):
    """Return sorted list of registered tool names."""
    tools = _run_async(_client_list_tools(mcp_server))
    return sorted(t.name for t in tools)


@pytest.fixture(scope="module")
def tools_by_name(mcp_server):
    """Return dict of tool_name -> tool object."""
    tools = _run_async(_client_list_tools(mcp_server))
    return {t.name: t for t in tools}


def _props_of(tool):
    """Schema properties across MCP SDK majors (2.x: input_schema)."""
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return (schema or {}).get("properties", {})


# ===================================================================
# 1. Server creation
# ===================================================================


class TestServerCreation:
    """Test that the MCP server is properly created."""

    def test_server_exists_mcp_server(self, mcp_server):
        # Arrange
        # Act
        # Assert
        assert mcp_server is not None

    def test_server_name_scitex_stats_mcp_server(self, mcp_server):
        # Arrange
        # Act
        # Assert
        assert mcp_server.name == "scitex-stats"

    def test_server_has_instructions_mcp_server(self, mcp_server):
        # Arrange
        # Act
        # Assert
        assert mcp_server.instructions is not None

    def test_server_has_instructions_mcp_server_2(self, mcp_server):
        # Arrange
        # Act
        # Assert
        assert len(mcp_server.instructions) > 0


# ===================================================================
# 2. Tool listing
# ===================================================================

EXPECTED_TOOLS = [
    "correct_pvalues",
    "describe",
    "effect_size",
    "format_results",
    "normality_test",
    "p_to_stars",
    "posthoc_test",
    "power_analysis",
    "recommend_tests",
    "run_test",
]


class TestToolListing:
    """Test that all expected tools are registered."""

    def test_tool_count_tool_names(self, tool_names):
        # Arrange
        # Act
        # Assert
        assert len(tool_names) >= 10, (
            f"Expected at least 10 tools, got {len(tool_names)}: {tool_names}"
        )

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_registered_tool_name_tool_names(self, tool_name, tool_names):
        # Arrange
        # Act
        # Assert
        assert tool_name in tool_names, f"Tool '{tool_name}' not found in {tool_names}"

    def test_all_tools_have_descriptions(self, tools_by_name):
        # Arrange
        # Act
        # Assert
        for name, tool in tools_by_name.items():
            assert tool.description is not None and len(tool.description) > 0, (
                f"Tool '{name}' has no description"
            )


# ===================================================================
# 3. Tool schemas
# ===================================================================


class TestToolSchemas:
    """Test that tools have proper input schemas (via FastMCP parameters attr)."""

    def test_run_test_has_test_name_param(self, tools_by_name):
        # Arrange
        tool = tools_by_name["run_test"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "test_name" in props

    def test_recommend_tests_has_n_groups(self, tools_by_name):
        # Arrange
        tool = tools_by_name["recommend_tests"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "n_groups" in props

    def test_correct_pvalues_has_pvalues(self, tools_by_name):
        # Arrange
        tool = tools_by_name["correct_pvalues"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "pvalues" in props

    def test_effect_size_has_groups_group1_props(self, tools_by_name):
        # Arrange
        tool = tools_by_name["effect_size"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "group1" in props

    def test_effect_size_has_groups_group2_props(self, tools_by_name):
        # Arrange
        tool = tools_by_name["effect_size"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "group2" in props

    def test_p_to_stars_has_p_value(self, tools_by_name):
        # Arrange
        tool = tools_by_name["p_to_stars"]
        # Act
        props = _props_of(tool)
        # Assert
        assert "p_value" in props


# ===================================================================
# 4. run_server function
# ===================================================================


class TestRunServerFunction:
    """Test that run_server is importable and callable."""

    def test_run_server_importable(self):
        # Arrange
        from scitex_stats._server import run_server
        # Act
        # Assert
        assert callable(run_server)

    def test_mcp_module_re_exports_case_1(self):
        # Arrange
        from scitex_stats._mcp import mcp, run_server
        # Act
        # Assert
        assert mcp is not None

    def test_mcp_module_re_exports_callable_run_server(self):
        # Arrange
        from scitex_stats._mcp import mcp, run_server
        # Act
        # Assert
        assert callable(run_server)


# EOF


# ===================================================================
# 5. Direct invocation of each @mcp.tool() function
# ===================================================================
# FastMCP 2.12 wraps an @mcp.tool() target in a non-callable
# FunctionTool; the underlying coroutine is reachable via ``.fn``.
# Calling it directly bumps coverage on the tool bodies, which are
# unreachable through the registration-only tests above.

import json
import numpy as np

from scitex_stats import _server as srv


def _decode(s):
    return json.loads(s)


def _tool_fn(name):
    """Return the raw coroutine behind a registered MCP tool (version-robust).

    FastMCP 2.x wraps an @mcp.tool() target in a non-callable FunctionTool
    whose body is reachable via ``.fn``; FastMCP 3.x leaves the attribute as
    the plain async function. Resolve whichever form is installed.
    """
    obj = getattr(srv, name)
    return getattr(obj, "fn", obj)


def test_recommend_tests_direct():
    # Arrange
    # Act
    out = _decode(
        _run_async(_tool_fn("recommend_tests")(n_groups=2, sample_sizes=[30, 30], top_k=3))
    )
    # Assert
    assert out["success"] is True


def test_run_test_direct_ttest_ind_success():
    # Arrange
    rng_s = np.random.default_rng(0)
    g1 = rng_s.normal(0, 1, 30).tolist()
    g2 = rng_s.normal(0.5, 1, 30).tolist()
    # Act
    out = _decode(_run_async(_tool_fn("run_test")(test_name="ttest_ind", data=[g1, g2])))
    # Assert
    assert out["success"] is True

def test_run_test_direct_ttest_ind_value():
    # Arrange
    rng_s = np.random.default_rng(0)
    g1 = rng_s.normal(0, 1, 30).tolist()
    g2 = rng_s.normal(0.5, 1, 30).tolist()
    # Act
    out = _decode(_run_async(_tool_fn("run_test")(test_name="ttest_ind", data=[g1, g2])))
    # Assert
    assert "p_value" in out


def test_format_results_direct_success():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("format_results")(
                test_name="ttest_ind",
                statistic=-3.21,
                p_value=0.002,
                df=58,
                effect_size=-0.83,
                effect_size_name="d",
                style="apa",
            )
        )
    )
    # Assert
    assert out["success"] is True

def test_format_results_direct_formatted():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("format_results")(
                test_name="ttest_ind",
                statistic=-3.21,
                p_value=0.002,
                df=58,
                effect_size=-0.83,
                effect_size_name="d",
                style="apa",
            )
        )
    )
    # Assert
    assert "formatted" in out


def test_power_analysis_direct():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("power_analysis")(
                test_type="ttest",
                effect_size=0.5,
                power=0.8,
                alpha=0.05,
            )
        )
    )
    # Assert
    assert out["success"] is True


def test_correct_pvalues_direct():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("correct_pvalues")(
                pvalues=[0.001, 0.04, 0.03, 0.20, 0.005],
                method="fdr_bh",
                alpha=0.05,
            )
        )
    )
    # Assert
    assert isinstance(out, dict)


def test_describe_direct_success():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("describe")(data=[1.0, 2.0, 3.0, 4.0, 5.0])))
    # Assert
    assert out["success"] is True

def test_describe_direct_mean():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("describe")(data=[1.0, 2.0, 3.0, 4.0, 5.0])))
    # Assert
    assert "mean" in out


def test_effect_size_direct_success():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("effect_size")(
                group1=[1, 2, 3, 4, 5],
                group2=[2, 3, 4, 5, 6],
                measure="cohens_d",
            )
        )
    )
    # Assert
    assert out["success"] is True

def test_effect_size_direct_cohen_measure():
    # Arrange
    # Act
    out = _decode(
        _run_async(
            _tool_fn("effect_size")(
                group1=[1, 2, 3, 4, 5],
                group2=[2, 3, 4, 5, 6],
                measure="cohens_d",
            )
        )
    )
    # Assert
    assert out["measure"] == "Cohen's d"


def test_normality_test_direct_success():
    # Arrange
    rng_n = np.random.default_rng(0)
    # Act
    out = _decode(
        _run_async(_tool_fn("normality_test")(data=rng_n.normal(0, 1, 50).tolist()))
    )
    # Assert
    assert out["success"] is True

def test_normality_test_direct_shapiro_wilk():
    # Arrange
    rng_n = np.random.default_rng(0)
    # Act
    out = _decode(
        _run_async(_tool_fn("normality_test")(data=rng_n.normal(0, 1, 50).tolist()))
    )
    # Assert
    assert out["test"] == "Shapiro-Wilk"


def test_posthoc_test_direct_success():
    # Arrange
    rng_p = np.random.default_rng(0)
    groups = [rng_p.normal(0, 1, 25).tolist() for _ in range(3)]
    # Act
    out = _decode(
        _run_async(
            _tool_fn("posthoc_test")(
                groups=groups,
                group_names=["A", "B", "C"],
                method="tukey",
            )
        )
    )
    # Assert
    assert out["success"] is True

def test_posthoc_test_direct_tukey_method():
    # Arrange
    rng_p = np.random.default_rng(0)
    groups = [rng_p.normal(0, 1, 25).tolist() for _ in range(3)]
    # Act
    out = _decode(
        _run_async(
            _tool_fn("posthoc_test")(
                groups=groups,
                group_names=["A", "B", "C"],
                method="tukey",
            )
        )
    )
    # Assert
    assert out["method"] == "tukey"


def test_p_to_stars_direct():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("p_to_stars")(p_value=0.001)))
    # Assert
    assert isinstance(out, dict)


def test_skills_list_direct_returns_json_envelope():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("skills_list")()))
    # Assert
    assert "success" in out


def test_skills_get_main_skill_direct():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("skills_get")()))
    # Assert
    assert "success" in out


def test_skills_get_unknown_name_direct():
    # Arrange
    # Act
    out = _decode(_run_async(_tool_fn("skills_get")(name="definitely-not-a-real-skill")))
    # Assert
    assert out["success"] is False
