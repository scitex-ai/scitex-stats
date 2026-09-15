"""check_applicability: ✓/✗ with reasons and full assumption evidence for every test."""

from __future__ import annotations

from scitex_stats._recommend import CATALOG, DEFAULT_THRESHOLDS, check_applicability


def _rows(data, **kw):
    return {r["test_id"]: r for r in check_applicability(data, **kw)}


def test_every_catalogue_test_is_reported(sample_ui):
    # Arrange
    # Act
    rows = check_applicability(sample_ui, design="independent")
    # Assert
    assert [r["test_id"] for r in rows] == [s.test_id for s in CATALOG]


def test_every_row_has_reasons(sample_ui):
    # Arrange
    # Act
    rows = check_applicability(sample_ui, design="independent")
    # Assert
    assert all(r["reasons"] for r in rows)


def test_not_applicable_rows_carry_a_fail_reason(nonnormal_small):
    # Arrange
    # Act
    rows = [r for r in check_applicability(nonnormal_small, design="independent") if not r["applicable"]]
    # Assert
    assert all(any(i["status"] == "fail" for i in r["reason_items"]) for r in rows)


def test_nonnormal_excludes_t_tests(nonnormal_small):
    # Arrange
    # Act
    rows = _rows(nonnormal_small, design="independent")
    # Assert
    assert not rows["ttest_welch"]["applicable"] and not rows["ttest_ind"]["applicable"]


def test_normality_evidence_is_per_group(sample_ui):
    # Arrange
    # Act
    samples = _rows(sample_ui, design="independent")["ttest_welch"]["assumptions"]["normality"]["samples"]
    # Assert
    assert [s["sample"] for s in samples] == ["Group 1", "Group 2"]


def test_levene_and_brown_forsythe_are_both_reported(sample_ui):
    # Arrange
    # Act
    var = _rows(sample_ui, design="independent")["ttest_ind"]["assumptions"]["equal_variance"]
    # Assert
    assert var["levene"] is not None and var["brown_forsythe"] is not None


def test_thresholds_are_included(sample_ui):
    # Arrange
    # Act
    th = _rows(sample_ui, design="independent")["anova"]["assumptions"]["thresholds"]
    # Assert
    assert th == DEFAULT_THRESHOLDS


def test_seed_is_42():
    # Arrange
    # Act
    seed = DEFAULT_THRESHOLDS["seed"]
    # Assert
    assert seed == 42


def test_small_n_low_power_caveat_is_reported(nonnormal_small):
    # Arrange
    # Act
    samples = _rows(nonnormal_small, design="independent")["ttest_welch"]["assumptions"]["normality"]["samples"]
    # Assert
    assert any("low power" in c["text"] for s in samples for c in s["caveats"])


def test_missing_values_are_removed_and_counted():
    # Arrange
    from scitex_stats._recommend import recommend_test

    # Act
    data = recommend_test([[1, 2, None, 4, 5], [2, "x", 4, 5, float("nan")]], design="independent")["data"]
    # Assert
    assert data["invalid_removed_per_group"] == [1, 2]


def test_paired_length_mismatch_is_not_applicable():
    # Arrange
    # Act
    rows = _rows([[1.0, 2.0, 3.0, 4.0], [2.0, 3.0, 4.0]], design="paired")
    # Assert
    assert not rows["ttest_rel"]["applicable"] and not rows["wilcoxon"]["applicable"]


def test_paired_normality_uses_differences(paired_normal):
    # Arrange
    # Act
    basis = _rows(paired_normal, design="paired")["ttest_rel"]["assumptions"]["normality"]["basis"]
    # Assert
    assert basis == "paired differences"


def test_ordinal_excludes_parametric_tests(sample_ui):
    # Arrange
    # Act
    rows = _rows(sample_ui, design="independent", scale="ordinal")
    # Assert
    assert not rows["ttest_welch"]["applicable"] and rows["mannwhitneyu"]["applicable"]


def test_fisher_only_for_2x2():
    # Arrange
    # Act
    rows = _rows([[3, 1, 2], [1, 4, 2]], design="independent", scale="categorical")
    # Assert
    assert not rows["fisher"]["applicable"]


def test_expected_count_threshold_is_five(small_expected_table):
    # Arrange
    # Act
    ec = _rows(small_expected_table, design="independent", scale="categorical")["chi2"]["assumptions"]["expected_counts"]
    # Assert
    assert ec["threshold"] == 5 and ec["status"] == "violated"


def test_threshold_override_changes_the_decision(normal_unequal_var):
    # Arrange
    # Act
    rows = _rows(normal_unequal_var, design="independent", thresholds={"variance_alpha": 1e-300})
    # Assert
    assert rows["ttest_ind"]["applicable"]
