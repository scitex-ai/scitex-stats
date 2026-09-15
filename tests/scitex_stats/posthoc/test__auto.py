#!/usr/bin/env python3
"""Tests for automatic post-hoc selection and comparisons (`posthoc/_auto.py`)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from scitex_stats.posthoc import run_posthoc, select_posthoc

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]
C = [5.9, 6.2, 6.0, 5.8, 6.4, 6.1]
NULL = [[5.1, 5.3, 4.9, 5.2, 5.0], [5.0, 5.2, 5.1, 4.8, 5.3], [5.2, 4.9, 5.1, 5.0, 5.2]]
HETERO = [list(np.random.default_rng(0).normal(5, 0.2, 15)), list(np.random.default_rng(1).normal(6, 3, 15)),
          list(np.random.default_rng(2).normal(7, 1, 15))]
BLOCKS = (np.random.default_rng(3).normal(0, 1, (14, 3)) + [0, 0.9, 1.6]).T.tolist()


@pytest.mark.parametrize(
    "omnibus, kwargs, method, correction",
    [
        ("anova", {"equal_variances": True}, "tukey", "Tukey (studentized range, family-wise)"),
        ("anova", {"equal_variances": False}, "games_howell", "Games–Howell (studentized range with Welch df, family-wise)"),
        ("welch_anova", {}, "games_howell", "Games–Howell (studentized range with Welch df, family-wise)"),
        ("kruskal", {}, "dunn", "Holm"),
        ("friedman", {}, "nemenyi", "Nemenyi (studentized range, family-wise)"),
        ("friedman", {"friedman_method": "wilcoxon"}, "wilcoxon", "Holm"),
        ("anova_rm", {}, "paired_t", "Holm"),
    ],
)
def test_select_posthoc_maps_omnibus_to_procedure(omnibus, kwargs, method, correction):
    # Arrange
    # Act
    choice = select_posthoc(omnibus, 3, **kwargs)
    # Assert
    assert (choice["method"], choice["correction"], choice["applicable"]) == (method, correction, True)


def test_select_posthoc_needs_three_groups():
    # Arrange
    # Act
    choice = select_posthoc("anova", 2)
    # Assert
    assert choice["applicable"] is False and "3 or more groups" in choice["reason"]


def test_select_posthoc_unknown_omnibus_is_not_applicable():
    # Arrange
    # Act
    choice = select_posthoc("chi2", 4)
    # Assert
    assert choice["applicable"] is False


def test_select_posthoc_rejects_unknown_friedman_method():
    # Arrange
    bad = "conover"
    # Act
    def call():
        return select_posthoc("friedman", 3, friedman_method=bad)

    # Assert
    with pytest.raises(ValueError, match="friedman_method"):
        call()


def test_anova_uses_brown_forsythe_to_pick_tukey_for_homogeneous_groups():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "anova")
    # Assert
    assert out["method"] == "tukey" and out["variance_check"]["equal_variances"] is True


def test_anova_picks_games_howell_when_variances_differ():
    # Arrange
    # Act
    out = run_posthoc(HETERO, "anova")
    # Assert
    assert out["method"] == "games_howell" and out["variance_check"]["equal_variances"] is False


def test_tukey_adjusted_p_matches_scipy_tukey_hsd():
    # Arrange
    reference = stats.tukey_hsd(np.array(A), np.array(B), np.array(C)).pvalue
    # Act
    out = run_posthoc([A, B, C], "anova", equal_variances=True)
    # Assert
    got = [c["p_adjusted"] for c in out["comparisons"]]
    assert got == pytest.approx([reference[0, 1], reference[0, 2], reference[1, 2]], rel=1e-6)


def test_games_howell_matches_pingouin():
    # Arrange
    pg = pytest.importorskip("pingouin")
    import pandas as pd

    frame = pd.DataFrame({"v": np.concatenate(HETERO), "g": np.repeat(["G1", "G2", "G3"], 15)})
    reference = pg.pairwise_gameshowell(frame, dv="v", between="g")
    p_col = "pval" if "pval" in reference else "p-unc"
    # Act
    out = run_posthoc(HETERO, "anova", equal_variances=False, when="always")
    # Assert
    assert [c["p_adjusted"] for c in out["comparisons"]] == pytest.approx(reference[p_col].tolist(), rel=1e-4)


def test_dunn_holm_adjustment_is_monotone_and_never_below_raw():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "kruskal")
    # Assert
    raw = [c["p_unadjusted"] for c in out["comparisons"]]
    adj = [c["p_adjusted"] for c in out["comparisons"]]
    order = np.argsort(raw)
    assert all(a >= r for a, r in zip(adj, raw)) and list(np.array(adj)[order]) == sorted(adj)


def test_dunn_holm_smallest_p_is_multiplied_by_number_of_comparisons():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "kruskal")
    # Assert
    raw = [c["p_unadjusted"] for c in out["comparisons"]]
    smallest = int(np.argmin(raw))
    assert out["comparisons"][smallest]["p_adjusted"] == pytest.approx(min(1.0, 3 * raw[smallest]))


def test_every_comparison_reports_apa_p_effect_and_ci():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "kruskal")
    # Assert
    c = out["comparisons"][0]
    assert c["p_apa"].startswith(("= ", "< ")) and c["effect_size"] is not None and c["effect_ci_apa"].startswith("95% CI [")


def test_parametric_comparisons_carry_mean_difference_ci():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "anova", equal_variances=True)
    # Assert
    c = out["comparisons"][0]
    assert c["mean_diff_ci_lower"] < c["mean_diff"] < c["mean_diff_ci_upper"] and c["mean_diff_ci_kind"] == "simultaneous"


def test_non_significant_omnibus_skips_comparisons_by_default():
    # Arrange
    # Act
    out = run_posthoc(NULL, "anova")
    # Assert
    assert out["ran"] is False and out["omnibus"]["significant"] is False and out["comparisons"] == []


def test_requested_comparisons_after_non_significant_omnibus_are_flagged():
    # Arrange
    # Act
    out = run_posthoc(NULL, "anova", when="always")
    # Assert
    assert out["ran"] is True and "omnibus_not_significant" in out["flags"]


def test_significant_omnibus_is_recorded():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "anova")
    # Assert
    assert out["omnibus"]["significant"] is True and out["omnibus"]["p_apa"] == "< .001"


def test_two_groups_run_nothing():
    # Arrange
    # Act
    out = run_posthoc([A, B], "anova")
    # Assert
    assert out["ran"] is False and out["applicable"] is False


@pytest.mark.parametrize("method", ["nemenyi", "wilcoxon"])
def test_friedman_procedures_run_on_blocks(method):
    # Arrange
    # Act
    out = run_posthoc(BLOCKS, "friedman", friedman_method=method, when="always")
    # Assert
    assert out["method"] == method and len(out["comparisons"]) == 3


def test_repeated_measures_anova_uses_paired_t_with_dz():
    # Arrange
    # Act
    out = run_posthoc(BLOCKS, "anova_rm", when="always")
    # Assert
    c = out["comparisons"][0]
    assert out["method"] == "paired_t" and c["effect_size_metric"] == "Cohen's d_z" and c["df"] == 13


def test_bootstrap_cis_are_identical_across_runs():
    # Arrange
    # Act
    first = run_posthoc([A, B, C], "kruskal", seed=42)
    second = run_posthoc([A, B, C], "kruskal", seed=42)
    # Assert
    assert [c["effect_ci_apa"] for c in first["comparisons"]] == [c["effect_ci_apa"] for c in second["comparisons"]]


def test_group_names_label_comparisons():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "anova", group_names=["Ctrl", "Low", "High"])
    # Assert
    assert (out["comparisons"][0]["group_i"], out["comparisons"][0]["group_j"]) == ("Ctrl", "Low")


def test_references_follow_the_procedure():
    # Arrange
    # Act
    out = run_posthoc([A, B, C], "kruskal")
    # Assert
    assert any(r.startswith("Dunn, O. J.") for r in out["references"]) and any(r.startswith("Holm, S.") for r in out["references"])


# EOF
