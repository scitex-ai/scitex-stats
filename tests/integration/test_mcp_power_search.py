"""Check bounded MCP sample-size searches against independent power solvers."""

import asyncio
from datetime import datetime
import json
from math import ceil

import pytest
from statsmodels.stats.power import FTestAnovaPower, GofChisquarePower

from scitex_stats import _server


def call_tool(**kwargs):
    function = getattr(_server.power_analysis, "fn", _server.power_analysis)
    return json.loads(asyncio.run(function(**kwargs)))


def reference(test_type):
    if test_type == "anova":
        return FTestAnovaPower(), {"k_groups": 3}, 3, 1000
    return GofChisquarePower(), {"n_bins": 3}, 1, 10000


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
@pytest.mark.parametrize("effect_size", [.0001, .001])
def test_unreachable_target_is_an_explicit_failure(test_type, effect_size):
    # Arrange
    solver, options, multiplier, limit = reference(test_type)
    maximum_power = solver.power(effect_size, limit * multiplier, .05, **options)
    # Act
    report = call_tool(test_type=test_type, effect_size=effect_size, power=.8, n_groups=3)
    # Assert
    assert (maximum_power < .8, report) == (
        True, {"success": False, "error": f"Required sample size exceeds supported search limit ({limit})"})


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
@pytest.mark.parametrize("effect_size", [.2, .4, .8])
def test_feasible_minimum_matches_independent_root_solver(test_type, effect_size):
    # Arrange
    solver, options, multiplier, _ = reference(test_type)
    target = .8
    expected = ceil(solver.solve_power(effect_size=effect_size, alpha=.05, power=target, **options) / multiplier)
    # Act
    report = call_tool(test_type=test_type, effect_size=effect_size, power=target, n_groups=3)
    n = report.get("required_n_per_group" if test_type == "anova" else "required_n")
    # Assert
    assert (report["success"], n, solver.power(effect_size, n * multiplier, .05, **options) >= target,
            solver.power(effect_size, (n - 1) * multiplier, .05, **options) < target) == (True, expected, True, True)


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
def test_feasible_solution_at_search_ceiling_is_preserved(test_type):
    # Arrange
    solver, options, multiplier, limit = reference(test_type)
    effect = .03
    target = solver.power(effect, (limit - .25) * multiplier, .05, **options)
    lower_power = solver.power(effect, (limit - 1) * multiplier, .05, **options)
    upper_power = solver.power(effect, limit * multiplier, .05, **options)
    # Act
    report = call_tool(test_type=test_type, effect_size=effect, power=target, n_groups=3)
    # Assert
    assert (lower_power < target <= upper_power, report["success"], report.get("required_n_per_group" if test_type == "anova" else "required_n")) == (True, True, limit)


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
def test_fixed_sample_power_preserves_complete_report(test_type):
    # Arrange
    solver, options, multiplier, _ = reference(test_type)
    expected = {"success": True, "test_type": test_type, "mode": "power_calculation",
                "power": pytest.approx(solver.power(.3, 20 * multiplier, .05, **options)), "alpha": .05}
    expected.update({"n_per_group": 20, "n_groups": 3, "effect_size_f": .3} if test_type == "anova"
                    else {"n": 20, "df": 2, "effect_size_w": .3})
    # Act
    report = call_tool(test_type=test_type, effect_size=.3, n=20, n_groups=3)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, isinstance(timestamp, datetime)) == (expected, True)


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
@pytest.mark.parametrize("effect_size", [3., 5.])
@pytest.mark.parametrize("n_groups", [3, 5])
def test_small_required_sample_matches_exhaustive_reference(test_type, effect_size, n_groups):
    # Arrange
    solver = FTestAnovaPower() if test_type == "anova" else GofChisquarePower()
    options = {"k_groups": n_groups} if test_type == "anova" else {"n_bins": n_groups}
    multiplier, floor = (n_groups, 2) if test_type == "anova" else (1, 1)
    candidates = [(n, solver.power(effect_size, n * multiplier, .05, **options))
                  for n in range(floor, 11)]
    expected = next(n for n, achieved in candidates if achieved >= .8)
    # Act
    report = call_tool(test_type=test_type, effect_size=effect_size, power=.8, n_groups=n_groups)
    # Assert
    assert (report["success"], report.get("required_n_per_group" if test_type == "anova" else "required_n")) == (True, expected)


@pytest.mark.parametrize("test_type", ["anova", "chi2"])
def test_search_remains_minimal_across_previous_floor(test_type):
    # Arrange
    solver, options, multiplier, _ = reference(test_type)
    previous_first = 3 if test_type == "anova" else 11
    target = solver.power(.8, (previous_first - .25) * multiplier, .05, **options)
    lower = solver.power(.8, (previous_first - 1) * multiplier, .05, **options)
    upper = solver.power(.8, previous_first * multiplier, .05, **options)
    # Act
    report = call_tool(test_type=test_type, effect_size=.8, power=target, n_groups=3)
    # Assert
    assert (lower < target <= upper, report["success"], report.get("required_n_per_group" if test_type == "anova" else "required_n")) == (True, True, previous_first)


@pytest.mark.parametrize("n", [0, 1, 2, 3])
def test_correlation_power_rejects_undefined_fisher_sample_size(n):
    # Arrange
    kwargs = {"test_type": "correlation", "effect_size": .3, "n": n}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert report == {"success": False, "error": "n must be greater than 3 for correlation power"}


@pytest.mark.parametrize("n", [4, 5, 30])
@pytest.mark.parametrize("effect_size", [-.3, .3])
def test_valid_correlation_power_matches_independent_normal_reference(n, effect_size):
    # Arrange
    from math import atanh, sqrt
    from statistics import NormalDist

    normal = NormalDist()
    critical = normal.inv_cdf(.975)
    shifted_mean = atanh(effect_size) * sqrt(n - 3)
    expected = {"success": True, "test_type": "correlation", "mode": "power_calculation",
                "power": pytest.approx(normal.cdf(shifted_mean - critical) + normal.cdf(-shifted_mean - critical), abs=1e-12),
                "n": n, "effect_size_r": effect_size, "alpha": .05}
    # Act
    report = call_tool(test_type="correlation", effect_size=effect_size, n=n)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, isinstance(timestamp, datetime)) == (expected, True)
