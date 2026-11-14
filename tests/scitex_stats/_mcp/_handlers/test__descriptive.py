"""Descriptive-statistics failure responses and percentile result labels."""

import asyncio

import pytest

from scitex_stats._mcp.handlers import describe_handler


@pytest.mark.parametrize("data", [[], [float("nan")], [float("nan"), float("nan")]])
def test_describe_unusable_data_reports_failure(data):
    # Arrange
    # Act
    result = asyncio.run(describe_handler(data=data))
    # Assert
    assert result["success"] is False


@pytest.mark.parametrize("data", [[], [float("nan")], [float("nan"), float("nan")]])
def test_describe_unusable_data_keeps_error_message(data):
    # Arrange
    # Act
    result = asyncio.run(describe_handler(data=data))
    # Assert
    assert result.get("error") == "No valid data points"


@pytest.mark.parametrize(
    "percentiles, expected",
    [
        ([2.5, 97.5], {"2.5": 2.5, "97.5": 97.5}),
        ([2.1, 2.9], {"2.1": 2.1, "2.9": 2.9}),
        ([0.0, 25.0, 100.0], {"0": 0.0, "25": 25.0, "100": 100.0}),
    ],
)
def test_describe_keeps_distinct_requested_percentile_labels(percentiles, expected):
    # Arrange: interpolation on [0, 100] gives the requested percentile itself.
    data = [0.0, 100.0]
    # Act
    result = asyncio.run(describe_handler(data=data, percentiles=percentiles))
    # Assert
    assert (result["success"], result["percentiles"]) == (
        True, pytest.approx(expected)
    )
