"""Native and transport contracts for normality-test dispatch."""

import asyncio
import inspect

import numpy as np
import pytest

from scitex_stats._mcp._handlers._normality import normality_test_handler


@pytest.mark.parametrize("method", ["shapiro", "dagostino", "anderson", "lilliefors"])
def test_native_dispatch_returns_data_for_supported_methods(method):
    from scitex_stats import normality_test

    result = normality_test([1, 2, 3, 4, 5, 6, 7, 8], method=method)
    assert not inspect.iscoroutinefunction(normality_test)
    assert isinstance(result, dict) and not {"success", "timestamp"} & result.keys()
    assert result["n"] == result["n_input"] == 8
    assert result["n_omitted"] == 0
    # Fixed references recorded from the parent leaf's supported backend path.
    expected_statistic = {
        "shapiro": 0.9748582562936844,
        "dagostino": 1.7004056883060088,
        "anderson": 0.13400045881773792,
        "lilliefors": 0.10485431269629009,
    }
    assert result["statistic"] == pytest.approx(expected_statistic[method], abs=1e-7)
    if method == "anderson":
        assert result["normal"] == (result["statistic"] < result["critical_value_5pct"])
        assert "p_value" not in result
    else:
        assert 0 <= result["p_value"] <= 1
        assert result["is_normal"] == (result["p_value"] >= 0.05)


def test_shapiro_closed_form_and_missing_counts():
    from scitex_stats import normality_test

    result = normality_test([1, float("nan"), 2, 3])
    assert (result["statistic"], result["p_value"]) == pytest.approx((1.0, 1.0))
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
    from scitex_stats import normality_test

    with pytest.raises(ValueError):
        normality_test(data, method=method)


@pytest.mark.parametrize(
    "data,method",
    [
        ([1, 2], "shapiro"),
        ([1, 2, 3, 4], "dagostino"),
        ([1, 2, 3], "lilliefors"),
        ([1, 1, 1], "shapiro"),
    ],
)
def test_transport_never_labels_input_error_as_success(data, method):
    result = asyncio.run(normality_test_handler(data, method=method))
    assert result["success"] is False and result["error"]


def test_transport_reports_used_and_input_sample_counts():
    result = asyncio.run(normality_test_handler([1, float("nan"), 2, 3]))
    assert result["success"] is True
    assert (result["n"], result["n_input"], result["n_omitted"]) == (3, 4, 1)


def test_missing_value_filter_does_not_mutate_the_input_array():
    from scitex_stats import normality_test

    data = np.array([1.0, np.nan, 2.0, 3.0])
    original = data.tobytes()
    normality_test(data)
    assert data.tobytes() == original
