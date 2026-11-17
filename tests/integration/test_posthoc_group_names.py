"""Post-hoc names must identify every input group without silent merging."""

import asyncio
from copy import deepcopy

import pytest

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

GROUPS = [[1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15], [2, 3, 4, 6, 8, 10, 13]]
METHODS = ["tukey", "dunnett", "games_howell", "dunn"]


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("names", [[], ["A", "B"], ["A", "B", "C", "D"], ["A", "A", "B"]])
def test_incomplete_extra_or_duplicate_labels_return_an_explicit_error(method, names):
    # Arrange
    groups = deepcopy(GROUPS)
    labels = list(names)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, labels, method))
    # Assert
    assert {"success": result["success"],
            "label_error": "group_names" in result.get("error", ""),
            "comparisons": "comparisons" in result,
            "preserved": groups == GROUPS and labels == names} == {
        "success": False, "label_error": True, "comparisons": False, "preserved": True,
    }


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("names", [None, ["Z", "A", "M"]])
def test_omitted_or_unique_labels_retain_every_expected_pair(method, names):
    # Arrange
    groups = deepcopy(GROUPS)
    labels = deepcopy(names)
    expected_names = names if names is not None else ["Group_1", "Group_2", "Group_3"]
    expected_pairs = ({(expected_names[i], expected_names[0]) for i in [1, 2]}
                      if method == "dunnett" else
                      {frozenset((expected_names[i], expected_names[j]))
                       for i in range(3) for j in range(i + 1, 3)})
    # Act
    result = asyncio.run(posthoc_test_handler(groups, labels, method))
    rows = result["comparisons"]
    pairs = ({(r["group"], r["vs_control"]) for r in rows} if method == "dunnett" else
             {frozenset((r["group1"], r["group2"])) for r in rows})
    # Assert
    assert {"success": result["success"], "pairs": pairs,
            "count": result["n_comparisons"],
            "preserved": groups == GROUPS and labels == names} == {
        "success": True, "pairs": expected_pairs,
        "count": 2 if method == "dunnett" else 3, "preserved": True,
    }
