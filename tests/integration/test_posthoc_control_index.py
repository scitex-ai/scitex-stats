"""Control selection cannot silently include the control as a treatment."""

import asyncio
from copy import deepcopy

import pytest

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

GROUPS = [[1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15], [2, 3, 4, 6, 8, 10, 13]]
NAMES = ["A", "B", "C"]


@pytest.mark.parametrize("index", [-1, -2, -3, -4, 3, 99])
def test_out_of_range_control_index_returns_explicit_error_without_comparisons(index):
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, NAMES, "dunnett", index))
    # Assert
    assert {"success": result["success"],
            "control_error": "control_group" in result.get("error", ""),
            "comparisons": "comparisons" in result,
            "inputs_unchanged": groups == GROUPS} == {
        "success": False, "control_error": True,
        "comparisons": False, "inputs_unchanged": True,
    }


@pytest.mark.parametrize("index", [0, 1, 2])
def test_valid_zero_based_control_selects_every_other_group_once(index):
    # Arrange: this tests group mapping, not the known method approximation.
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, NAMES, "dunnett", index))
    # Assert
    assert {"success": result["success"], "count": result["n_comparisons"],
            "pairs": [(r["group"], r["vs_control"]) for r in result["comparisons"]],
            "inputs_unchanged": groups == GROUPS} == {
        "success": True, "count": 2,
        "pairs": [(name, NAMES[index]) for i, name in enumerate(NAMES) if i != index],
        "inputs_unchanged": True,
    }


@pytest.mark.parametrize("method", ["tukey", "games_howell", "dunn"])
def test_methods_without_control_preserve_their_existing_ignored_parameter(method):
    # Arrange
    groups = deepcopy(GROUPS)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, NAMES, method, -1))
    # Assert
    assert (result["success"], result["n_comparisons"], groups == GROUPS) == (True, 3, True)
