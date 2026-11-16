"""MCP preserves valid numerical results and reports unsupported requests."""

import asyncio

import pytest

from scitex_stats._mcp.handlers import effect_size_handler


@pytest.mark.parametrize("measure", ["cohens_d", "hedges_g"])
def test_effect_size_handler_reports_unimplemented_unpooled_mode(measure):
    # Arrange
    groups = dict(group1=[1, 2, 3], group2=[4, 5, 6])
    # Act
    result = asyncio.run(effect_size_handler(**groups, measure=measure, pooled=False))
    # Assert
    assert (result["success"], "pooled=False" in result.get("error", "")) == (False, True)


@pytest.mark.parametrize(
    "measure,expected",
    [("cohens_d", -3.0), ("hedges_g", -2.4), ("glass_delta", -3.0), ("cliffs_delta", -1.0)],
)
def test_effect_size_handler_keeps_supported_numerical_results(measure, expected):
    # Arrange
    groups = dict(group1=[1, 2, 3], group2=[4, 5, 6])
    # Act
    result = asyncio.run(effect_size_handler(**groups, measure=measure))
    # Assert
    assert (result["success"], result["value"], result["group1_n"], result["group2_n"]) == (
        True, pytest.approx(expected, abs=1e-12, rel=0), 3, 3,
    )
