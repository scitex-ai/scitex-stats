"""Compare both Games-Howell interfaces with SciPy's independent implementation."""

import asyncio

import numpy as np
import pytest

scipy = pytest.importorskip("scipy", minversion="1.16")
from scipy import stats

from scitex_stats.posthoc import posthoc_games_howell
from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler


@pytest.fixture
def groups():
    return [np.array(x, dtype=float) for x in [
        [0, 1, 2, 3, 4], [1, 2, 5, 9, 12, 14], [5, 6, 6, 7, 9, 10, 11],
    ]]


@pytest.mark.parametrize("alpha", [0.05, 0.10])
def test_python_games_howell_probability_matches_scipy(groups, alpha):
    # Arrange
    reference = stats.tukey_hsd(*groups, equal_var=False)
    pairs = [(i, j) for i in range(3) for j in range(i + 1, 3)]
    expected = [round(float(reference.pvalue[i, j]), 4) for i, j in pairs]
    # Act
    result = posthoc_games_howell(groups, alpha=alpha, return_as="dict")
    # Assert
    assert [r["pvalue"] for r in result] == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("alpha", [0.05, 0.10])
def test_python_games_howell_intervals_match_scipy(groups, alpha):
    # Arrange
    interval = stats.tukey_hsd(*groups, equal_var=False).confidence_interval(1 - alpha)
    pairs = [(i, j) for i in range(3) for j in range(i + 1, 3)]
    expected = [round(float(value), 3) for i, j in pairs
                for value in (interval.low[i, j], interval.high[i, j])]
    # Act
    result = posthoc_games_howell(groups, alpha=alpha, return_as="dict")
    observed = [r[key] for r in result for key in ("ci_lower", "ci_upper")]
    # Assert
    assert observed == pytest.approx(expected, abs=1e-12)


def test_mcp_games_howell_adjusted_probability_matches_scipy(groups):
    # Arrange
    reference = stats.tukey_hsd(*groups, equal_var=False)
    expected = [float(reference.pvalue[i, j]) for i in range(3) for j in range(i + 1, 3)]
    # Act
    result = asyncio.run(posthoc_test_handler(
        groups=[g.tolist() for g in groups], method="games_howell",
    ))
    # Assert
    assert [r["p_adj"] for r in result["comparisons"]] == pytest.approx(expected, abs=1e-12)


def test_mcp_games_howell_retains_welch_diagnostic_probability(groups):
    # Arrange
    expected = [float(stats.ttest_ind(groups[i], groups[j], equal_var=False).pvalue)
                for i in range(3) for j in range(i + 1, 3)]
    # Act
    result = asyncio.run(posthoc_test_handler(
        groups=[g.tolist() for g in groups], method="games_howell",
    ))
    # Assert
    assert [r["p_value"] for r in result["comparisons"]] == pytest.approx(expected, abs=1e-12)


def test_python_significance_and_stars_use_the_adjusted_probability(groups):
    # Arrange
    reference = stats.tukey_hsd(*groups, equal_var=False)
    probabilities = [float(reference.pvalue[i, j]) for i in range(3) for j in range(i + 1, 3)]
    def stars(value):
        return "***" if value < 0.001 else "**" if value < 0.01 else "*" if value < 0.05 else "ns"
    expected = [(p < 0.05, stars(p)) for p in probabilities]
    # Act
    result = posthoc_games_howell(groups, return_as="dict")
    # Assert
    assert [(r["significant"], r["pstars"]) for r in result] == expected


def test_python_games_howell_refuses_zero_standard_error():
    # Arrange
    groups = [[0.0] * 4, [1.0] * 4]
    # Act
    # Assert
    with pytest.raises(ValueError, match="finite positive standard error"):
        posthoc_games_howell(groups, return_as="dict")


def test_mcp_games_howell_reports_zero_standard_error_as_failure():
    # Arrange
    groups = [[0.0] * 4, [1.0] * 4]
    # Act
    result = asyncio.run(posthoc_test_handler(groups=groups, method="games_howell"))
    # Assert
    assert (result["success"], result["error"]) == (
        False, "Games-Howell requires finite positive standard error and degrees of freedom",
    )
