"""Grouped NumPy inputs retain provenance verification and tamper detection."""

from copy import deepcopy

import numpy as np
import pytest

import scitex_stats as stats
from scitex_stats._mcp._handlers._run_test import run_test_sync

GROUPS = [[1., 2., 4., 5.], [3., 5., 7., 9.], [6., 8., 10., 13.]]


def _result(api):
    if api == "native":
        return stats.run_test("anova", groups=GROUPS)
    return run_test_sync("anova", data=GROUPS)


@pytest.mark.parametrize("api", ["native", "mcp"])
@pytest.mark.parametrize("container", ["list", "ndarray"])
@pytest.mark.parametrize("tampered", [False, True])
def test_supplied_groups_verify_equally_and_tampering_is_rejected(api, container, tampered):
    # Arrange
    result = _result(api)
    supplied = deepcopy(GROUPS)
    supplied[0][0] += .25 if tampered else 0.
    supplied = np.asarray(supplied) if container == "ndarray" else supplied
    before = np.asarray(supplied).copy()
    slot = "groups" if api == "native" else "data"
    # Act
    report = stats.verify(result, **{slot: supplied})
    statuses = {row["name"]: row["status"] for row in report["checks"]}
    # Assert
    assert {"verified": report["verified"], "checks": statuses,
            "input_preserved": np.array_equal(supplied, before)} == {
        "verified": not tampered,
        "checks": {"receipt": "pass", "result": "pass",
                   "inputs": "fail" if tampered else "pass",
                   "recompute": "skip" if tampered else "pass"},
        "input_preserved": True,
    }


@pytest.mark.parametrize("api", ["native", "mcp"])
def test_changed_array_shape_fails_input_verification(api):
    # Arrange
    result = _result(api)
    wrong_shape = np.asarray(GROUPS)[:, 0]
    slot = "groups" if api == "native" else "data"
    # Act
    report = stats.verify(result, **{slot: wrong_shape})
    statuses = {row["name"]: row["status"] for row in report["checks"]}
    # Assert
    assert (report["verified"], statuses["inputs"], statuses["recompute"]) == (False, "fail", "skip")
