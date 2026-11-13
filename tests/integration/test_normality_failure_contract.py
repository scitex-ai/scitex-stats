"""A statistical input error must not be reported as a successful test."""

import asyncio

import pytest

from scitex_stats._mcp._handlers._normality import normality_test_handler


@pytest.mark.parametrize("data, method, error", [
    ([], "shapiro", "Need at least 3 data points"),
    ([1.0, 2.0], "shapiro", "Need at least 3 data points"),
    ([float("nan")] * 3, "shapiro", "Need at least 3 data points"),
    ([1.0, 2.0, float("nan")], "shapiro", "Need at least 3 data points"),
    (list(range(7)), "dagostino", "D'Agostino test requires at least 8 samples"),
])
def test_normality_input_error_is_a_failure(data, method, error):
    # Arrange: inputs violate the method's existing sample requirement.
    # Act
    result = asyncio.run(normality_test_handler(data=data, method=method))
    # Assert
    assert (result["success"], result.get("error"), "statistic" in result) == (False, error, False)
