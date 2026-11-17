"""Native and transport contracts for normality-test dispatch."""

import asyncio
import inspect

import numpy as np
import pytest

from scitex_stats._mcp._handlers._normality import normality_test_handler


@pytest.mark.parametrize(
    "method,expected",
    [
        (
            "shapiro",
            {
                "test": "Shapiro-Wilk",
                "statistic_name": "W",
                "statistic": pytest.approx(0.9748582562936844, abs=1e-7),
                "p_value": pytest.approx(0.933165191583391, abs=1e-7),
                "is_normal": True,
                "interpretation": "Data appears normally distributed (p >= 0.05)",
            },
        ),
        (
            "dagostino",
            {
                "test": "D'Agostino-Pearson",
                "statistic_name": "K2",
                "statistic": pytest.approx(1.7004056883060088, abs=1e-7),
                "p_value": pytest.approx(0.42732824212143383, abs=1e-7),
                "is_normal": True,
                "interpretation": "Data appears normally distributed (p >= 0.05)",
            },
        ),
        (
            "anderson",
            {
                "test": "Anderson-Darling",
                "statistic_name": "A2",
                "statistic": pytest.approx(0.13400045881773792, abs=1e-7),
                "critical_value_5pct": 0.666,
                "normal": True,
            },
        ),
        (
            "lilliefors",
            {
                "test": "Lilliefors",
                "statistic_name": "D",
                "statistic": pytest.approx(0.10485431269629009, abs=1e-7),
                "p_value": pytest.approx(0.99, abs=1e-7),
                "is_normal": True,
                "interpretation": "Data appears normally distributed (p >= 0.05)",
            },
        ),
    ],
)
def test_native_dispatch_returns_supported_method_result(method, expected):
    # Arrange
    from scitex_stats import normality_test

    # Act
    result = normality_test([1, 2, 3, 4, 5, 6, 7, 8], method=method)
    # Assert
    assert result == {
        "method": method,
        "n": 8,
        "n_input": 8,
        "n_omitted": 0,
        **expected,
    }


def test_native_operation_is_synchronous():
    # Arrange
    from scitex_stats import normality_test

    # Act
    asynchronous = inspect.iscoroutinefunction(normality_test)
    # Assert
    assert asynchronous is False


def test_shapiro_closed_form_after_missing_value_omission():
    # Arrange
    from scitex_stats import normality_test

    # Act
    result = normality_test([1, float("nan"), 2, 3])
    # Assert
    assert (result["statistic"], result["p_value"]) == pytest.approx((1.0, 1.0))


def test_native_missing_value_counts():
    # Arrange
    from scitex_stats import normality_test

    # Act
    result = normality_test([1, float("nan"), 2, 3])
    # Assert
    assert (result["n"], result["n_input"], result["n_omitted"]) == (3, 4, 1)


@pytest.mark.parametrize(
    "data,method",
    [
        ([1, 2], "shapiro"),
        ([1, 2, 3, 4], "dagostino"),
        ([1, 2, 3], "lilliefors"),
        ([[1, 2, 3]], "shapiro"),
        ([1, 2, float("inf")], "shapiro"),
        ([1, 1, 1], "shapiro"),
    ],
)
def test_native_rejects_unusable_data(data, method):
    # Arrange
    from scitex_stats import normality_test

    # Act
    # Assert
    with pytest.raises(ValueError):
        normality_test(data, method=method)


@pytest.mark.parametrize(
    "data,method,error",
    [
        ([1, 2], "shapiro", "Need at least 3 data points after omitting NaNs"),
        ([1, 2, 3, 4], "dagostino", "D'Agostino test requires at least 8 samples"),
        ([1, 2, 3], "lilliefors", "Lilliefors test requires at least 4 samples"),
        ([1, 1, 1], "shapiro", "Normality testing requires non-constant data"),
    ],
)
def test_transport_never_labels_input_error_as_success(data, method, error):
    # Arrange
    request = normality_test_handler(data, method=method)
    # Act
    result = asyncio.run(request)
    # Assert
    assert result == {"success": False, "error": error}


def test_transport_reports_used_and_input_sample_counts():
    # Arrange
    request = normality_test_handler([1, float("nan"), 2, 3])
    # Act
    result = asyncio.run(request)
    # Assert
    assert {key: result[key] for key in ["success", "n", "n_input", "n_omitted"]} == {
        "success": True,
        "n": 3,
        "n_input": 4,
        "n_omitted": 1,
    }


def test_missing_value_filter_does_not_mutate_the_input_array():
    # Arrange
    from scitex_stats import normality_test

    data = np.array([1.0, np.nan, 2.0, 3.0])
    original = data.tobytes()
    # Act
    normality_test(data)
    # Assert
    assert data.tobytes() == original
