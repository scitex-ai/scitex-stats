#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for `scitex_stats.reporting.full_report` (six-stat reporting doctrine)."""

from __future__ import annotations

import numpy as np
import pytest

from scitex_stats.reporting import IncompleteReportError, full_report


def _ttest_ind_result():
    """Minimal stand-in for a `test_ttest_ind()` result dict."""
    return {
        "test_method": "Welch's t-test (independent)",
        "statistic": 2.34,
        "stat_symbol": "t",
        "pvalue": 0.021,
        "stars": "*",
        "effect_size": 0.47,
        "effect_size_metric": "Cohen's d",
        "n_x": 50,
        "n_y": 50,
    }


def test_full_report_with_explicit_ci_returns_ci_tuple():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["ci"] == (0.12, 0.89)


def test_full_report_with_explicit_ci_sets_ci_level():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89), confidence=0.95)
    # Assert
    assert report["ci_level"] == 0.95


def test_full_report_preserves_method():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["method"] == "Welch's t-test (independent)"


def test_full_report_preserves_statistic():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["statistic"] == 2.34


def test_full_report_preserves_pvalue():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["pvalue"] == 0.021


def test_full_report_preserves_effect_size():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["effect_size"] == 0.47


def test_full_report_collects_n_x_and_n_y():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["n"] == {"n_x": 50, "n_y": 50}


def test_full_report_missing_fields_empty_when_complete():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert report["missing_fields"] == []


def test_full_report_formatted_contains_method_name():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert "Welch's t-test (independent)" in report["formatted"]


def test_full_report_formatted_contains_ci_bracket():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert "95% CI [0.12, 0.89]" in report["formatted"]


def test_full_report_formatted_italicizes_stat_symbol():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, ci=(0.12, 0.89))
    # Assert
    assert "*t*" in report["formatted"]


def test_full_report_derives_ci_from_raw_arrays_independent_ttest():
    # Arrange
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 50)
    y = rng.normal(0.8, 1, 50)
    result = _ttest_ind_result()
    # Act
    report = full_report(result, data=x, data2=y)
    # Assert
    assert report["ci"] is not None


def test_full_report_derived_ci_is_ordered_lower_le_upper():
    # Arrange
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 50)
    y = rng.normal(0.8, 1, 50)
    result = _ttest_ind_result()
    # Act
    report = full_report(result, data=x, data2=y)
    # Assert
    assert report["ci"][0] <= report["ci"][1]


def test_full_report_bootstrap_fallback_for_nonparametric_method():
    # Arrange
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 40)
    y = rng.normal(0.5, 1, 40)
    result = dict(_ttest_ind_result())
    result["test_method"] = "Mann-Whitney U test"
    # Act
    report = full_report(result, data=x, data2=y, n_bootstrap=200, random_state=0)
    # Assert
    assert report["ci"] is not None


def test_full_report_raises_when_ci_undeterminable_and_strict():
    # Arrange
    result = _ttest_ind_result()
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(result)


def test_full_report_non_strict_logs_and_returns_missing_ci():
    # Arrange
    result = _ttest_ind_result()
    # Act
    report = full_report(result, strict=False)
    # Assert
    assert "ci" in report["missing_fields"]


def test_full_report_raises_when_method_missing():
    # Arrange
    result = _ttest_ind_result()
    del result["test_method"]
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(result, ci=(0.12, 0.89))


def test_full_report_raises_when_effect_size_missing():
    # Arrange
    result = _ttest_ind_result()
    del result["effect_size"]
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(result, ci=(0.12, 0.89))


def test_full_report_raises_when_n_missing():
    # Arrange
    result = _ttest_ind_result()
    del result["n_x"]
    del result["n_y"]
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(result, ci=(0.12, 0.89))
