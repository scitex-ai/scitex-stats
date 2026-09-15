"""as_result(): raw test dict -> unified result fields."""

from __future__ import annotations

from scitex_stats._recommend._applicability import SPECS
from scitex_stats._recommend._result import as_result


def test_anova_rm_df_pair_is_collected():
    # Arrange
    raw = {"statistic": 8.6, "pvalue": 0.002, "df_effect": 2.0, "df_error": 22.0}
    # Act
    out = as_result(raw, SPECS["anova_rm"], "primary", 0.05)
    # Assert
    assert out["df"] == [2.0, 22.0]


def test_missing_p_is_not_significant_none():
    # Arrange
    raw = {"statistic": None, "pvalue": None}
    # Act
    out = as_result(raw, SPECS["brunner_munzel"], "sensitivity", 0.05)
    # Assert
    assert out["significant"] is None


def test_role_is_kept():
    # Arrange
    raw = {"statistic": 1.0, "pvalue": 0.5}
    # Act
    out = as_result(raw, SPECS["kruskal"], "sensitivity", 0.05)
    # Assert
    assert out["role"] == "sensitivity"
