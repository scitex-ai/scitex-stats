"""Assumption checks: Shapiro–Wilk, Levene / Brown–Forsythe, expected counts."""

from __future__ import annotations

import pytest

from scitex_stats._recommend._assumptions import run_checks, thresholds
from scitex_stats._recommend._data import prepare


def _checks(data, **kw):
    kw.setdefault("design", "independent")
    kw.setdefault("scale", "continuous")
    return run_checks(prepare(data, **kw), thresholds())


def test_constant_group_normality_unknown():
    # Arrange
    data = [[1.0, 1.0, 1.0, 1.0], [1.0, 2.0, 3.0, 4.0]]
    # Act
    status = _checks(data)["normality"]["status"]
    # Assert
    assert status == "unknown"


def test_two_values_normality_unknown():
    # Arrange
    data = [[1.0, 2.0], [1.0, 2.0, 3.0]]
    # Act
    status = _checks(data)["normality"]["status"]
    # Assert
    assert status == "unknown"


def test_skewed_group_normality_violated(nonnormal_small):
    # Arrange
    # Act
    status = _checks(nonnormal_small)["normality"]["status"]
    # Assert
    assert status == "violated"


def test_unequal_spread_variance_violated(normal_unequal_var):
    # Arrange
    # Act
    status = _checks(normal_unequal_var)["equal_variance"]["status"]
    # Assert
    assert status == "violated"


def test_large_n_oversensitivity_caveat():
    # Arrange
    import numpy as np

    rng = np.random.default_rng(42)
    data = [rng.normal(size=400).tolist(), rng.normal(size=400).tolist()]
    # Act
    caveats = [c["text"] for s in _checks(data)["normality"]["samples"] for c in s["caveats"]]
    # Assert
    assert any("oversensitive" in c for c in caveats)


def test_expected_counts_minimum(small_expected_table):
    # Arrange
    # Act
    ec = _checks(small_expected_table, scale="categorical")["expected_counts"]
    # Assert
    assert ec["min_expected"] == pytest.approx(16 / 9)


def test_unknown_threshold_is_rejected():
    # Arrange
    overrides = {"not_a_threshold": 1}
    # Act
    def call():
        return thresholds(overrides)

    # Assert
    with pytest.raises(ValueError, match="unknown threshold"):
        call()
