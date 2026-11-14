"""Exercise real APA validation through its registered MCP function."""

import asyncio
import json

import pytest
import scitex_stats as stats
from scitex_stats import _server

CASES = ("empty", "plain", "html", "result")


def arguments(case):
    kwargs = {"text": "", "html": None, "result": None}
    if case == "plain":
        kwargs["text"] = "t(14) = -6.354, p = 0.0000, d = 3.2, n = 16"
    elif case == "html":
        kwargs["html"] = "<i>χ</i><sup>2</sup>(1, <i>N</i> = 30) = 3.23, <i>p</i> = .072, <i>V</i> = .33"
    elif case == "result":
        kwargs["result"] = stats.run_test("ttest_ind", data=[1, 2, 3, 4], data2=[3, 5, 6, 8])
        kwargs["text"] = "t(6) = 0.00, p = .900, d = 0.00, n = 8"
    return kwargs


def call_tool(kwargs):
    function = getattr(_server.validate_apa, "fn", _server.validate_apa)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("case", CASES)
def test_apa_tool_runs_native_validation_in_a_worker(case, observe_native):
    # Arrange
    kwargs = arguments(case)
    operation = stats.validate_apa
    # Act
    with observe_native(operation) as calls:
        report = call_tool(kwargs)
    # Assert
    assert (set(report), calls) == ({"ok", "violations", "expected"}, [kwargs])


@pytest.mark.parametrize("case", CASES)
def test_apa_tool_preserves_complete_native_report(case):
    # Arrange
    kwargs = arguments(case)
    expected = stats.validate_apa(**kwargs)
    # Act
    report = call_tool(kwargs)
    # Assert
    assert report == expected


@pytest.mark.parametrize("html", [42, ["not markup"]])
def test_apa_tool_preserves_invalid_html_type_exception(html):
    # Arrange
    kwargs = {"html": html}
    # Act
    with pytest.raises(TypeError):
        # Assert
        call_tool(kwargs)
