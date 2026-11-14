"""Preserve Fisher hypotheses across native dispatch and MCP transport."""

import asyncio

import pytest
from scipy import stats

import scitex_stats as ss
from scitex_stats._mcp._handlers._run_test import run_test_handler

TABLE = [[8, 2], [1, 5]]


@pytest.mark.parametrize("alternative", ["two-sided", "less", "greater"])
@pytest.mark.parametrize("input_style", ["groups", "rows"])
def test_native_fisher_dispatch_matches_requested_scipy_hypothesis(
    alternative, input_style
):
    # Arrange
    expected = stats.fisher_exact(TABLE, alternative=alternative)
    inputs = {"groups": TABLE} if input_style == "groups" else {
        "data": TABLE[0], "data2": TABLE[1]
    }
    # Act
    result = ss.run_test("fisher", alternative=alternative, **inputs)
    # Assert
    assert (result["alternative"], result["statistic"], result["pvalue"]) == (
        alternative, pytest.approx(float(expected.statistic)),
        pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("alternative", ["two-sided", "less", "greater"])
def test_mcp_fisher_reference_control(alternative):
    # Arrange
    expected = stats.fisher_exact(TABLE, alternative=alternative)
    # Act
    result = asyncio.run(
        run_test_handler("fisher_exact", data=TABLE, alternative=alternative)
    )
    # Assert
    assert (result["success"], result["alternative"], result["p_value"]) == (
        True, alternative, pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("alternative", ["two-sided", "less", "greater"])
def test_native_fisher_receipt_replays_the_requested_hypothesis(alternative):
    # Arrange
    result = ss.run_test("fisher", groups=TABLE, alternative=alternative)
    # Act
    verified = ss.verify(result, groups=TABLE)
    # Assert
    assert (result["alternative"], verified["verified"]) == (alternative, True)


def test_chi_square_remains_a_nondirectional_contingency_test():
    # Arrange
    expected = stats.chi2_contingency(TABLE)
    # Act
    result = ss.run_test("chi2", groups=TABLE)
    # Assert
    assert (result["statistic"], result["pvalue"]) == (
        pytest.approx(float(expected.statistic)),
        pytest.approx(float(expected.pvalue)),
    )
