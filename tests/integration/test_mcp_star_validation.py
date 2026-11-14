"""Exercise invalid inputs and preserved strict thresholds through real MCP calls."""

import asyncio
import json
from datetime import datetime

import pytest
from scitex_stats import _server
from scitex_stats._mcp._handlers._stars import p_to_stars_handler

INVALID_P = [-.1, 1.1, float("nan"), float("inf"), float("-inf"), True, False, None, ".01"]
INVALID_THRESHOLDS = [[], [.01], [.01, .05], [.001, .01, .05, .1],
                      [.05, .01, .001], [.01, .01, .05], [-.1, .01, .05],
                      [.001, .01, 1.1], [float("nan"), .01, .05],
                      [.001, float("inf"), .05], [False, .01, .05],
                      [".001", .01, .05], "not a list"]
VALID = [(0, None, "***", "p < 0.001"), (.001, None, "**", "p < 0.01"),
         (.01, None, "*", "p < 0.05"), (.05, None, "ns", "p >= 0.05 (not significant)"),
         (1, None, "ns", "p >= 0.05 (not significant)"),
         (.00001, [.0001, .001, .01], "***", "p < 0.0001"),
         (.0001, [.0001, .001, .01], "**", "p < 0.001"),
         (.001, [.0001, .001, .01], "*", "p < 0.01"),
         (.01, [.0001, .001, .01], "ns", "p >= 0.01 (not significant)"),
         (0, [0, .5, 1], "**", "p < 0.5"),
         (.5, [0, .5, 1], "*", "p < 1"),
         (.005, (.001, .01, .05), "**", "p < 0.01")]


def call_tool(**kwargs):
    function = getattr(_server.p_to_stars, "fn", _server.p_to_stars)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("value", INVALID_P)
def test_star_tool_rejects_invalid_probability_without_stars(value):
    # Arrange
    kwargs = {"p_value": value}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert (set(report), report.get("success"), "p_value" in report.get("error", "")) == ({"success", "error"}, False, True)


@pytest.mark.parametrize("thresholds", INVALID_THRESHOLDS)
@pytest.mark.parametrize("value", [0, 1])
def test_star_tool_rejects_invalid_thresholds_before_data_dependent_selection(value, thresholds):
    # Arrange
    kwargs = {"p_value": value, "thresholds": thresholds}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert (set(report), report.get("success"), "thresholds" in report.get("error", "")) == ({"success", "error"}, False, True)


@pytest.mark.parametrize("value, thresholds, stars, significance", VALID)
def test_star_tool_preserves_valid_values_boundaries_and_transport_fields(value, thresholds, stars, significance):
    # Arrange
    expected_thresholds = list(thresholds) if thresholds is not None else [.001, .01, .05]
    # Act
    report = call_tool(p_value=value, thresholds=thresholds)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, type(timestamp)) == ({"success": True, "p_value": value, "stars": stars, "significance": significance, "thresholds": expected_thresholds}, datetime)


def test_star_handler_preserves_tuple_thresholds_for_existing_direct_callers():
    # Arrange
    thresholds = (.001, .01, .05)
    # Act
    report = asyncio.run(p_to_stars_handler(.005, thresholds))
    # Assert
    assert (report["success"], report["stars"], type(report["thresholds"]), report["thresholds"]) == (True, "**", tuple, thresholds)


def test_star_handler_does_not_modify_caller_thresholds():
    # Arrange
    thresholds = [.001, .01, .05]
    before = thresholds.copy()
    # Act
    asyncio.run(p_to_stars_handler(.005, thresholds))
    # Assert
    assert thresholds == before
