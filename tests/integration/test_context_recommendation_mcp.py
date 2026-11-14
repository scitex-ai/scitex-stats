"""Qualify default-family, single-factor context recommendations through MCP."""

import asyncio
import copy
from datetime import datetime
import inspect
import json

import pytest
import scitex_stats as stats
from scitex_stats import _server
from scitex_stats.auto import StatContext
from scitex_stats.auto._rules import TEST_RULES

CASES = ("default", "explicit", "paired", "ordinal", "categorical", "control", "empty_sizes", "zero")


def arguments(case):
    kwargs = {"n_groups": 2, "sample_sizes": None, "outcome_type": "continuous", "design": "between",
              "paired": False, "has_control_group": False, "top_k": 3}
    changes = {"explicit": {"sample_sizes": [9, 17], "top_k": 1},
               "paired": {"sample_sizes": [12, 12], "design": "within", "paired": True},
               "ordinal": {"sample_sizes": [20, 23], "outcome_type": "ordinal"},
               "categorical": {"sample_sizes": [40, 50], "outcome_type": "categorical"},
               "control": {"n_groups": 3, "sample_sizes": [8, 9, 10], "has_control_group": True},
               "empty_sizes": {"sample_sizes": []}, "zero": {"top_k": 0}}
    kwargs.update(changes.get(case, {}))
    return kwargs


def context(kwargs):
    return StatContext(n_groups=kwargs["n_groups"], sample_sizes=kwargs["sample_sizes"] or [30] * kwargs["n_groups"],
                       outcome_type=kwargs["outcome_type"], design=kwargs["design"], paired=kwargs["paired"],
                       has_control_group=kwargs["has_control_group"], n_factors=1)


def call_tool(kwargs):
    function = getattr(_server.recommend_tests, "fn", _server.recommend_tests)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("case", CASES)
def test_context_recommendation_runs_native_selector_in_worker(case, observe_native):
    # Arrange
    kwargs = arguments(case)
    before = copy.deepcopy(kwargs)
    operation = inspect.unwrap(stats.recommend_tests)
    expected = {"ctx": context(kwargs), "top_k": kwargs["top_k"], "families": None}
    # Act
    with observe_native(operation) as calls:
        report = call_tool(kwargs)
    # Assert
    assert (report["success"], calls, kwargs) == (True, [expected], before)


@pytest.mark.parametrize("case", CASES)
def test_context_recommendation_preserves_native_order_and_owned_details(case):
    # Arrange
    kwargs = arguments(case)
    expected_names = stats.recommend_tests(context(kwargs), top_k=kwargs["top_k"])
    expected_context = {key: value for key, value in kwargs.items() if key != "top_k"}
    keys = {"name", "family", "priority", "needs_normality", "needs_equal_variance", "rationale"}
    expected_details = [(name, TEST_RULES[name].family, TEST_RULES[name].priority,
                         TEST_RULES[name].needs_normality, TEST_RULES[name].needs_equal_variance) for name in expected_names]
    # Act
    report = call_tool(kwargs)
    rows = report["recommendations"]
    timestamp = datetime.fromisoformat(report["timestamp"])
    observed = [(row["name"], row["family"], row["priority"], row["needs_normality"], row["needs_equal_variance"]) for row in rows]
    # Assert
    assert (set(report), report["success"], report["context"], observed,
            all(set(row) == keys and isinstance(row["rationale"], str) and row["rationale"].strip() for row in rows),
            isinstance(timestamp, datetime)) == ({"success", "context", "recommendations", "timestamp"}, True,
                                                expected_context, expected_details, True, True)


def test_public_default_facade_wraps_the_same_native_selector():
    # Arrange
    public = stats.recommend_tests
    # Act
    native = inspect.unwrap(public)
    # Assert
    assert (native is stats.auto.recommend_tests, inspect.iscoroutinefunction(public)) == (True, False)
