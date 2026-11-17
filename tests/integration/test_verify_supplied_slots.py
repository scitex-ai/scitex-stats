"""MCP-origin receipts cannot silently ignore supplied native-only input slots."""

from copy import deepcopy

import numpy as np
import pytest

import scitex_stats as stats
from scitex_stats._mcp._handlers._run_test import run_test_sync

DATA = [[1., 2., 4., 5.], [3., 5., 7., 9.]]


@pytest.fixture(scope="module")
def mcp_result():
    return run_test_sync("ttest_ind", data=DATA)


@pytest.mark.parametrize("slot,value", [("data2", [99., 101.]),
                                      ("groups", [[99., 101.], [104., 110.]])])
@pytest.mark.parametrize("container", ["list", "ndarray"])
@pytest.mark.parametrize("supply_data", [False, True])
def test_native_only_supplied_slots_cannot_be_ignored(mcp_result, slot, value, container, supply_data):
    # Arrange
    payload = np.asarray(value) if container == "ndarray" else deepcopy(value)
    arguments = {slot: payload}
    arguments.update({"data": deepcopy(DATA)} if supply_data else {})
    before = np.asarray(payload).copy()
    # Act
    report = stats.verify(mcp_result, **arguments)
    checks = {row["name"]: row["status"] for row in report["checks"]}
    inputs = next(row["inputs"] for row in report["checks"] if row["name"] == "inputs")
    # Assert
    assert (report["verified"], checks,
            any(row.get("error") == "not in receipt" for row in inputs),
            np.array_equal(payload, before)) == (
        False, {"receipt": "pass", "result": "pass", "inputs": "fail", "recompute": "skip"},
        True, True,
    )


@pytest.mark.parametrize("supply_data", [False, True])
def test_matching_or_embedded_mcp_data_still_verifies(mcp_result, supply_data):
    # Arrange
    arguments = {"data": deepcopy(DATA)} if supply_data else {}
    # Act
    report = stats.verify(mcp_result, **arguments)
    # Assert
    assert (report["verified"], {row["status"] for row in report["checks"]}) == (
        True, {"pass"},
    )
