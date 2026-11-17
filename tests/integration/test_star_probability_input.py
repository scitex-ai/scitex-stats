"""MCP significance symbols require a valid scalar probability."""

import asyncio
import json

import pytest

from scitex_stats._mcp._handlers._stars import p_to_stars_handler
from scitex_stats._mcp.tool_schemas import get_tool_schemas


@pytest.mark.parametrize("value", [-.001, 1.001, float("nan"), float("inf"), -float("inf")])
def test_invalid_probability_returns_error_without_symbols(value):
    # Arrange
    arguments = {"p_value": value}
    # Act
    result = asyncio.run(p_to_stars_handler(**arguments))
    json.dumps(result, allow_nan=False)
    # Assert
    assert {"success": result["success"], "stars": "stars" in result,
            "error": "p_value" in result.get("error", "")} == {
        "success": False, "stars": False, "error": True,
    }


@pytest.mark.parametrize("value,expected", [(0., "***"), (.0001, "***"),
                         (.001, "**"), (.005, "**"), (.01, "*"), (.05, "ns"), (1., "ns")])
def test_valid_probabilities_keep_strict_default_boundaries(value, expected):
    # Arrange
    arguments = {"p_value": value}
    # Act
    result = asyncio.run(p_to_stars_handler(**arguments))
    # Assert
    assert (result["success"], result["stars"], result["p_value"], result["thresholds"]) == (
        True, expected, value, [.001, .01, .05],
    )


def test_valid_custom_thresholds_keep_their_existing_result():
    # Arrange
    thresholds = [.0001, .001, .01]
    before = thresholds.copy()
    # Act
    result = asyncio.run(p_to_stars_handler(.001, thresholds=thresholds))
    # Assert
    assert (result["success"], result["stars"], result["significance"], thresholds) == (
        True, "*", "p < 0.01", before,
    )


def test_authoritative_wire_schema_declares_probability_bounds():
    # Arrange
    tools = get_tool_schemas()
    # Act
    tool = next(tool for tool in tools if tool.name == "p_to_stars")
    field = tool.model_dump(by_alias=True)["inputSchema"]["properties"]["p_value"]
    # Assert
    assert {"minimum": field.get("minimum"), "maximum": field.get("maximum")} == {
        "minimum": 0, "maximum": 1,
    }
