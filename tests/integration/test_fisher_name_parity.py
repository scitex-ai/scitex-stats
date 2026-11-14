"""Equivalent Fisher names preserve scientific inputs, output and provenance."""

import asyncio

import pytest
from scipy import stats

import scitex_stats as ss
from scitex_stats._mcp._handlers._run_test import run_test_handler

TABLE = [[8, 2], [1, 5]]
NAMES = ["fisher", "fisher_exact"]


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("alternative", ["two-sided", "less", "greater"])
@pytest.mark.parametrize("input_style", ["groups", "rows"])
def test_native_fisher_names_match_scipy(name, alternative, input_style):
    # Arrange
    expected = stats.fisher_exact(TABLE, alternative=alternative)
    inputs = {"groups": TABLE} if input_style == "groups" else {
        "data": TABLE[0], "data2": TABLE[1]
    }
    # Act
    result = ss.run_test(name, alternative=alternative, **inputs)
    # Assert
    assert (result["alternative"], result["statistic"], result["pvalue"]) == (
        alternative, pytest.approx(float(expected.statistic)),
        pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("alternative", ["two-sided", "less", "greater"])
def test_mcp_fisher_names_match_scipy(name, alternative):
    # Arrange
    expected = stats.fisher_exact(TABLE, alternative=alternative)
    # Act
    result = asyncio.run(
        run_test_handler(name, data=TABLE, alternative=alternative)
    )
    # Assert
    assert (result["success"], result.get("test_name"), result.get("p_value")) == (
        True, name, pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("alternative", ["less", "greater"])
def test_native_fisher_receipt_preserves_name_and_hypothesis(name, alternative):
    # Arrange
    result = ss.run_test(name, groups=TABLE, alternative=alternative)
    # Act
    verification = ss.verify(result, groups=TABLE)
    test = result["provenance"]["test"]
    # Assert
    assert (test["name"], test["parameters"]["alternative"],
            verification["verified"]) == (name, alternative, True)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("alternative", ["less", "greater"])
def test_mcp_fisher_receipt_preserves_name_and_hypothesis(name, alternative):
    # Arrange
    result = asyncio.run(
        run_test_handler(name, data=TABLE, alternative=alternative)
    )
    # Act
    verification = ss.verify(result, groups=TABLE)
    test = result["provenance"]["test"]
    # Assert
    assert (test["name"], test["parameters"]["alternative"],
            verification["verified"]) == (name, alternative, True)


@pytest.mark.parametrize("plot_spec", [False, True])
@pytest.mark.parametrize("input_style", ["groups", "rows"])
def test_native_fisher_alias_retains_count_table_output(plot_spec, input_style):
    # Arrange
    inputs = {"groups": TABLE} if input_style == "groups" else {
        "data": TABLE[0], "data2": TABLE[1]
    }
    original = ss.run_test("fisher", plot_spec=plot_spec, **inputs)
    # Act
    alias = ss.run_test("fisher_exact", plot_spec=plot_spec, **inputs)
    payload = {k: v for k, v in alias.items() if k != "provenance"}
    expected = {k: v for k, v in original.items() if k != "provenance"}
    # Assert: count cells must not become continuous sample descriptives.
    assert (payload, "descriptives" in alias,
            alias.get("plot_spec", {}).get("kind")) == (
        expected, False, "contingency" if plot_spec else None,
    )


def test_fisher_names_are_discoverable_in_the_native_dispatcher():
    # Arrange
    names = set(ss.available_tests())
    # Act
    accepted = set(NAMES) & names
    # Assert
    assert accepted == set(NAMES)
