"""Exercise native normality values, exceptions and actual MCP delegation."""

import asyncio
import inspect

import pytest
import scitex_stats as ss


def test_python_normality_matches_scipy_shapiro_without_transport_metadata():
    # Arrange
    from scipy.stats import shapiro

    data = [1.1, 1.4, 1.8, 2.5, 2.9, 3.1, 3.9, 4.2]
    expected = shapiro(data)
    # Act
    result = ss.normality_test(data=data, method="shapiro")
    # Assert
    assert (inspect.iscoroutinefunction(ss.normality_test), isinstance(result, dict),
            set(result) & {"success", "timestamp"}, result["statistic"], result["p_value"]) == (
                False, True, set(), pytest.approx(float(expected.statistic)),
                pytest.approx(float(expected.pvalue)),
            )


@pytest.mark.parametrize("data, method, error", [
    ([], "shapiro", "Need at least 3 data points"),
    ([1.0, 2.0], "shapiro", "Need at least 3 data points"),
    ([float("nan")] * 3, "shapiro", "Need at least 3 data points"),
    ([1.0, 2.0, float("nan")], "shapiro", "Need at least 3 data points"),
    (list(range(7)), "dagostino", "D'Agostino test requires at least 8 samples"),
])
def test_python_normality_raises_a_native_input_error(data, method, error):
    # Arrange: the public operation has no transport failure envelope.
    # Act
    # Assert
    with pytest.raises(ValueError, match=error):
        ss.normality_test(data=data, method=method)


@pytest.mark.parametrize("method", ["shapiro", "dagostino", "anderson", "lilliefors"])
def test_mcp_normality_preserves_the_public_python_payload(method):
    # Arrange
    from scitex_stats._mcp._handlers._normality import normality_test_handler

    data = [float(value) for value in range(1, 21)]
    expected = ss.normality_test(data=data, method=method)
    # Act
    result = asyncio.run(normality_test_handler(data=data, method=method))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (result["success"], payload) == (True, expected)


def test_mcp_normality_calls_the_public_operation(observe_native):
    # Arrange: observe the actual function entry; retain real calculations.
    from scitex_stats._mcp._handlers._normality import normality_test_handler

    kwargs = dict(data=[1.0, 2.0, 3.0], method="shapiro")
    expected = ss.normality_test(**kwargs)
    # Act
    with observe_native(ss.normality_test) as calls:
        result = asyncio.run(normality_test_handler(**kwargs))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (calls, result["success"], payload) == ([kwargs], True, expected)
