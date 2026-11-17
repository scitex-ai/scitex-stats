"""A bounded sample-size result must attain the requested target power."""

import asyncio

import pytest
from statsmodels.stats.power import FTestAnovaPower, GofChisquarePower

from scitex_stats._mcp._handlers._power import power_analysis_handler

MODELS = [("anova", 3, 2, 1000, "required_n_per_group"),
          ("chi2", 4, 10, 10000, "required_n")]


def _reference(test_type, effect_size, n, groups):
    if test_type == "anova":
        return FTestAnovaPower().power(effect_size, nobs=n * groups, alpha=.05, k_groups=groups)
    return GofChisquarePower().power(effect_size, nobs=n, alpha=.05, n_bins=groups)


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
@pytest.mark.parametrize("goal", [.8, .95])
def test_unattained_target_is_not_reported_as_a_required_sample_size(test_type, groups, lower, upper, key, goal):
    # Arrange
    effect_size = .001
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, power=goal, n_groups=groups))
    # Assert
    assert {"success": result["success"], "required": key in result,
            "range_error": str(upper) in result.get("error", "")} == {
        "success": False, "required": False, "range_error": True,
    }


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
def test_feasible_lower_bound_is_returned_without_an_off_by_one(test_type, groups, lower, upper, key):
    # Arrange
    effect_size = 10.
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, n_groups=groups))
    # Assert
    assert (result["success"], result[key]) == (True, lower)


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
def test_required_size_attains_target_and_previous_supported_size_does_not(test_type, groups, lower, upper, key):
    # Arrange
    effect_size, goal = .3, .8
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, power=goal, n_groups=groups))
    n = result[key]
    # Assert
    assert {"success": result["success"], "within_range": lower <= n <= upper,
            "attains": _reference(test_type, effect_size, n, groups) >= goal,
            "minimal": n == lower or _reference(test_type, effect_size, n - 1, groups) < goal} == {
        "success": True, "within_range": True, "attains": True, "minimal": True,
    }


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
def test_supported_upper_bound_can_be_returned_when_it_reaches_the_goal(test_type, groups, lower, upper, key):
    # Arrange: independent power model puts target between upper-1 and upper.
    effect_size = .05 if test_type == "anova" else .02
    goal = _reference(test_type, effect_size, upper, groups) - 1e-8
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, power=goal, n_groups=groups))
    # Assert
    assert (result["success"], result[key]) == (True, upper)


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
@pytest.mark.parametrize("goal", [0., 1., -.1, 1.1, float("nan")])
def test_invalid_target_power_returns_an_explicit_error(test_type, groups, lower, upper, key, goal):
    # Arrange
    effect_size = .3
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, power=goal, n_groups=groups))
    # Assert
    assert (result["success"], key in result, bool(result.get("error"))) == (False, False, True)


@pytest.mark.parametrize("test_type,groups,lower,upper,key", MODELS)
def test_fixed_n_power_matches_the_independent_model(test_type, groups, lower, upper, key):
    # Arrange
    effect_size, n = .3, 40
    expected = _reference(test_type, effect_size, n, groups)
    # Act
    result = asyncio.run(power_analysis_handler(test_type, effect_size, n=n, n_groups=groups))
    # Assert
    assert result["power"] == pytest.approx(expected, rel=1e-12, abs=1e-14)
