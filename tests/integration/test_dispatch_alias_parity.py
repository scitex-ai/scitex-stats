"""Accept the same existing scientific test aliases across Python and MCP."""

import asyncio
import inspect

import numpy as np
import pytest
from scipy import stats
import scitex_stats as ss
from scitex_stats._mcp._handlers._run_test import run_test_handler

CASES = [
    ("ttest", "ttest_ind", "ttest_ind"),
    ("ttest_rel", "ttest_paired", "ttest_rel"),
    ("brunnermunzel", "brunner_munzel", "brunnermunzel"),
    ("mann_whitney", "mannwhitneyu", "mannwhitneyu"),
]


@pytest.fixture
def samples():
    return [1.0, 2.0, 4.0, 8.0, 16.0, 32.0], [0.0, 1.0, 3.0, 6.0, 10.0, 11.0]


@pytest.mark.parametrize("alias, canonical, scipy_name", CASES)
@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
def test_mcp_existing_python_alias_matches_scipy(samples, alias, canonical, scipy_name, alternative):
    # Arrange
    x, y = samples
    expected = getattr(stats, scipy_name)(x, y, alternative=alternative)
    native = ss.run_test(alias, data=x, data2=y, alternative=alternative)
    # Act
    result = asyncio.run(run_test_handler(alias, data=[x, y], alternative=alternative))
    # Assert
    assert (result["success"], result.get("statistic"), result.get("p_value"),
            native["statistic"], native["pvalue"], result.get("test_name")) == (
                True, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
                pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)), alias,
            )


def test_mcp_paired_alias_omits_nan_positions_together():
    # Arrange
    x = np.array([1.0, np.nan, 3.0, 4.0, 8.0, 12.0])
    y = np.array([0.0, 1.0, np.nan, 2.0, 4.0, 8.0])
    mask = np.isfinite(x) & np.isfinite(y)
    expected = stats.ttest_rel(x[mask], y[mask])
    # Act
    result = asyncio.run(run_test_handler("ttest_rel", data=[x.tolist(), y.tolist()]))
    # Assert
    assert (result["success"], result.get("statistic"), result.get("p_value")) == (
        True, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("alias, canonical, scipy_name", CASES)
def test_alias_receipt_retains_requested_name_and_verifies(samples, alias, canonical, scipy_name):
    # Arrange
    x, y = samples
    # Act
    result = asyncio.run(run_test_handler(alias, data=[x, y]))
    verified = ss.verify(result, groups=[x, y])
    # Assert
    assert (result.get("provenance", {}).get("test", {}).get("name"), verified["verified"]) == (
        alias, True,
    )


@pytest.mark.parametrize("alias, canonical, scipy_name", CASES)
def test_python_alias_and_mcp_canonical_bind_to_the_same_owner(alias, canonical, scipy_name):
    # Arrange
    from scitex_stats import tests
    from scitex_stats._dispatch import _ALIASES
    from scitex_stats._mcp._handlers._run_test import _TEST_DISPATCH

    category, function = _TEST_DISPATCH[canonical]
    # Act
    native = getattr(tests, _ALIASES[alias])
    mcp_owner = getattr(getattr(tests, category), function)
    # Assert
    assert inspect.unwrap(native) is inspect.unwrap(mcp_owner)


@pytest.mark.parametrize("name", ["made_up_test", "ttest_welch"])
def test_mcp_still_refuses_unknown_names_and_unimplemented_welch_mode(samples, name):
    # Arrange: Welch is a mode with different semantics, not a spelling alias.
    x, y = samples
    # Act
    result = asyncio.run(run_test_handler(name, data=[x, y]))
    # Assert
    assert (result["success"], result["error"].startswith("Unknown test:")) == (False, True)
