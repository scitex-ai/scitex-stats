"""Check real native star selection and preserved MCP validation boundaries."""

import asyncio
import copy
import json

import pytest
import scitex_stats as stats
from scitex_stats import _server

CASES = [(.0005, None), (.001, None), (.01, None), (.05, None),
         (.0001, [.0001, .001, .01]), (.001, [.0001, .001, .01]), (.01, [.0001, .001, .01]),
         (0, [0, .5, 1]), (1, [0, .5, 1])]


def call_tool(**kwargs):
    function = getattr(_server.p_to_stars, "fn", _server.p_to_stars)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("p_value, thresholds", CASES)
def test_star_tool_delegates_to_native_style_selection(p_value, thresholds, observe_native):
    # Arrange
    values = thresholds if thresholds is not None else [.001, .01, .05]
    pairs = list(zip(values, ("***", "**", "*")))
    style = stats.StatStyle(id="reference", label="Reference", target="plain", alpha_thresholds=pairs)
    expected = stats.p_to_stars(p_value, style=style) if thresholds is not None else stats.p_to_stars(p_value)
    before = copy.deepcopy(thresholds)
    # Act
    with observe_native(stats.p_to_stars) as calls:
        report = call_tool(p_value=p_value, thresholds=thresholds)
    observed = [(call["p_value"], call["style"].alpha_thresholds) for call in calls]
    # Assert
    assert (report["success"], report["stars"], observed, thresholds) == (True, expected, [(p_value, pairs)], before)


@pytest.mark.parametrize("kwargs", [{"p_value": -.1}, {"p_value": True},
                                    {"p_value": .01, "thresholds": []},
                                    {"p_value": .01, "thresholds": [.05, .01, .001]}])
def test_star_validation_precedes_native_selection(kwargs, observe_native):
    # Arrange
    before = copy.deepcopy(kwargs)
    # Act
    with observe_native(stats.p_to_stars) as calls:
        report = call_tool(**kwargs)
    # Assert
    assert (set(report), report["success"], calls, kwargs) == ({"success", "error"}, False, [], before)


def test_custom_mcp_thresholds_do_not_mutate_default_native_style():
    # Arrange
    style = stats.get_stat_style("apa_latex")
    before = copy.deepcopy(style)
    # Act
    report = call_tool(p_value=.2, thresholds=[.1, .3, .5])
    # Assert
    assert (report["success"], report["stars"], style) == (True, "**", before)
