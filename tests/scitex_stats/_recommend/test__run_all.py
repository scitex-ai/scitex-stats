"""run_all_applicable: primary vs sensitivity, the p-hacking warning, agreement, determinism."""

from __future__ import annotations

import json

import pytest

from scitex_stats._recommend import run_all_applicable


def test_warning_names_p_hacking(normal_equal_var):
    # Arrange
    # Act
    out = run_all_applicable(normal_equal_var, design="independent")
    # Assert
    assert "p-hacking" in out["warning"] and "false-positive" in out["warning"]


def test_exactly_one_primary(normal_equal_var):
    # Arrange
    # Act
    roles = [r["role"] for r in run_all_applicable(normal_equal_var, design="independent")["results"]]
    # Assert
    assert roles.count("primary") == 1


def test_primary_is_listed_first(three_normal_equal):
    # Arrange
    # Act
    results = run_all_applicable(three_normal_equal, design="independent", assume_equal_variance=True)["results"]
    # Assert
    assert results[0]["role"] == "primary"


def test_others_are_sensitivity(three_normal_equal):
    # Arrange
    # Act
    results = run_all_applicable(three_normal_equal, design="independent", assume_equal_variance=True)["results"]
    # Assert
    assert {r["role"] for r in results[1:]} == {"sensitivity"}


def test_primary_matches_recommendation(normal_unequal_var):
    # Arrange
    # Act
    out = run_all_applicable(normal_unequal_var, design="independent")
    # Assert
    assert out["results"][0]["test_id"] == out["recommendation"]["primary"]["test_id"]


def test_order_is_not_by_p_value(three_normal_equal):
    # Arrange
    from scitex_stats._recommend import CATALOG

    catalogue = [s.test_id for s in CATALOG]
    results = run_all_applicable(three_normal_equal, design="independent", assume_equal_variance=True)["results"]
    # Act
    rest = [r["test_id"] for r in results[1:]]
    # Assert
    assert rest == sorted(rest, key=catalogue.index)


def test_pre_registered_primary_is_honoured(normal_equal_var):
    # Arrange
    # Act
    out = run_all_applicable(normal_equal_var, design="independent", primary="mannwhitneyu")
    # Assert
    assert out["results"][0]["test_id"] == "mannwhitneyu" and out["primary_source"] == "pre-registered"


def test_non_applicable_primary_is_refused(normal_unequal_var):
    # Arrange
    primary = "ttest_ind"
    # Act
    def call():
        return run_all_applicable(normal_unequal_var, design="independent", primary=primary)

    # Assert
    with pytest.raises(ValueError, match="not applicable"):
        call()


def test_every_applicable_test_runs(three_normal_equal):
    # Arrange
    out = run_all_applicable(three_normal_equal, design="independent", assume_equal_variance=True)
    # Act
    applicable = {r["test_id"] for r in out["recommendation"]["applicability"] if r["applicable"]}
    # Assert
    assert {r["test_id"] for r in out["results"]} == applicable


def test_every_result_has_a_p_value(three_normal_equal):
    # Arrange
    # Act
    results = run_all_applicable(three_normal_equal, design="independent", assume_equal_variance=True)["results"]
    # Assert
    assert all(r["pvalue"] is not None for r in results)


def test_agreement_reports_agree(sample_ui):
    # Arrange
    # Act
    agreement = run_all_applicable(sample_ui, design="independent")["agreement"]
    # Assert
    assert agreement["status"] == "agree"


def test_agreement_detects_disagreement():
    # Arrange
    from scitex_stats._recommend._run_all import agreement

    results = [{"test_id": "a", "pvalue": 0.01, "significant": True}, {"test_id": "b", "pvalue": 0.2, "significant": False}]
    # Act
    out = agreement(results, 0.05)
    # Assert
    assert out["status"] == "disagree"


def test_welch_anova_matches_reference():
    # Arrange: Welch (1951) statistic, cross-checked against pingouin.welch_anova
    from scitex_stats._recommend._applicability import welch_anova
    import numpy as np

    groups = [np.array([4.0, 5.0, 6.0, 5.5, 4.5]), np.array([6.0, 9.0, 7.5, 8.0, 10.0]), np.array([5.0, 12.0, 3.0, 9.0, 15.0])]
    # Act
    out = welch_anova(groups)
    # Assert
    pingouin = pytest.importorskip("pingouin")
    import pandas as pd

    df = pd.DataFrame({"v": np.concatenate(groups), "g": np.repeat([0, 1, 2], 5)})
    ref = pingouin.welch_anova(df, dv="v", between="g")
    assert abs(out["statistic"] - float(ref["F"].iloc[0])) < 1e-9


def test_categorical_run_uses_fisher(small_expected_table):
    # Arrange
    # Act
    results = run_all_applicable(small_expected_table, design="independent", scale="categorical")["results"]
    # Assert
    assert [r["test_id"] for r in results] == ["fisher"]


def test_paired_three_conditions_run(paired_normal):
    # Arrange
    groups = paired_normal + [[v + 1.0 for v in paired_normal[1]]]
    # Act
    results = run_all_applicable(groups, design="paired")["results"]
    # Assert
    assert all(r["error"] is None for r in results)


def _without_clock(obj):
    # A provenance receipt is stamped with wall-clock time; everything else must repeat exactly.
    if isinstance(obj, dict):
        return {k: _without_clock(v) for k, v in obj.items() if k not in ("timestamp_utc", "receipt_sha256")}
    if isinstance(obj, list):
        return [_without_clock(v) for v in obj]
    return obj


def test_run_all_is_deterministic(three_normal_unequal):
    # Arrange
    first = json.dumps(_without_clock(run_all_applicable(three_normal_unequal, design="independent")), sort_keys=True, default=str)
    # Act
    second = json.dumps(_without_clock(run_all_applicable(three_normal_unequal, design="independent")), sort_keys=True, default=str)
    # Assert
    assert first == second
