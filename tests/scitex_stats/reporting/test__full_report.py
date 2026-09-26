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


# ===================================================================
# Regression tests: per-test CI semantics + input validation
# (PR #89 hold: perfect Spearman / MWU got a raw mean-diff CI; NaN
# statistic/p/effect and reversed/NaN CI were accepted as complete;
# RM-ANOVA / Friedman method-under-`test` and n-under-`n_subjects`
# were rejected as missing.)
# ===================================================================


def _spearman_result(method="Spearman's rank correlation"):
    # Arrange
    return {
        "test_method": method,
        "statistic": 0.9,
        "stat_symbol": "r",
        "pvalue": 0.01,
        "stars": "*",
        "effect_size": 0.9,
        "effect_size_metric": "rho",
        "n_x": 10,
        "n_y": 10,
    }


def test_spearman_perfect_rho_gives_degenerate_ci():
    # Arrange — identical arrays -> rho = 1.0 exactly
    x = np.arange(1, 11, dtype=float)
    y = np.arange(1, 11, dtype=float)
    # Act
    import scitex_stats as ss

    report = full_report(ss.run_test("spearman", data=x, data2=y), data=x, data2=y)
    # Assert — a perfect rank correlation has no sampling variance: CI is
    # [1.0, 1.0], NOT a wide/negative-spanning mean-difference interval.
    assert report["ci"] == (1.0, 1.0)


def test_spearman_strong_rho_ci_bounded_to_minus_one_one():
    # Arrange — a near-monotonic pair (one inversion) -> high rho
    x = np.arange(1, 13, dtype=float)
    y = np.array([1, 2, 3, 4, 5, 6, 8, 7, 9, 10, 11, 12], dtype=float)
    # Act
    import scitex_stats as ss

    report = full_report(ss.run_test("spearman", data=x, data2=y), data=x, data2=y)
    lo, hi = report["ci"]
    # Assert — the CI lives on the correlation scale [-1, 1] (the old
    # mean-difference bug produced an interval several units wide).
    assert -1.0 <= lo <= hi <= 1.0


def test_spearman_ci_not_a_mean_difference_interval():
    # Arrange — 0..10 scale data; a mean-diff CI would span several units
    x = np.arange(1, 11, dtype=float)
    y = np.arange(1, 11, dtype=float) * 0.5 + 0.1
    # Act
    import scitex_stats as ss

    report = full_report(ss.run_test("spearman", data=x, data2=y), data=x, data2=y)
    lo, hi = report["ci"]
    # Assert — CI width on the correlation scale is < 1 (never a raw-unit CI)
    assert (hi - lo) < 1.0


def test_mannwhitney_ci_is_rank_biserial_not_mean_diff():
    # Arrange
    a = np.array([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    b = np.array([2.0, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    # Act
    import scitex_stats as ss

    report = full_report(
        ss.run_test("mannwhitneyu", data=a, data2=b),
        data=a,
        data2=b,
        n_bootstrap=400,
        random_state=0,
    )
    lo, hi = report["ci"]
    # Assert — the reportable MWU effect is the rank-biserial r in [-1, 1];
    # the old bug returned a mean-difference CI that exceeded 1.
    assert -1.0 <= lo <= hi <= 1.0


def test_nan_statistic_pvalue_effect_marked_missing():
    # Arrange
    res = _spearman_result()
    res["statistic"] = float("nan")
    res["pvalue"] = float("nan")
    res["effect_size"] = float("nan")
    # Act
    report = full_report(res, ci=(0.1, 0.5), strict=False)
    # Assert — NaN values are not "present"; all three must be reported missing
    assert set(report["missing_fields"]) == {"statistic", "pvalue", "effect_size"}


def test_nan_statistic_strict_raises():
    # Arrange
    res = _spearman_result()
    res["statistic"] = float("nan")
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(res, ci=(0.1, 0.5), strict=True)


def test_reversed_explicit_ci_treated_as_missing():
    # Arrange — lower > upper is not a valid interval
    res = _spearman_result()
    # Act
    report = full_report(res, ci=(5.0, -5.0), strict=False)
    # Assert
    assert "ci" in report["missing_fields"]


def test_reversed_explicit_ci_strict_raises():
    # Arrange
    res = _spearman_result()
    # Act
    # Assert
    with pytest.raises(IncompleteReportError):
        full_report(res, ci=(5.0, -5.0), strict=True)


def test_nan_result_provided_ci_treated_as_missing():
    # Arrange — result carries NaN ci_lower/ci_upper
    res = _spearman_result()
    res["ci_lower"] = float("nan")
    res["ci_upper"] = float("nan")
    # Act
    report = full_report(res, strict=False)
    # Assert
    assert "ci" in report["missing_fields"]


def test_method_read_from_test_key_friedman():
    # Arrange — Friedman stores the method under `test`, not `test_method`
    res = {
        "test": "Friedman test",
        "statistic": 20.5,
        "stat_symbol": "chi2",
        "pvalue": 0.0001,
        "stars": "***",
        "effect_size": 0.4,
        "effect_size_metric": "kendall_w",
        "n_subjects": 25,
    }
    # Act
    report = full_report(res, ci=(0.2, 0.6))
    # Assert — method is recognised, not reported missing
    assert report["method"] == "Friedman test"


def test_n_read_from_n_subjects_friedman():
    # Arrange — same result; n lives under n_subjects
    res = {
        "test": "Friedman test",
        "statistic": 20.5,
        "stat_symbol": "chi2",
        "pvalue": 0.0001,
        "effect_size": 0.4,
        "effect_size_metric": "kendall_w",
        "n_subjects": 25,
    }
    # Act
    report = full_report(res, ci=(0.2, 0.6))
    # Assert — n_subjects is collected, so `n` is present
    assert report["n"] == {"n_subjects": 25}


def test_rm_anova_result_method_and_n_recognised():
    # Arrange — repeated-measures ANOVA stores method under `test`,
    # n under `n_subjects`
    res = {
        "test": "Repeated Measures ANOVA",
        "statistic": 11.0,
        "stat_symbol": "F",
        "pvalue": 0.0001,
        "effect_size": 0.3,
        "effect_size_metric": "partial_eta_squared",
        "n_subjects": 30,
    }
    # Act
    report = full_report(res, ci=(0.2, 0.45), strict=False)
    # Assert — neither method nor n is missing for this family
    assert ("method" not in report["missing_fields"]) and ("n" not in report["missing_fields"])


def test_friedman_end_to_end_method_and_n_not_missing():
    # Arrange — drive the real Friedman emitter through full_report
    import scitex_stats as ss

    rng = np.random.default_rng(7)
    groups = [rng.normal(0, 1, 20) for _ in range(4)]
    result = ss.run_test("friedman", groups=groups)
    # Act
    report = full_report(result, ci=(0.2, 0.5), strict=False)
    # Assert — the real result's method (`test`) and n (`n_subjects`) resolve
    assert ("method" not in report["missing_fields"]) and ("n" not in report["missing_fields"])


def test_full_report_exposed_at_package_top_level():
    # Arrange
    import scitex_stats as ss
    # Act
    # Assert — the public-API contract includes full_report
    assert callable(ss.full_report)

