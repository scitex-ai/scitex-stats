"""Corrupted embedded numeric values are findings, not verifier crashes."""

from copy import deepcopy

import pytest

import scitex_stats as stats
from scitex_stats._mcp._handlers._run_test import run_test_sync

X = [1., 2., 4., 5.]
Y = [3., 5., 7., 9.]


@pytest.fixture(params=["native", "mcp"])
def receipt_and_arguments(request):
    if request.param == "native":
        return stats.run_test("ttest_ind", data=X, data2=Y), {"data": X, "data2": Y}, "data"
    return run_test_sync("ttest_ind", data=[X, Y]), {"data": [X, Y]}, "data[0]"


@pytest.mark.parametrize("first", ["not numeric", {"__float__": "bad"}, {"__float__": None}])
@pytest.mark.parametrize("supply", [False, True])
def test_invalid_embedded_values_fail_without_exception(receipt_and_arguments, first, supply):
    # Arrange
    result, arguments, slot = deepcopy(receipt_and_arguments)
    result["provenance"]["inputs"][slot]["values"][0] = first
    before = deepcopy(result)
    supplied = arguments if supply else {}
    # Act
    report = stats.verify(result, **supplied)
    statuses = {row["name"]: row["status"] for row in report["checks"]}
    inputs = next(row["inputs"] for row in report["checks"] if row["name"] == "inputs")
    # Assert
    assert (report["verified"], statuses,
            any(row.get("error") and row["match"] is False for row in inputs), result) == (
        False, {"receipt": "fail", "result": "pass", "inputs": "fail", "recompute": "skip"},
        True, before,
    )


@pytest.mark.parametrize("supply", [False, True])
def test_valid_embedded_values_retain_verification(receipt_and_arguments, supply):
    # Arrange
    result, arguments, _ = deepcopy(receipt_and_arguments)
    before = deepcopy(result)
    supplied = arguments if supply else {}
    # Act
    report = stats.verify(result, **supplied)
    # Assert
    assert (report["verified"], {row["status"] for row in report["checks"]}, result) == (
        True, {"pass"}, before,
    )
