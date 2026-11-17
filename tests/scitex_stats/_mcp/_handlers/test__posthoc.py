"""Games–Howell output follows the studentized-range reference, not Bonferroni."""

import asyncio
import json

import numpy as np
import pytest
from scipy import stats

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler
from scitex_stats._server import _json

GROUPS = [[1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15], [2, 3, 4, 6, 8, 10, 13]]
# Independent SciPy 1.18.1 tukey_hsd(*GROUPS, equal_var=False) reference.
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html
REFERENCE_P = [0.36279300269403825, 0.33283357941141123, 0.9392457414503831]
REFERENCE_CI = [(-11.145969381244745, 3.7459693812447448),
                (-7.855560120981518, 2.312702978124375),
                (-6.75028507578145, 8.607427932924308)]


def test_games_howell_matches_independent_unequal_size_variance_reference():
    # Arrange
    groups = [list(group) for group in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "B", "C"], "games_howell"))
    # Assert
    assert [row["p_adj"] for row in result["comparisons"]] == pytest.approx(
        REFERENCE_P, rel=1e-10, abs=1e-12,
    )


def test_games_howell_reports_matching_simultaneous_intervals():
    # Arrange
    groups = [list(group) for group in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "B", "C"], "games_howell"))
    intervals = [(row.get("confidence_level"), row.get("ci_lower"), row.get("ci_upper"))
                 for row in result["comparisons"]]
    # Assert
    assert np.asarray(intervals, dtype=float) == pytest.approx(np.column_stack(([0.95] * 3, np.asarray(REFERENCE_CI))), rel=1e-10)


def test_games_howell_wire_decisions_are_json_booleans():
    # Arrange
    groups = [list(group) for group in GROUPS]
    result = asyncio.run(posthoc_test_handler(groups, method="games_howell"))
    # Act
    body = json.loads(_json(result))
    # Assert
    assert [type(row["reject"]) for row in body["comparisons"]] == [bool, bool, bool]


@pytest.mark.parametrize("groups", [GROUPS[:2], [[1, 1, 1], [1, 2, 3, 4]]])
def test_games_howell_two_groups_preserve_welch_statistic_and_raw_probability(groups):
    # Arrange
    samples = groups
    expected = stats.ttest_ind(*samples, equal_var=False)
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="games_howell"))
    row = result["comparisons"][0]
    # Assert
    assert (row["t_statistic"], row["p_value"], row["p_adj"], row["mean_diff"]) == pytest.approx(
        (expected.statistic, expected.pvalue, expected.pvalue,
         np.mean(groups[0]) - np.mean(groups[1])), rel=1e-10,
    )


@pytest.mark.parametrize("groups", [
    [[1, 1], [2, 2], [3, 4]],
    [[1], [2, 3], [4, 5]],
    [[1, float("nan")], [2, 3], [4, 5]],
    [[1, float("inf")], [2, 3], [4, 5]],
    [[[1, 2], [3, 4]], [[2, 3], [4, 5]], [[3, 4], [5, 6]]],
    [[1, 2]],
])
def test_games_howell_rejects_undefined_inputs_instead_of_success(groups):
    # Arrange
    data = groups
    # Act
    result = asyncio.run(posthoc_test_handler(data, method="games_howell"))
    # Assert
    assert result["success"] is False and bool(result.get("error"))


def test_games_howell_wire_rejection_is_true_for_separated_samples():
    # Arrange
    groups = [(np.asarray(group) + offset).tolist()
              for group, offset in zip(GROUPS, [0, 30, 60])]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="games_howell"))
    body = json.loads(_json(result))
    # Assert
    assert [row["reject"] for row in body["comparisons"]] == [True, True, True]
