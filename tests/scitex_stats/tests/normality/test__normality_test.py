"""Tests for `scitex_stats.normality_test` (method-dispatched normality)."""

import numpy as np
import pytest
from scipy import stats as scipy_stats

from scitex_stats.tests.normality import normality_test

NORMAL = np.random.default_rng(0).normal(0, 1, 50).tolist()


def test_shapiro_matches_scipy():
    # Arrange
    _, expected_p = scipy_stats.shapiro(NORMAL)
    # Act
    result = normality_test(NORMAL, method="shapiro")
    # Assert
    assert result["p_value"] == pytest.approx(expected_p)


def test_anderson_reports_five_percent_decision():
    # Arrange
    method = "anderson"
    # Act
    result = normality_test(NORMAL, method=method)
    # Assert
    assert set(result) >= {"critical_value_5pct", "normal"}


def test_too_few_values_raise():
    # Arrange
    data = [1.0, 2.0]
    # Act
    call = lambda: normality_test(data)  # noqa: E731
    # Assert
    with pytest.raises(ValueError, match="at least 3"):
        call()


def test_dagostino_needs_eight_values():
    # Arrange
    data = [1.0, 2.0, 3.0, 4.0]
    # Act
    call = lambda: normality_test(data, method="dagostino")  # noqa: E731
    # Assert
    with pytest.raises(ValueError, match="8 samples"):
        call()
