"""Dunn ranks, adjustment policy and wire types follow the native expert."""

import asyncio
import json
from copy import deepcopy

import numpy as np
import pytest

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler
from scitex_stats._server import _json
from scitex_stats.posthoc._auto import _dunn

GROUPS = [[1, 1, 2, 2, 3], [2, 3, 3, 4, 4, 5], [3, 4, 4, 5, 5, 6, 6]]
# Independent scikit-posthocs0.18.0 posthoc_dunn reference, synthetic inputs.
RAW = [.06835917756213984, .0012327992784233223, .1564927158324166]
BONFERRONI = [.20507753268641954, .003698397835269967, .4694781474972498]
HOLM = [.13671835512427968, .003698397835269967, .1564927158324166]
TAIL = 2.5239394239903128e-34


def test_mcp_dunn_tied_rank_probabilities_match_independent_reference():
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunn"))
    # Assert
    assert [row["p_adj"] for row in result["comparisons"]] == pytest.approx(BONFERRONI, rel=1e-10, abs=1e-12)


def test_mcp_dunn_raw_probabilities_match_independent_reference():
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunn"))
    # Assert
    assert [row["p_value"] for row in result["comparisons"]] == pytest.approx(RAW, rel=1e-10, abs=1e-12)


def test_mcp_dunn_decisions_are_wire_booleans():
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    body = json.loads(_json(asyncio.run(posthoc_test_handler(groups, method="dunn"))))
    # Assert
    assert {"types": [type(row["reject"]) for row in body["comparisons"]],
            "values": [row["reject"] for row in body["comparisons"]]} == {
        "types": [bool] * 3, "values": [False, True, False],
    }


def test_mcp_dunn_retains_representable_small_tail_probabilities():
    # Arrange
    groups = [list(range(100)), list(range(100, 200))]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunn"))
    # Assert
    assert result["comparisons"][0]["p_adj"] == pytest.approx(TAIL, rel=1e-10, abs=0)


@pytest.mark.parametrize("groups", [
    [[1, 1], [1, 1], [1, 1]],
    [[1, float("nan")], [2, 3], [3, 4]],
    [[], [2, 3], [3, 4]],
    [[1, 2]],
    [[[1, 2]], [[3, 4]], [[5, 6]]],
])
def test_mcp_dunn_unusable_rank_inputs_return_explicit_error(groups):
    # Arrange
    inputs = deepcopy(groups)
    # Act
    result = asyncio.run(posthoc_test_handler(inputs, method="dunn"))
    # Assert
    assert {"success": result["success"], "error": "error" in result,
            "comparisons": "comparisons" in result} == {
        "success": False, "error": True, "comparisons": False,
    }


def test_native_dunn_default_remains_holm():
    # Arrange
    groups = [np.asarray(group, dtype=float) for group in GROUPS]
    # Act
    rows = _dunn(groups, alpha=.05, level=.95)
    # Assert
    assert [row["p_adjusted"] for row in rows] == pytest.approx(HOLM, rel=1e-10, abs=1e-12)


def test_native_dunn_can_supply_bonferroni_to_its_adapter():
    # Arrange
    groups = [np.asarray(group, dtype=float) for group in GROUPS]
    # Act
    rows = _dunn(groups, alpha=.05, level=.95, correction="bonferroni")
    # Assert
    assert [row["p_adjusted"] for row in rows] == pytest.approx(BONFERRONI, rel=1e-10, abs=1e-12)


def test_mcp_dunn_preserves_input_and_requested_label_order():
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["z", "a", "m"], "dunn"))
    # Assert
    assert {"inputs": groups, "labels": [(r["group1"], r["group2"]) for r in result["comparisons"]]} == {
        "inputs": GROUPS, "labels": [("z", "a"), ("z", "m"), ("a", "m")],
    }
