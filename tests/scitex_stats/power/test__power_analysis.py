"""Tests for `scitex_stats.power_analysis` (test-type-dispatched power)."""

import pytest

from scitex_stats.power import power_analysis, power_ttest


def test_ttest_power_matches_primitive():
    # Arrange
    expected = power_ttest(effect_size=0.5, n1=64, n2=64, alpha=0.05, test_type="two-sample")
    # Act
    result = power_analysis("ttest", effect_size=0.5, n=64)
    # Assert
    assert result["power"] == pytest.approx(expected)


def test_ttest_without_n_computes_sample_size():
    # Arrange
    effect = 0.5
    # Act
    result = power_analysis("ttest", effect_size=effect, power=0.8)
    # Assert
    assert result["mode"] == "sample_size_calculation"


@pytest.mark.parametrize("test_type", ["anova", "correlation", "chi2"])
def test_other_test_types_compute_power_given_n(test_type):
    # Arrange
    kwargs = dict(effect_size=0.3, n=100)
    # Act
    result = power_analysis(test_type, **kwargs)
    # Assert
    assert 0.0 < result["power"] <= 1.0


def test_unknown_test_type_raises():
    # Arrange
    test_type = "bogus"
    # Act
    call = lambda: power_analysis(test_type, effect_size=0.5)  # noqa: E731
    # Assert
    with pytest.raises(ValueError, match="Unknown test_type"):
        call()
