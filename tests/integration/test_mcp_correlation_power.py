"""Exercise correlation-power domain contracts and independent normal references."""

import asyncio
from datetime import datetime
import json

import pytest

from scitex_stats import _server

INVALID_PROBABILITIES = [-.1, 0., 1., 1.1, float("nan"), float("inf")]


def call_tool(**kwargs):
    function = getattr(_server.power_analysis, "fn", _server.power_analysis)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("n", [0, 1, 2, 3])
def test_correlation_power_rejects_undefined_fisher_sample_size(n):
    # Arrange
    kwargs = {"test_type": "correlation", "effect_size": .3, "n": n}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert report == {"success": False, "error": "n must be greater than 3 for correlation power"}


@pytest.mark.parametrize("alpha", [.01, .05, .1])
@pytest.mark.parametrize("n", [4, 5, 30])
@pytest.mark.parametrize("effect_size", [-.999, -.3, 0., .3, .999])
def test_valid_correlation_power_matches_independent_normal_reference(n, effect_size, alpha):
    # Arrange
    from math import atanh, sqrt
    from statistics import NormalDist

    normal = NormalDist()
    critical = normal.inv_cdf(1 - alpha / 2)
    shifted_mean = atanh(effect_size) * sqrt(n - 3)
    expected = {"success": True, "test_type": "correlation", "mode": "power_calculation",
                "power": pytest.approx(normal.cdf(shifted_mean - critical) + normal.cdf(-shifted_mean - critical), abs=1e-12),
                "n": n, "effect_size_r": effect_size, "alpha": alpha}
    # Act
    report = call_tool(test_type="correlation", effect_size=effect_size, n=n, alpha=alpha)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, isinstance(timestamp, datetime)) == (expected, True)


@pytest.mark.parametrize("n", [None, 30])
@pytest.mark.parametrize("effect_size", [-2., -1., 1., 2., float("nan"), float("inf"), -float("inf")])
def test_correlation_power_rejects_out_of_range_and_nonfinite_effects(n, effect_size):
    # Arrange
    kwargs = {"test_type": "correlation", "effect_size": effect_size, "n": n}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert report == {"success": False, "error": "effect_size must be finite and strictly between -1 and 1 for correlation power"}


@pytest.mark.parametrize("n", [None, 30])
@pytest.mark.parametrize("alpha", INVALID_PROBABILITIES)
def test_correlation_power_rejects_invalid_significance_level(n, alpha):
    # Arrange
    kwargs = {"test_type": "correlation", "effect_size": .3, "n": n, "alpha": alpha}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert report == {"success": False, "error": "alpha must be finite and strictly between 0 and 1 for correlation power"}


@pytest.mark.parametrize("power", INVALID_PROBABILITIES)
def test_correlation_sample_size_rejects_invalid_target_power(power):
    # Arrange
    kwargs = {"test_type": "correlation", "effect_size": .3, "power": power}
    # Act
    report = call_tool(**kwargs)
    # Assert
    assert report == {"success": False, "error": "power must be finite and strictly between 0 and 1 for correlation sample size"}


@pytest.mark.parametrize("effect_size", [-.3, .3])
@pytest.mark.parametrize("alpha", [.01, .1])
@pytest.mark.parametrize("power", [.5, .9])
def test_valid_correlation_sample_size_preserves_fisher_inverse(effect_size, alpha, power):
    # Arrange
    from math import atanh, ceil
    from statistics import NormalDist

    normal = NormalDist()
    expected_n = ceil(((normal.inv_cdf(1 - alpha / 2) + normal.inv_cdf(power)) / atanh(effect_size)) ** 2 + 3)
    expected = {"success": True, "test_type": "correlation", "mode": "sample_size_calculation",
                "required_n": expected_n, "effect_size_r": effect_size, "target_power": power, "alpha": alpha}
    # Act
    report = call_tool(test_type="correlation", effect_size=effect_size, alpha=alpha, power=power)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, isinstance(timestamp, datetime)) == (expected, True)


@pytest.mark.parametrize("unused_power", [0., float("nan")])
def test_fixed_sample_correlation_preserves_unused_target_argument(unused_power):
    # Arrange
    from math import atanh, sqrt
    from statistics import NormalDist

    normal = NormalDist()
    shift, critical = atanh(.3) * sqrt(27), normal.inv_cdf(.975)
    expected = {"success": True, "test_type": "correlation", "mode": "power_calculation", "n": 30,
                "power": pytest.approx(normal.cdf(shift - critical) + normal.cdf(-shift - critical)),
                "effect_size_r": .3, "alpha": .05}
    # Act
    report = call_tool(test_type="correlation", effect_size=.3, n=30, power=unused_power)
    timestamp = datetime.fromisoformat(report.pop("timestamp"))
    # Assert
    assert (report, isinstance(timestamp, datetime)) == (expected, True)
