"""Explicit Tukey requires usable groups and positive finite pooled error."""

import asyncio
import json
from copy import deepcopy
from itertools import combinations

import numpy as np
import pytest
from scipy.stats import studentized_range

from scitex_stats import posthoc_test
from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

INVALID = [
    ([[1., 1.], [1., 1.], [1., 1.]], "pooled"),
    ([[1., 1.], [2., 2.], [3., 3.]], "pooled"),
    ([[1.], [2.], [3.]], "pooled"),
    ([[float("nan"), 2.], [3., 4.]], "finite"),
    ([[float("inf"), 2.], [3., 4.]], "finite"),
    ([[], [1., 2.]], "nonempty"),
    ([[[1.], [2.]], [[3.], [4.]]], "1D"),
    ([[1e308, -1e308], [2., 3.]], "pooled"),
]


@pytest.mark.parametrize("groups,message", INVALID)
def test_native_tukey_rejects_undefined_groups(groups, message):
    # Arrange
    failure = None
    # Act
    try:
        posthoc_test(groups, method="tukey")
    except Exception as error:
        failure = error
    # Assert
    assert {"type": type(failure), "message": message in str(failure)} == {
        "type": ValueError, "message": True,
    }


@pytest.mark.parametrize("groups,message", INVALID)
def test_mcp_tukey_returns_error_without_comparisons(groups, message):
    # Arrange
    arguments = {"groups": groups, "method": "tukey"}
    # Act
    result = asyncio.run(posthoc_test_handler(**arguments))
    json.dumps(result, allow_nan=False)
    # Assert
    assert {"success": result["success"], "rows": "comparisons" in result,
            "message": message in result.get("error", "")} == {
        "success": False, "rows": False, "message": True,
    }


VALID = [
    [[1., 2., 4., 5.], [3., 5., 7., 9., 10.], [7., 8., 10., 13.]],
    [[1., 1.], [2., 2.], [3., 4., 5.]],
    [[1.], [2., 4., 5.], [3., 6., 8.]],
]


@pytest.mark.parametrize("groups", VALID)
def test_usable_pooled_variance_preserves_tukey_kramer_results(groups):
    # Arrange: independent studentized-range reference, including a singleton.
    before = deepcopy(groups)
    arrays = [np.asarray(group, dtype=float) for group in groups]
    df = sum(len(group) for group in arrays) - len(arrays)
    mse = sum(np.sum((group - np.mean(group)) ** 2) for group in arrays) / df
    critical = studentized_range.ppf(.95, len(arrays), df)
    expected = []
    for left, right in combinations(arrays, 2):
        difference = np.mean(right) - np.mean(left)
        se = np.sqrt(mse * (1 / len(left) + 1 / len(right)) / 2)
        probability = studentized_range.sf(abs(difference) / se, len(arrays), df)
        expected.append([difference, probability, difference - critical * se,
                         difference + critical * se])
    # Act
    native = posthoc_test(groups, method="tukey")
    wire = asyncio.run(posthoc_test_handler(groups, method="tukey"))
    success = wire.pop("success")
    wire.pop("timestamp")
    rows = native["comparisons"]
    actual = [[r["mean_diff"], r["p_adj"], r["ci_lower"], r["ci_upper"]] for r in rows]
    json.dumps(native, allow_nan=False)
    # Assert
    assert {"success": success, "same_payload": native == wire,
            "values": np.allclose(actual, expected, rtol=1e-10, atol=1e-12),
            "inputs": groups == before,
            "boolean_decisions": all(type(r["reject"]) is bool for r in rows)} == {
        "success": True, "same_payload": True, "values": True, "inputs": True,
        "boolean_decisions": True,
    }
