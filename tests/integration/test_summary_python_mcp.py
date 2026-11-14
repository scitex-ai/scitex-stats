"""Qualify the dictionary summary separately from legacy axis-aware describe."""

import asyncio
import inspect
import statistics

import numpy as np
import pytest
import scitex_stats as ss

from scitex_stats._capabilities import get_capabilities
from scitex_stats._mcp.handlers import describe_handler


@pytest.mark.parametrize("data, clean", [
    ([1., 2., 3.], [1., 2., 3.]),
    ([float("nan"), 1., 2., 3.], [1., 2., 3.]),
    ([-5., -1., 2., 8.], [-5., -1., 2., 8.]),
])
def test_native_summary_is_synchronous_and_matches_sample_statistics(data, clean):
    # Arrange
    expected = (len(clean), statistics.fmean(clean), statistics.stdev(clean), statistics.variance(clean))
    # Act
    result = ss.summarize(data=data)
    observed = (result["n"], result["mean"], result["std"], result["var"])
    # Assert
    assert (inspect.iscoroutinefunction(ss.summarize), set(result) & {"success", "timestamp"}, observed) == (
        False, set(), pytest.approx(expected),
    )


@pytest.mark.parametrize("data, message", [
    ([], "No valid data points"),
    ([float("nan")], "No valid data points"),
    ([float("inf")], "Data must contain only finite values after removing NaN"),
    ([-float("inf")], "Data must contain only finite values after removing NaN"),
    ([1., float("inf")], "Data must contain only finite values after removing NaN"),
    ([float("nan"), 1., float("inf")], "Data must contain only finite values after removing NaN"),
])
def test_native_summary_raises_the_owning_input_exception(data, message):
    # Arrange
    # Act
    with pytest.raises(ValueError, match=message):
        # Assert
        ss.summarize(data=data)


@pytest.mark.parametrize("kwargs", [
    {"data": [1., 2., 3.], "percentiles": None},
    {"data": [float("nan"), 1., 2., 3.], "percentiles": [25., 75.]},
    {"data": [0., 100.], "percentiles": [2.1, 2.9, 97.5]},
    {"data": [-5., -1., 2., 8.], "percentiles": []},
])
def test_mcp_summary_preserves_complete_native_payload(kwargs):
    # Arrange
    expected = ss.summarize(**kwargs)
    # Act
    report = asyncio.run(describe_handler(**kwargs))
    payload = {key: value for key, value in report.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (report["success"], payload) == (True, expected)


@pytest.mark.parametrize("kwargs", [
    {"data": [1., 2., 3.], "percentiles": None},
    {"data": [0., 100.], "percentiles": [2.1, 2.9, 97.5]},
])
def test_mcp_summary_calls_the_public_native_operation_in_worker(kwargs, observe_native):
    # Arrange
    operation = ss.summarize
    expected = operation(**kwargs)
    # Act
    with observe_native(operation) as calls:
        report = asyncio.run(describe_handler(**kwargs))
    payload = {key: value for key, value in report.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (calls, report["success"], payload) == ([kwargs], True, expected)


def test_legacy_axis_aware_describe_still_returns_stacked_values_and_names():
    # Arrange
    data = np.array([[1., 2., 3.], [4., 5., 6.]])
    # Act
    values, names = ss.describe(data, dim=-1, funcs=["mean"])
    # Assert
    assert (values.tolist(), names) == ([[2.], [5.]], ["mean"])


def test_summary_capability_declares_the_explicit_mcp_name_mapping():
    # Arrange
    expected = {"name": "summarize", "purpose": "Summarize a numeric sample as a dictionary after removing NaN values.",
                "python": ["scitex_stats.summarize"], "mcp": ["describe"],
                "test_references": ["tests/integration/test_summary_python_mcp.py"]}
    # Act
    rows = [item for item in get_capabilities()["capabilities"] if item["name"] == "summarize"]
    # Assert
    assert rows == [expected]
