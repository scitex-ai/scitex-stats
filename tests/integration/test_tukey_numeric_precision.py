"""Tukey numeric results retain precision before presentation formatting."""

import asyncio
import json

import numpy as np
import pytest

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

GROUPS = [[1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15], [2, 3, 4, 6, 8, 10, 13]]
# Independent scipy.stats.tukey_hsd reference, same equal-variance method.
REFERENCE_P = [0.3539129796144884, 0.5266372523778904, 0.9203741958565332]
REFERENCE_INTERVALS = [[-3.0469337922297353, 10.446933792229736],
                       [-3.7527724524165054, 9.295629595273649],
                       [-7.1275161584004225, 5.270373301257565]]


def test_tukey_probabilities_match_full_precision_reference():
    # Arrange
    groups = [list(group) for group in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "B", "C"], "tukey"))
    # Assert
    assert [row["p_adj"] for row in result["comparisons"]] == pytest.approx(
        REFERENCE_P, rel=1e-10, abs=1e-12,
    )


def test_tukey_intervals_and_differences_keep_precision_and_existing_direction():
    # Arrange: adapter differences remain group2 minus group1.
    expected = np.column_stack(([3.7, 2.7714285714285714, -0.9285714285714288],
                                REFERENCE_INTERVALS))
    # Act
    result = asyncio.run(posthoc_test_handler(GROUPS, ["A", "B", "C"], "tukey"))
    rows = [[r["mean_diff"], r["ci_lower"], r["ci_upper"]] for r in result["comparisons"]]
    # Assert
    assert np.asarray(rows) == pytest.approx(expected, rel=1e-10, abs=1e-12)


def test_tukey_small_representable_probabilities_remain_positive():
    # Arrange: the old four-decimal display table rounded all three to zero.
    groups = [[0, 1, 2, 3, 4], [8, 9, 10, 11, 12], [16, 17, 18, 19, 20]]
    expected = [1.0433084891126043e-5, 5.216605813984643e-9, 1.0433084891126043e-5]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "B", "C"], "tukey"))
    # Assert
    assert [row["p_adj"] for row in result["comparisons"]] == pytest.approx(
        expected, rel=1e-7, abs=1e-15,
    )


def test_tukey_sorted_pairs_keep_labels_inputs_boolean_decisions_and_strict_json():
    # Arrange
    groups = [list(group) for group in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["Z", "A", "M"], "tukey"))
    rows = json.loads(json.dumps(result, allow_nan=False))["comparisons"]
    # Assert
    assert {"pairs": [(r["group1"], r["group2"]) for r in rows],
            "directions": [np.sign(r["mean_diff"]) for r in rows],
            "booleans": [type(r["reject"]) is bool for r in rows],
            "inputs_unchanged": groups == GROUPS} == {
        "pairs": [("A", "M"), ("A", "Z"), ("M", "Z")],
        "directions": [-1, -1, -1], "booleans": [True] * 3,
        "inputs_unchanged": True,
    }
