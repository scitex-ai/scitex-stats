"""Dunnett uses a shared-error multiple-to-control distribution, not Bonferroni."""

import asyncio
import json

import pytest

from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler
from scitex_stats._server import _json

CONTROL = [2.9, 3.0, 2.5, 2.6, 3.2]
TREATMENTS = [[3.8, 2.7, 4.0, 2.4], [2.8, 3.4, 3.7, 2.2, 2.0]]
GROUPS = [CONTROL, *TREATMENTS]
# Published SciPy dunnett example; randomized integration is approximate.
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.dunnett.html
STATISTICS = [0.90874545, -0.05007117]
PROBABILITIES = [0.58325114, 0.99819341]


def test_dunnett_statistics_use_error_pooled_across_all_groups():
    # Arrange
    groups = [list(g) for g in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunnett"))
    # Assert
    assert [r["t_statistic"] for r in result["comparisons"]] == pytest.approx(
        STATISTICS, rel=1e-7, abs=1e-8,
    )


def test_dunnett_family_probabilities_match_the_published_reference():
    # Arrange
    groups = [list(g) for g in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunnett"))
    # Assert: published randomized-QMC values can vary at integration precision.
    assert [r["p_adj"] for r in result["comparisons"]] == pytest.approx(
        PROBABILITIES, rel=0, abs=2e-4,
    )


def test_dunnett_published_drug_example_matches_independent_family_probabilities():
    # Arrange: SciPy1.11.4 reference [0.62004941,0.0059035], explicitly may vary.
    groups = [[7.4, 8.5, 7.2, 8.24, 9.84, 8.32],
              [9.76, 8.8, 7.68, 9.36], [12.8, 9.68, 12.16, 9.2, 10.55]]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, method="dunnett"))
    # Assert
    assert [r["p_adj"] for r in result["comparisons"]] == pytest.approx(
        [0.62004941, 0.0059035], rel=0, abs=2e-4,
    )


def test_reordered_control_preserves_treatment_order_and_reference_statistics():
    # Arrange
    groups = [TREATMENTS[0], CONTROL, TREATMENTS[1]]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "control", "B"], "dunnett", 1))
    # Assert
    assert {"pairs": [(r["group"], r["vs_control"]) for r in result["comparisons"]],
            "statistics": [r["t_statistic"] for r in result["comparisons"]]} == {
        "pairs": [("A", "control"), ("B", "control")],
        "statistics": pytest.approx(STATISTICS, rel=1e-7, abs=1e-8),
    }


def test_dunnett_wire_decisions_are_booleans_with_strict_json_values():
    # Arrange
    result = asyncio.run(posthoc_test_handler(GROUPS, method="dunnett"))
    # Act
    payload = json.loads(_json(result))
    json.dumps(payload, allow_nan=False)
    # Assert
    assert [type(r["reject"]) for r in payload["comparisons"]] == [bool, bool]


@pytest.mark.parametrize("groups", [
    [[1., 1.], [1., 1.], [2., 2.]],
    [[1.], [2.], [3.]],
    [[1., float("nan")], [2., 3.], [4., 5.]],
    [[1., float("inf")], [2., 3.], [4., 5.]],
    [[], [2., 3.], [4., 5.]],
])
def test_dunnett_undefined_inputs_return_error_without_comparisons(groups):
    # Arrange
    data = groups
    # Act
    result = asyncio.run(posthoc_test_handler(data, method="dunnett"))
    # Assert
    assert (result["success"], "comparisons" in result, bool(result.get("error"))) == (
        False, False, True,
    )


def test_dunnett_integration_is_repeatable_and_inputs_are_preserved():
    # Arrange
    groups = [list(g) for g in GROUPS]
    first = asyncio.run(posthoc_test_handler(groups, method="dunnett"))
    # Act
    second = asyncio.run(posthoc_test_handler(groups, method="dunnett"))
    # Assert
    assert (second["comparisons"], groups) == (first["comparisons"], GROUPS)
