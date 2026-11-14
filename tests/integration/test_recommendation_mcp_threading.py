"""Exercise actual recommendation calculations through their registered MCP functions."""

import asyncio
import json
import sys
import threading

import pytest
import scitex_stats as stats
from scitex_stats import _server

NAMES = ("check_applicability", "recommend_test", "run_all_applicable")
SAMPLE = [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7],
          [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]]


def arguments(name):
    tool = {"groups": SAMPLE, "design": "independent", "scale": "continuous",
            "group_names": ["A", "B"]}
    if name == "recommend_test":
        tool["assume_equal_variance"] = False
    elif name == "run_all_applicable":
        tool.update(primary="mannwhitneyu", alternative="greater")
    native = {key: value for key, value in tool.items() if key != "groups"}
    native["data"] = tool["groups"]
    return tool, native


def call_tool(name, kwargs):
    function = getattr(_server, name)
    function = getattr(function, "fn", function)
    return json.loads(asyncio.run(function(**kwargs)))


def call_with_native_result(name, kwargs):
    """Observe the actual return, including its per-call provenance receipt."""
    operation = getattr(stats, name)
    results = []
    caller = threading.get_ident()
    previous_main, previous_worker = sys.getprofile(), threading.getprofile()

    def observe(frame, event, arg):
        if event == "return" and frame.f_code is operation.__code__:
            results.append(arg)
        previous = previous_main if threading.get_ident() == caller else previous_worker
        if previous is not None:
            previous(frame, event, arg)

    sys.setprofile(observe)
    threading.setprofile(observe)
    try:
        result = call_tool(name, kwargs)
    finally:
        sys.setprofile(previous_main)
        threading.setprofile(previous_worker)
    return result, results


def native_payload(native):
    payload = {"applicability": native} if isinstance(native, list) else native
    return json.loads(json.dumps({"success": True, **payload}, default=str))


@pytest.mark.parametrize("name", NAMES)
def test_recommendation_tool_runs_native_calculation_in_a_worker(name, observe_native):
    # Arrange
    tool, native = arguments(name)
    operation = getattr(stats, name)
    # Act
    with observe_native(operation) as calls:
        result = call_tool(name, tool)
    observed = [{key: call[key] for key in native} for call in calls]
    # Assert
    assert (result["success"], observed) == (True, [native])


@pytest.mark.parametrize("name", NAMES)
def test_recommendation_tool_preserves_native_payload_and_transport_envelope(name):
    # Arrange
    tool, _ = arguments(name)
    # Act
    result, returns = call_with_native_result(name, tool)
    # Assert
    assert [result] == [native_payload(value) for value in returns]


@pytest.mark.parametrize("name", NAMES)
def test_recommendation_tool_preserves_invalid_design_failure(name):
    # Arrange
    tool, _ = arguments(name)
    tool["design"] = "sideways"
    # Act
    result = call_tool(name, tool)
    # Assert
    assert (result.get("success"), "design" in result.get("error", "")) == (False, True)
