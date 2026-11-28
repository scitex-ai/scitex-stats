"""Failure responses for unusable descriptive-statistics input."""

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
