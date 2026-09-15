"""recommend_test: one primary test per branch of the decision table.

Test-style notes: each test asserts a SINGLE property with Arrange/Act/Assert markers.
"""

from __future__ import annotations

import json

import pytest

from scitex_stats._recommend import recommend_test


def _primary(data, **kw):
    rec = recommend_test(data, **kw)
    return rec["primary"]["test_id"] if rec["primary"] else None


def test_normal_equal_variance_defaults_to_welch(normal_equal_var):
    # Arrange
    # Act
    primary = _primary(normal_equal_var, design="independent")
    # Assert
    assert primary == "ttest_welch"


def test_normal_equal_variance_lists_student_as_alternative(normal_equal_var):
    # Arrange
    # Act
    rec = recommend_test(normal_equal_var, design="independent")
    # Assert
    assert "ttest_ind" in [a["test_id"] for a in rec["alternatives"]]


def test_student_needs_a_documented_reason(normal_equal_var):
    # Arrange
    # Act
    primary = _primary(normal_equal_var, design="independent", assume_equal_variance=True)
    # Assert
    assert primary == "ttest_ind"


def test_welch_choice_is_stated_in_the_decision_path(normal_equal_var):
    # Arrange
    # Act
    rec = recommend_test(normal_equal_var, design="independent")
    # Assert
    assert any("Welch" in step["text"] and "documented" in step["text"] for step in rec["decision_path"])


def test_normal_unequal_variance_is_welch(normal_unequal_var):
    # Arrange
    # Act
    primary = _primary(normal_unequal_var, design="independent")
    # Assert
    assert primary == "ttest_welch"


def test_unequal_variance_makes_student_not_applicable(normal_unequal_var):
    # Arrange
    # Act
    rows = {r["test_id"]: r for r in recommend_test(normal_unequal_var, design="independent")["applicability"]}
    # Assert
    assert rows["ttest_ind"]["applicable"] is False


def test_nonnormal_small_n_is_mann_whitney(nonnormal_small):
    # Arrange
    # Act
    primary = _primary(nonnormal_small, design="independent")
    # Assert
    assert primary == "mannwhitneyu"


def test_paired_normal_is_paired_t(paired_normal):
    # Arrange
    # Act
    primary = _primary(paired_normal, design="paired")
    # Assert
    assert primary == "ttest_rel"


def test_paired_nonnormal_is_wilcoxon(paired_nonnormal):
    # Arrange
    # Act
    primary = _primary(paired_nonnormal, design="paired")
    # Assert
    assert primary == "wilcoxon"


def test_three_normal_equal_defaults_to_welch_anova(three_normal_equal):
    # Arrange
    # Act
    primary = _primary(three_normal_equal, design="independent")
    # Assert
    assert primary == "welch_anova"


def test_three_normal_equal_with_documented_reason_is_anova(three_normal_equal):
    # Arrange
    # Act
    primary = _primary(three_normal_equal, design="independent", assume_equal_variance=True)
    # Assert
    assert primary == "anova"


def test_documented_reason_does_not_override_unequal_variances(three_normal_unequal):
    # Arrange
    # Act
    primary = _primary(three_normal_unequal, design="independent", assume_equal_variance=True)
    # Assert
    assert primary == "welch_anova"


def test_three_normal_unequal_is_welch_anova(three_normal_unequal):
    # Arrange
    # Act
    primary = _primary(three_normal_unequal, design="independent")
    # Assert
    assert primary == "welch_anova"


def test_three_nonnormal_is_kruskal(three_nonnormal):
    # Arrange
    # Act
    primary = _primary(three_nonnormal, design="independent")
    # Assert
    assert primary == "kruskal"


def test_three_paired_nonnormal_is_friedman(three_nonnormal):
    # Arrange
    # Act
    primary = _primary(three_nonnormal, design="paired")
    # Assert
    assert primary in ("friedman", "anova_rm")


def test_small_expected_counts_is_fisher(small_expected_table):
    # Arrange
    # Act
    primary = _primary(small_expected_table, design="independent", scale="categorical")
    # Assert
    assert primary == "fisher"


def test_small_expected_counts_make_chi2_not_applicable(small_expected_table):
    # Arrange
    # Act
    rows = {r["test_id"]: r for r in recommend_test(small_expected_table, design="independent", scale="categorical")["applicability"]}
    # Assert
    assert rows["chi2"]["applicable"] is False


def test_large_expected_counts_is_chi2(large_expected_table):
    # Arrange
    # Act
    primary = _primary(large_expected_table, design="independent", scale="categorical")
    # Assert
    assert primary == "chi2"


def test_ordinal_two_groups_is_mann_whitney(normal_equal_var):
    # Arrange
    # Act
    primary = _primary(normal_equal_var, design="independent", scale="ordinal")
    # Assert
    assert primary == "mannwhitneyu"


def test_primary_is_always_applicable(three_normal_unequal):
    # Arrange
    rec = recommend_test(three_normal_unequal, design="independent")
    # Act
    rows = {r["test_id"]: r for r in rec["applicability"]}
    # Assert
    assert rows[rec["primary"]["test_id"]]["applicable"] is True


def test_non_overlapping_groups_fall_back_from_brunner_munzel(sample_ui):
    # Arrange
    # Act
    rows = {r["test_id"]: r for r in recommend_test(sample_ui, design="independent")["applicability"]}
    # Assert
    assert rows["brunner_munzel"]["applicable"] is False


def test_unspecified_design_is_flagged_not_silent(sample_ui):
    # Arrange
    # Act
    rec = recommend_test(sample_ui)
    # Assert
    assert any("Design not specified" in n["text"] for n in rec["notes"])


def test_summary_reads_as_a_path(normal_unequal_var):
    # Arrange
    # Act
    summary = recommend_test(normal_unequal_var, design="independent")["summary"]
    # Assert
    assert summary.endswith("Primary test: Welch's t-test") and "Variances differ" in summary


def test_output_is_json_serialisable(three_normal_equal):
    # Arrange
    rec = recommend_test(three_normal_equal, design="independent")
    # Act
    text = json.dumps(rec)
    # Assert
    assert '"primary"' in text


def test_recommendation_is_deterministic(three_normal_unequal):
    # Arrange
    first = json.dumps(recommend_test(three_normal_unequal, design="independent"), sort_keys=True)
    # Act
    second = json.dumps(recommend_test(three_normal_unequal, design="independent"), sort_keys=True)
    # Assert
    assert first == second


def test_one_group_has_no_recommendation():
    # Arrange
    # Act
    primary = _primary([[1.0, 2.0, 3.0]], design="independent")
    # Assert
    assert primary is None


@pytest.mark.parametrize("design", ["between", "within", "repeated"])
def test_design_aliases_are_accepted(sample_ui, design):
    # Arrange
    # Act
    rec = recommend_test(sample_ui, design=design)
    # Assert
    assert rec["data"]["design_specified"] is True


def test_unknown_design_raises(sample_ui):
    # Arrange
    design = "sideways"
    # Act
    def call():
        return recommend_test(sample_ui, design=design)

    # Assert
    with pytest.raises(ValueError, match="design"):
        call()
