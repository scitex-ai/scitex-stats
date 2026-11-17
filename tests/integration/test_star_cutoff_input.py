"""Custom MCP significance cutoffs form three ordered probability bounds."""

import asyncio
import json

import pytest

from scitex_stats._mcp._handlers._stars import p_to_stars_handler
from scitex_stats._mcp.tool_schemas import get_tool_schemas


@pytest.mark.parametrize("thresholds", [[], [.01], [.01, .05], [.001, .01, .05, .1],
                         [.05, .01, .001], [.001, .001, .05], [0., .01, .05],
                         [-.001, .01, .05], [.001, .01, 1.01],
                         [float("nan"), .01, .05], [.001, float("inf"), .05]])
def test_invalid_custom_cutoffs_return_error_without_symbols(thresholds):
    # Arrange
    before = thresholds.copy()
    # Act
    result = asyncio.run(p_to_stars_handler(.0001, thresholds=thresholds))
    json.dumps(result, allow_nan=False)
    # Assert
    assert (result["success"], "stars" in result,
            "thresholds" in result.get("error", ""), thresholds == before) == (
        False, False, True, True,
    )


@pytest.mark.parametrize("value,expected", [(0., "***"), (.0001, "**"),
                         (.001, "*"), (.01, "ns"), (1., "ns")])
def test_custom_cutoffs_preserve_each_strict_boundary(value, expected):
    # Arrange
    thresholds = [.0001, .001, .01]
    # Act
    result = asyncio.run(p_to_stars_handler(value, thresholds=thresholds))
    # Assert
    assert (result["success"], result["stars"], result["thresholds"], thresholds) == (
        True, expected, [.0001, .001, .01], [.0001, .001, .01],
    )


def test_probability_one_is_valid_as_the_last_cutoff():
    # Arrange
    thresholds = [.01, .1, 1.]
    # Act
    result = asyncio.run(p_to_stars_handler(.5, thresholds=thresholds))
    # Assert
    assert (result["success"], result["stars"], result["significance"]) == (
        True, "*", "p < 1.0",
    )


def test_wire_schema_declares_three_bounded_cutoffs():
    # Arrange
    tool = next(t for t in get_tool_schemas() if t.name == "p_to_stars")
    # Act
    field = tool.model_dump(by_alias=True)["inputSchema"]["properties"]["thresholds"]
    array = next(item for item in field["anyOf"] if item.get("type") == "array")
    # Assert
    assert (array.get("minItems"), array.get("maxItems"), array["items"].get("exclusiveMinimum"),
            array["items"].get("maximum")) == (3, 3, 0, 1)
