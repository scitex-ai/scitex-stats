"""Check post-hoc design admission without qualifying numerical procedures."""

import asyncio
import copy
from datetime import datetime
import json

import pytest

from scitex_stats import _server

METHODS = ("tukey", "dunnett", "games_howell", "dunn")
GROUPS = [[1., 2., 4., 7.], [3., 5., 8., 9.], [2., 6., 10., 13.]]


def call_tool(**kwargs):
    function = getattr(_server.posthoc_test, "fn", _server.posthoc_test)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("groups", [[], [[1., 2., 3.]]])
def test_posthoc_requires_at_least_two_groups(method, groups):
    # Arrange
    kwargs = {"method": method, "groups": groups}
    before = copy.deepcopy(kwargs)
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert (report, kwargs) == ({"success": False, "error": "At least two groups are required for post-hoc comparisons"}, before)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("names", [["Control", "A"], ["Control", "A", "B", "Extra"]])
def test_posthoc_names_match_every_group(method, names):
    # Arrange
    kwargs = {"method": method, "groups": copy.deepcopy(GROUPS), "group_names": names}
    before = copy.deepcopy(kwargs)
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert (report, kwargs) == ({"success": False, "error": "group_names must match the number of groups"}, before)


@pytest.mark.parametrize("control", [-2, -1, 3, 9])
def test_dunnett_control_must_be_an_existing_nonnegative_index(control):
    # Arrange
    kwargs = {"method": "dunnett", "groups": copy.deepcopy(GROUPS), "control_group": control}
    before = copy.deepcopy(kwargs)
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert (report, kwargs) == ({"success": False, "error": "control_group must be an index from 0 to the number of groups minus 1"}, before)


@pytest.mark.parametrize("control", [0, 1, 2])
@pytest.mark.parametrize("names", [None, [], ["Control", "A", "B"]])
def test_valid_dunnett_control_preserves_comparison_identity_and_fields(control, names):
    # Arrange
    kwargs = {"method": "dunnett", "groups": copy.deepcopy(GROUPS), "group_names": copy.deepcopy(names), "control_group": control}
    before = copy.deepcopy(kwargs)
    labels = names or ["Group_1", "Group_2", "Group_3"]
    expected = [(name, labels[control]) for i, name in enumerate(labels) if i != control]
    keys = {"group", "vs_control", "mean_diff", "t_statistic", "p_value", "p_adj", "reject"}
    # Act
    report = call_tool(**kwargs)
    timestamp = datetime.fromisoformat(report["timestamp"])
    rows = report["comparisons"]
    # Assert
    assert (set(report), report["success"], report["method"], report["n_groups"], report["n_comparisons"],
            [(row["group"], row["vs_control"]) for row in rows], all(set(row) == keys for row in rows),
            isinstance(timestamp, datetime), kwargs) == (
                {"success", "method", "n_groups", "n_comparisons", "comparisons", "timestamp"}, True,
                "dunnett", 3, 2, expected, True, True, before)
