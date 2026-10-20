"""Tests for ``scitex_stats._mcp.handlers`` re-exports + key handlers.

Async handlers are driven via ``asyncio.run`` so the suite doesn't
depend on pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import math

import numpy as np

from scitex_stats._mcp import handlers as h


def _arun(coro):
    return asyncio.run(coro)


# ----- module surface ------------------------------------------------------ #

_EXPECTED_HANDLER_NAMES = {
    "recommend_tests_handler",
    "run_test_handler",
    "format_results_handler",
    "power_analysis_handler",
    "correct_pvalues_handler",
    "describe_handler",
    "effect_size_handler",
    "normality_test_handler",
    "posthoc_test_handler",
    "p_to_stars_handler",
}


def test_handlers_all_lists_expected_names():
    # Arrange
    expected = _EXPECTED_HANDLER_NAMES

    # Act
    exported = set(h.__all__)

    # Assert
    assert expected.issubset(exported)


def test_handlers_module_defines_expected_attributes():
    # Arrange
    expected = _EXPECTED_HANDLER_NAMES

    # Act
    missing = [name for name in expected if not hasattr(h, name)]

    # Assert
    assert not missing, f"missing: {missing}"


# ----- p_to_stars_handler -------------------------------------------------- #


def test_p_to_stars_tiny_p_succeeds():
    # Arrange
    p_value = 0.0001

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value))

    # Assert
    assert out["success"] is True


def test_p_to_stars_three_stars_for_tiny_p():
    # Arrange
    p_value = 0.0001

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value))

    # Assert
    assert out["stars"] == "***"


def test_p_to_stars_two_stars_for_p_under_0_01():
    # Arrange
    p_value = 0.005

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value))

    # Assert
    assert out["stars"] == "**"


def test_p_to_stars_one_star_for_p_under_0_05():
    # Arrange
    p_value = 0.04

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value))

    # Assert
    assert out["stars"] == "*"


def test_p_to_stars_ns_for_p_over_0_05():
    # Arrange
    p_value = 0.20

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value))

    # Assert
    assert out["stars"] == "ns"


def test_p_to_stars_custom_thresholds_override_defaults():
    # Arrange
    p_value = 0.05  # 0.05 >= 0.01 -> not significant under tightened thresholds
    thresholds = [0.0001, 0.001, 0.01]

    # Act
    out = _arun(h.p_to_stars_handler(p_value=p_value, thresholds=thresholds))

    # Assert
    assert out["stars"] == "ns"


def test_p_to_stars_handler_returns_dict_on_bad_thresholds():
    # Arrange
    bad_thresholds = "not_a_list"

    # Act
    out = _arun(h.p_to_stars_handler(p_value=0.01, thresholds=bad_thresholds))

    # Assert
    assert isinstance(out, dict)


def test_p_to_stars_handler_reports_success_key_on_bad_thresholds():
    # Arrange
    bad_thresholds = "not_a_list"

    # Act
    out = _arun(h.p_to_stars_handler(p_value=0.01, thresholds=bad_thresholds))

    # Assert
    assert "success" in out


# ----- describe_handler ---------------------------------------------------- #


def test_describe_reports_success():
    # Arrange
    data = [float(i) for i in range(1, 11)]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["success"] is True


def test_describe_counts_all_points():
    # Arrange
    data = [float(i) for i in range(1, 11)]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["n"] == 10


def test_describe_computes_mean():
    # Arrange
    data = [float(i) for i in range(1, 11)]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert math.isclose(out["mean"], 5.5)


def test_describe_computes_range():
    # Arrange
    data = [float(i) for i in range(1, 11)]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert math.isclose(out["range"], 9.0)


def test_describe_filters_nan_from_count():
    # Arrange
    data = [1.0, 2.0, float("nan"), 3.0]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["n"] == 3


def test_describe_default_percentiles_present():
    # Arrange
    data = list(range(100))

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert "percentiles" in out


def test_describe_default_percentiles_include_quartiles():
    # Arrange
    data = list(range(100))

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert {"25", "50", "75"}.issubset(set(out["percentiles"].keys()))


def test_describe_custom_percentiles_present():
    # Arrange
    data = list(range(100))

    # Act
    out = _arun(h.describe_handler(data=data, percentiles=[10, 90]))

    # Assert
    assert {"10", "90"}.issubset(set(out["percentiles"].keys()))


def test_describe_single_point_counts_one():
    # Arrange
    data = [42.0]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["n"] == 1


def test_describe_single_point_std_defaults_to_zero():
    # Arrange
    data = [42.0]  # n=1: std/var/sem default to 0.0 (avoid division by n-1)

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["std"] == 0.0


def test_describe_single_point_mean_is_the_point():
    # Arrange
    data = [42.0]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["mean"] == 42.0


def test_describe_iqr_correct():
    # Arrange
    data = list(range(1, 102))  # for 1..101, IQR (Q3-Q1) ~= 50

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert math.isclose(out["iqr"], 50.0, abs_tol=1.0)


def test_describe_skewness_present_when_scipy_available():
    # Arrange
    data = list(range(1, 50))  # scipy is a hard dep, so skewness should be present

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert "skewness" in out


def test_describe_skewness_is_float_when_scipy_available():
    # Arrange
    data = list(range(1, 50))

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert isinstance(out["skewness"], float)


def test_describe_empty_data_reports_success():
    # Arrange
    data = [float("nan"), float("nan")]  # all-NaN -> "No valid data points" branch

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out["success"] is True


def test_describe_empty_data_returns_error_message():
    # Arrange
    data = [float("nan"), float("nan")]

    # Act
    out = _arun(h.describe_handler(data=data))

    # Assert
    assert out.get("error") == "No valid data points"


# (`describe_handler`'s scipy-ImportError fallback is hard to stub
# cleanly without breaking other sibling handlers that share scipy
# in this process. Skipped intentionally.)


# ----- posthoc_test_handler ------------------------------------------------ #

_RNG = np.random.default_rng(0)
_G1 = _RNG.normal(0.0, 1.0, 30).tolist()
_G2 = _RNG.normal(0.5, 1.0, 30).tolist()
_G3 = _RNG.normal(1.0, 1.0, 30).tolist()


def test_posthoc_tukey_succeeds():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="tukey"
        )
    )

    # Assert
    assert out["success"] is True


def test_posthoc_tukey_echoes_method():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="tukey"
        )
    )

    # Assert
    assert out["method"] == "tukey"


def test_posthoc_tukey_reports_three_groups():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="tukey"
        )
    )

    # Assert
    assert out["n_groups"] == 3


def test_posthoc_tukey_makes_three_comparisons_for_three_groups():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="tukey"
        )
    )

    # Assert
    assert out["n_comparisons"] == 3


def test_posthoc_tukey_includes_expected_pair():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="tukey"
        )
    )

    # Assert
    pair_keys = {(c.get("group1"), c.get("group2")) for c in out["comparisons"]}
    assert ("A", "B") in pair_keys or ("B", "A") in pair_keys


def test_posthoc_games_howell_succeeds_with_unequal_variances():
    # Arrange
    g_hi_var = _RNG.normal(0.0, 3.0, 30).tolist()
    groups = [_G1, g_hi_var, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="games_howell"
        )
    )

    # Assert
    assert out["success"] is True


def test_posthoc_games_howell_echoes_method():
    # Arrange
    g_hi_var = _RNG.normal(0.0, 3.0, 30).tolist()
    groups = [_G1, g_hi_var, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="games_howell"
        )
    )

    # Assert
    assert out["n_comparisons"] == 3


def test_posthoc_dunnett_succeeds():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups,
            group_names=["ctrl", "B", "C"],
            method="dunnett",
            control_group=0,
        )
    )

    # Assert
    assert out["success"] is True


def test_posthoc_dunnett_makes_k_minus_one_comparisons():
    # Arrange
    groups = [_G1, _G2, _G3]  # Dunnett: control vs each other => k-1 comparisons

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups,
            group_names=["ctrl", "B", "C"],
            method="dunnett",
            control_group=0,
        )
    )

    # Assert
    assert out["n_comparisons"] == 2


def test_posthoc_dunn_succeeds():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="dunn"
        )
    )

    # Assert
    assert out["success"] is True


def test_posthoc_dunn_makes_three_comparisons():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(
        h.posthoc_test_handler(
            groups=groups, group_names=["A", "B", "C"], method="dunn"
        )
    )

    # Assert
    assert out["n_comparisons"] == 3


def test_posthoc_rejects_unknown_method():
    # Arrange
    groups = [_G1, _G2]

    # Act
    out = _arun(h.posthoc_test_handler(groups=groups, method="not_a_real_method"))

    # Assert
    assert out["success"] is False


def test_posthoc_unknown_method_error_names_the_method():
    # Arrange
    groups = [_G1, _G2]

    # Act
    out = _arun(h.posthoc_test_handler(groups=groups, method="not_a_real_method"))

    # Assert
    assert "not_a_real_method" in out["error"]


def test_posthoc_default_group_names_are_one_based_indexed():
    # Arrange
    groups = [_G1, _G2, _G3]

    # Act
    out = _arun(h.posthoc_test_handler(groups=groups))

    # Assert
    names = {c.get("group1") for c in out["comparisons"]} | {
        c.get("group2") for c in out["comparisons"]
    }
    assert names == {"Group_1", "Group_2", "Group_3"}


# ----- power_analysis_handler --------------------------------------------- #


def test_power_ttest_succeeds_when_n_and_effect_given():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, n=30, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_power_ttest_mode_is_power_calculation_when_n_given():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, n=30, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["mode"] == "power_calculation"


def test_power_ttest_power_is_a_probability():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, n=30, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert 0.0 < out["power"] < 1.0


def test_power_ttest_echoes_sample_size():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, n=30, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["n1"] == 30


def test_power_ttest_echoes_effect_size():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, n=30, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["effect_size"] == 0.5


def test_power_ttest_mode_is_sample_size_when_only_effect_given():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, power=0.8, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["mode"] == "sample_size_calculation"


def test_power_ttest_required_n1_is_positive():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, power=0.8, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["required_n1"] > 0


def test_power_ttest_total_n_is_sum_of_groups():
    # Arrange
    kwargs = dict(test_type="ttest", effect_size=0.5, power=0.8, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["total_n"] == out["required_n1"] + out["required_n2"]


def test_power_ttest_errors_when_neither_n_nor_effect_given():
    # Arrange
    kwargs = dict(test_type="ttest")

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is False


def test_power_ttest_error_mentions_required_inputs():
    # Arrange
    kwargs = dict(test_type="ttest")

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert "n or effect_size" in out["error"]


def test_power_anova_succeeds():
    # Arrange
    kwargs = dict(test_type="anova", effect_size=0.3, power=0.8, alpha=0.05, n_groups=3)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_power_anova_echoes_test_type():
    # Arrange
    kwargs = dict(test_type="anova", effect_size=0.3, power=0.8, alpha=0.05, n_groups=3)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["test_type"] == "anova"


def test_power_correlation_succeeds():
    # Arrange
    kwargs = dict(test_type="correlation", effect_size=0.3, power=0.8, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_power_correlation_echoes_test_type():
    # Arrange
    kwargs = dict(test_type="correlation", effect_size=0.3, power=0.8, alpha=0.05)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["test_type"] == "correlation"


def test_power_chi2_succeeds():
    # Arrange
    kwargs = dict(test_type="chi2", effect_size=0.3, power=0.8, alpha=0.05, n_groups=4)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_power_chi2_echoes_test_type():
    # Arrange
    kwargs = dict(test_type="chi2", effect_size=0.3, power=0.8, alpha=0.05, n_groups=4)

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["test_type"] == "chi2"


def test_power_rejects_unknown_test_type():
    # Arrange
    kwargs = dict(test_type="not_a_real_test")

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert out["success"] is False


def test_power_unknown_test_type_error_names_the_type():
    # Arrange
    kwargs = dict(test_type="not_a_real_test")

    # Act
    out = _arun(h.power_analysis_handler(**kwargs))

    # Assert
    assert "not_a_real_test" in out["error"]


# ----- normality_test_handler -------------------------------------------- #


def test_normality_shapiro_succeeds():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="shapiro"))

    # Assert
    assert out["success"] is True


def test_normality_shapiro_labels_test():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="shapiro"))

    # Assert
    assert out["test"] == "Shapiro-Wilk"


def test_normality_shapiro_statistic_name_is_w():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="shapiro"))

    # Assert
    assert out["statistic_name"] == "W"


def test_normality_shapiro_reports_is_normal():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="shapiro"))

    # Assert
    assert "is_normal" in out


def test_normality_dagostino_succeeds():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="dagostino"))

    # Assert
    assert out["success"] is True


def test_normality_dagostino_labels_test():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="dagostino"))

    # Assert
    assert out["test"] == "D'Agostino-Pearson"


def test_normality_dagostino_succeeds_with_too_few_samples():
    # Arrange
    data = [1.0, 2.0, 3.0, 4.0]

    # Act
    out = _arun(h.normality_test_handler(data=data, method="dagostino"))

    # Assert
    assert out["success"] is True


def test_normality_dagostino_too_few_samples_returns_error():
    # Arrange
    data = [1.0, 2.0, 3.0, 4.0]

    # Act
    out = _arun(h.normality_test_handler(data=data, method="dagostino"))

    # Assert
    assert "8 samples" in out["error"]


def test_normality_anderson_succeeds():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="anderson"))

    # Assert
    assert out["success"] is True


def test_normality_anderson_labels_test():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="anderson"))

    # Assert
    assert out["test"] == "Anderson-Darling"


def test_normality_anderson_returns_critical_value():
    # Arrange
    data = np.random.default_rng(0).normal(0, 1, 50).tolist()

    # Act
    out = _arun(h.normality_test_handler(data=data, method="anderson"))

    # Assert
    assert "critical_value_5pct" in out


def test_normality_rejects_too_few_overall():
    # Arrange
    data = [1.0, 2.0]

    # Act
    out = _arun(h.normality_test_handler(data=data))

    # Assert
    assert "error" in out


def test_normality_rejects_unknown_method():
    # Arrange
    data = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Act
    out = _arun(h.normality_test_handler(data=data, method="bogus"))

    # Assert
    assert out["success"] is False


def test_normality_unknown_method_error_names_the_method():
    # Arrange
    data = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Act
    out = _arun(h.normality_test_handler(data=data, method="bogus"))

    # Assert
    assert "bogus" in out["error"]


# ----- effect_size_handler ------------------------------------------------ #

_E_RNG = np.random.default_rng(7)
_E_G1 = _E_RNG.normal(0.0, 1.0, 30).tolist()
_E_G2 = _E_RNG.normal(0.8, 1.0, 30).tolist()


def test_effect_size_cohens_d_succeeds():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="cohens_d")
    )

    # Assert
    assert out["success"] is True


def test_effect_size_cohens_d_labels_measure():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="cohens_d")
    )

    # Assert
    assert out["measure"] == "Cohen's d"


def test_effect_size_cohens_d_includes_interpretation():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="cohens_d")
    )

    # Assert
    assert "value" in out and "interpretation" in out


def test_effect_size_cohens_d_value_within_ci():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="cohens_d")
    )

    # Assert
    assert out["ci_lower"] < out["value"] < out["ci_upper"]


def test_effect_size_hedges_g_succeeds():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="hedges_g")
    )

    # Assert
    assert out["success"] is True


def test_effect_size_hedges_g_labels_measure():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="hedges_g")
    )

    # Assert
    assert out["measure"] == "Hedges' g"


def test_effect_size_glass_delta_succeeds():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="glass_delta")
    )

    # Assert
    assert out["success"] is True


def test_effect_size_glass_delta_labels_measure():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="glass_delta")
    )

    # Assert
    assert out["measure"] == "Glass's delta"


def test_effect_size_cliffs_delta_labels_measure():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(
            group1=groups[0], group2=groups[1], measure="cliffs_delta"
        )
    )

    # Assert
    assert out["measure"] == "Cliff's delta"


def test_effect_size_cliffs_delta_skips_ci():
    # Arrange
    groups = (_E_G1, _E_G2)  # CI only added for parametric d-family

    # Act
    out = _arun(
        h.effect_size_handler(
            group1=groups[0], group2=groups[1], measure="cliffs_delta"
        )
    )

    # Assert
    assert "ci_lower" not in out and "ci_upper" not in out


def test_effect_size_rejects_unknown_measure():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="bogus")
    )

    # Assert
    assert out["success"] is False


def test_effect_size_unknown_measure_error_names_it():
    # Arrange
    groups = (_E_G1, _E_G2)

    # Act
    out = _arun(
        h.effect_size_handler(group1=groups[0], group2=groups[1], measure="bogus")
    )

    # Assert
    assert "bogus" in out["error"]


# ----- recommend_tests_handler ------------------------------------------- #


def test_recommend_tests_two_groups_succeeds():
    # Arrange
    kwargs = dict(
        n_groups=2,
        sample_sizes=[30, 30],
        outcome_type="continuous",
        design="between",
        paired=False,
        top_k=3,
    )

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_recommend_tests_respects_top_k_upper_bound():
    # Arrange
    kwargs = dict(
        n_groups=2,
        sample_sizes=[30, 30],
        outcome_type="continuous",
        design="between",
        paired=False,
        top_k=3,
    )

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert len(out["recommendations"]) <= 3


def test_recommend_tests_returns_at_least_one():
    # Arrange
    kwargs = dict(
        n_groups=2,
        sample_sizes=[30, 30],
        outcome_type="continuous",
        design="between",
        paired=False,
        top_k=3,
    )

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert len(out["recommendations"]) > 0


def test_recommend_tests_recommendation_has_required_fields():
    # Arrange
    kwargs = dict(
        n_groups=2,
        sample_sizes=[30, 30],
        outcome_type="continuous",
        design="between",
        paired=False,
        top_k=3,
    )

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    first = out["recommendations"][0]
    missing = [k for k in ("name", "family", "rationale") if k not in first]
    assert not missing, f"missing keys: {missing}"


def test_recommend_tests_echoes_context_n_groups():
    # Arrange
    kwargs = dict(n_groups=3, design="between")

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert out["context"]["n_groups"] == 3


def test_recommend_tests_echoes_context_design():
    # Arrange
    kwargs = dict(n_groups=3, design="between")

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert out["context"]["design"] == "between"


def test_recommend_tests_default_sample_sizes_succeed():
    # Arrange
    kwargs = dict(n_groups=2, sample_sizes=None)  # default-30 per group inside handler

    # Act
    out = _arun(h.recommend_tests_handler(**kwargs))

    # Assert
    assert out["success"] is True


# ----- format_results_handler -------------------------------------------- #


def test_format_results_apa_succeeds():
    # Arrange
    kwargs = dict(
        test_name="ttest_ind",
        statistic=-3.21,
        p_value=0.0022,
        df=58,
        effect_size=-0.83,
        effect_size_name="d",
        style="apa",
    )

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_format_results_apa_echoes_style():
    # Arrange
    kwargs = dict(
        test_name="ttest_ind",
        statistic=-3.21,
        p_value=0.0022,
        df=58,
        effect_size=-0.83,
        effect_size_name="d",
        style="apa",
    )

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["style"] == "apa"


def test_format_results_apa_returns_nonempty_string():
    # Arrange
    kwargs = dict(
        test_name="ttest_ind",
        statistic=-3.21,
        p_value=0.0022,
        df=58,
        effect_size=-0.83,
        effect_size_name="d",
        style="apa",
    )

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert isinstance(out["formatted"], str) and out["formatted"]


def test_format_results_apa_includes_stars():
    # Arrange
    kwargs = dict(
        test_name="ttest_ind",
        statistic=-3.21,
        p_value=0.0022,
        df=58,
        effect_size=-0.83,
        effect_size_name="d",
        style="apa",
    )

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["stars"]  # at least "*"


def test_format_results_nature_succeeds():
    # Arrange
    kwargs = dict(test_name="ttest_ind", statistic=2.0, p_value=0.04, style="nature")

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_format_results_nature_echoes_style():
    # Arrange
    kwargs = dict(test_name="ttest_ind", statistic=2.0, p_value=0.04, style="nature")

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["style"] == "nature"


def test_format_results_unknown_style_falls_back_and_succeeds():
    # Arrange
    kwargs = dict(
        test_name="ttest_ind",
        statistic=2.0,
        p_value=0.04,
        style="not_a_real_style",  # handler maps unknown -> apa_latex internally
    )

    # Act
    out = _arun(h.format_results_handler(**kwargs))

    # Assert
    assert out["success"] is True


# ----- run_test_handler -------------------------------------------------- #


def test_run_test_ttest_ind_succeeds():
    # Arrange
    kwargs = dict(test_name="ttest_ind", data=[_E_G1, _E_G2], alternative="two-sided")

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_run_test_ttest_ind_echoes_test_name():
    # Arrange
    kwargs = dict(test_name="ttest_ind", data=[_E_G1, _E_G2], alternative="two-sided")

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["test_name"] == "ttest_ind"


def test_run_test_ttest_ind_includes_statistic_and_pvalue():
    # Arrange
    kwargs = dict(test_name="ttest_ind", data=[_E_G1, _E_G2], alternative="two-sided")

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert "statistic" in out and "p_value" in out


def test_run_test_one_sample_succeeds():
    # Arrange
    kwargs = dict(test_name="ttest_1samp", data=[_E_G1])

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["success"] is True


def test_run_test_one_sample_echoes_test_name():
    # Arrange
    kwargs = dict(test_name="ttest_1samp", data=[_E_G1])

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["test_name"] == "ttest_1samp"


def test_run_test_rejects_unknown_test_name():
    # Arrange
    kwargs = dict(test_name="not_a_real_test", data=[_E_G1, _E_G2])

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["success"] is False


def test_run_test_unknown_test_name_error_names_it():
    # Arrange
    kwargs = dict(test_name="not_a_real_test", data=[_E_G1, _E_G2])

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert "not_a_real_test" in out["error"]


def test_run_test_rejects_missing_data():
    # Arrange
    kwargs = dict(test_name="ttest_ind")

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert out["success"] is False


def test_run_test_missing_data_error_mentions_data():
    # Arrange
    kwargs = dict(test_name="ttest_ind")

    # Act
    out = _arun(h.run_test_handler(**kwargs))

    # Assert
    assert "data" in out["error"].lower()


# ----- run_test_handler: remaining branches ---------------------------- #


_T_RNG = np.random.default_rng(11)


def test_run_test_multi_group_anova_succeeds():
    # Arrange
    groups = [_T_RNG.normal(0, 1, 25).tolist() for _ in range(3)]

    # Act
    out = _arun(h.run_test_handler(test_name="anova", data=groups))

    # Assert
    assert out["success"] is True


def test_run_test_multi_group_anova_includes_statistic():
    # Arrange
    groups = [_T_RNG.normal(0, 1, 25).tolist() for _ in range(3)]

    # Act
    out = _arun(h.run_test_handler(test_name="anova", data=groups))

    # Assert
    assert "statistic" in out


def test_run_test_multi_group_kruskal_succeeds():
    # Arrange
    groups = [_T_RNG.normal(0, 1, 25).tolist() for _ in range(3)]

    # Act
    out = _arun(h.run_test_handler(test_name="kruskal", data=groups))

    # Assert
    assert out["success"] is True


def test_run_test_multi_group_kruskal_echoes_test_name():
    # Arrange
    groups = [_T_RNG.normal(0, 1, 25).tolist() for _ in range(3)]

    # Act
    out = _arun(h.run_test_handler(test_name="kruskal", data=groups))

    # Assert
    assert out["test_name"] == "kruskal"


def test_run_test_contingency_chi2_succeeds():
    # Arrange
    table = [[10, 20], [30, 40]]

    # Act
    out = _arun(h.run_test_handler(test_name="chi2", data=table))

    # Assert
    assert out["success"] is True


def test_run_test_contingency_chi2_echoes_test_name():
    # Arrange
    table = [[10, 20], [30, 40]]

    # Act
    out = _arun(h.run_test_handler(test_name="chi2", data=table))

    # Assert
    assert out["test_name"] == "chi2"


def test_run_test_contingency_fisher_exact_succeeds():
    # Arrange
    table = [[2, 5], [8, 3]]

    # Act
    out = _arun(
        h.run_test_handler(
            test_name="fisher_exact", data=table, alternative="two-sided"
        )
    )

    # Assert
    assert out["success"] is True


def test_run_test_contingency_fisher_exact_echoes_test_name():
    # Arrange
    table = [[2, 5], [8, 3]]

    # Act
    out = _arun(
        h.run_test_handler(
            test_name="fisher_exact", data=table, alternative="two-sided"
        )
    )

    # Assert
    assert out["test_name"] == "fisher_exact"


def test_run_test_correlation_pearson_succeeds():
    # Arrange
    rng_c = np.random.default_rng(0)
    x = rng_c.normal(size=40)
    y = 0.5 * x + rng_c.normal(size=40, scale=0.3)

    # Act
    out = _arun(h.run_test_handler(test_name="pearson", data=[x.tolist(), y.tolist()]))

    # Assert
    assert out["success"] is True


def test_run_test_correlation_pearson_echoes_test_name():
    # Arrange
    rng_c = np.random.default_rng(0)
    x = rng_c.normal(size=40)
    y = 0.5 * x + rng_c.normal(size=40, scale=0.3)

    # Act
    out = _arun(h.run_test_handler(test_name="pearson", data=[x.tolist(), y.tolist()]))

    # Assert
    assert out["test_name"] == "pearson"


def test_run_test_data_file_path_succeeds(tmp_path):
    # Arrange
    import pandas as _pd

    csv = tmp_path / "two_cols.csv"
    _pd.DataFrame(
        {"a": [1.0, 2.0, 3.0, 4.0, 5.0], "b": [2.0, 3.0, 5.0, 6.0, 7.0]}
    ).to_csv(csv, index=False)

    # Act
    out = _arun(
        h.run_test_handler(test_name="pearson", data_file=str(csv), columns=["a", "b"])
    )

    # Assert
    assert out["success"] is True


def test_run_test_data_file_path_echoes_test_name(tmp_path):
    # Arrange
    import pandas as _pd

    csv = tmp_path / "two_cols.csv"
    _pd.DataFrame(
        {"a": [1.0, 2.0, 3.0, 4.0, 5.0], "b": [2.0, 3.0, 5.0, 6.0, 7.0]}
    ).to_csv(csv, index=False)

    # Act
    out = _arun(
        h.run_test_handler(test_name="pearson", data_file=str(csv), columns=["a", "b"])
    )

    # Assert
    assert out["test_name"] == "pearson"


def test_run_test_data_file_missing_column_fails(tmp_path):
    # Arrange
    import pandas as _pd

    csv = tmp_path / "one_col.csv"
    _pd.DataFrame({"a": [1.0, 2.0, 3.0]}).to_csv(csv, index=False)

    # Act
    out = _arun(
        h.run_test_handler(
            test_name="pearson", data_file=str(csv), columns=["a", "missing_col"]
        )
    )

    # Assert
    assert out["success"] is False


def test_run_test_data_file_missing_column_error_names_it(tmp_path):
    # Arrange
    import pandas as _pd

    csv = tmp_path / "one_col.csv"
    _pd.DataFrame({"a": [1.0, 2.0, 3.0]}).to_csv(csv, index=False)

    # Act
    out = _arun(
        h.run_test_handler(
            test_name="pearson", data_file=str(csv), columns=["a", "missing_col"]
        )
    )

    # Assert
    assert "missing_col" in out["error"]


def _anova_rm_wide_data():
    """Repeated-measures wide-format data: 3 subject-aligned conditions."""
    rng_rm = np.random.default_rng(2)
    n_subj = 12
    cond1 = rng_rm.normal(0, 1, n_subj).tolist()
    cond2 = (np.array(cond1) + rng_rm.normal(0.4, 0.3, n_subj)).tolist()
    cond3 = (np.array(cond1) + rng_rm.normal(0.8, 0.3, n_subj)).tolist()
    return [cond1, cond2, cond3]


def test_run_test_anova_rm_succeeds():
    # Arrange
    data = _anova_rm_wide_data()

    # Act
    out = _arun(h.run_test_handler(test_name="anova_rm", data=data))

    # Assert
    assert out["success"] is True


def test_run_test_anova_rm_echoes_test_name():
    # Arrange
    data = _anova_rm_wide_data()

    # Act
    out = _arun(h.run_test_handler(test_name="anova_rm", data=data))

    # Assert
    assert out["test_name"] == "anova_rm"


# ----- correct_pvalues_handler ----------------------------------------- #


def test_correct_pvalues_fdr_bh_succeeds():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    assert out["success"] is True


def test_correct_pvalues_fdr_bh_echoes_method():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    assert out["method"] == "fdr_bh"


def test_correct_pvalues_fdr_bh_reports_n_tests():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    assert out["n_tests"] == 5


def test_correct_pvalues_fdr_bh_returns_one_corrected_per_input():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    assert len(out["corrected_pvalues"]) == 5


def test_correct_pvalues_fdr_bh_returns_one_reject_flag_per_input():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    assert len(out["reject_null"]) == 5


def test_correct_pvalues_fdr_bh_corrected_never_below_raw():
    # Arrange
    pvalues = [0.001, 0.04, 0.03, 0.20, 0.005]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh"))

    # Assert
    raw_sorted = sorted(out["original_pvalues"])
    adj_sorted = sorted(out["corrected_pvalues"])
    assert all(a >= r - 1e-12 for r, a in zip(raw_sorted, adj_sorted))


def test_correct_pvalues_bonferroni_succeeds():
    # Arrange
    pvalues = [0.01, 0.02, 0.05]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni"))

    # Assert
    assert out["success"] is True


def test_correct_pvalues_bonferroni_multiplies_by_n():
    # Arrange
    pvalues = [0.01, 0.02, 0.05]  # Bonferroni multiplies by n=3

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni"))

    # Assert
    assert abs(out["corrected_pvalues"][0] - 0.03) < 1e-10


def test_correct_pvalues_holm_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05, 0.20]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="holm"))

    # Assert
    assert out["method"] == "holm"


def test_correct_pvalues_sidak_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="sidak"))

    # Assert
    assert out["method"] == "sidak"


def test_correct_pvalues_fdr_by_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05, 0.20]

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="fdr_by"))

    # Assert
    assert out["method"] == "fdr_by"


def test_correct_pvalues_unknown_method_succeeds():
    # Arrange
    pvalues = [0.01, 0.02, 0.03]  # method_map default maps unknown -> fdr_bh

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="not_a_real_method"))

    # Assert
    assert out["success"] is True


def test_correct_pvalues_unknown_method_is_echoed_back():
    # Arrange
    pvalues = [
        0.01,
        0.02,
        0.03,
    ]  # handler echoes requested method despite fdr_bh internally

    # Act
    out = _arun(h.correct_pvalues_handler(pvalues=pvalues, method="not_a_real_method"))

    # Assert
    assert out["method"] == "not_a_real_method"


def test_correct_pvalues_n_significant_counts_rejections():
    # Arrange
    pvalues = [
        0.001,
        0.5,
        0.6,
        0.7,
    ]  # only 0.001 stays significant after Bonferroni (x4)

    # Act
    out = _arun(
        h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni", alpha=0.05)
    )

    # Assert
    assert out["n_significant"] == 1


def test_correct_pvalues_reject_null_count_matches_n_significant():
    # Arrange
    pvalues = [0.001, 0.5, 0.6, 0.7]

    # Act
    out = _arun(
        h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni", alpha=0.05)
    )

    # Assert
    assert sum(out["reject_null"]) == 1


# ----- correct_pvalues fallback path (statsmodels missing) ------------ #


def _arun_without_statsmodels(coro_factory):
    """Stub the statsmodels import inside `do_correct` to force the
    handler's no-statsmodels fallback path (lines 62-107)."""
    import sys as _sys

    saved = _sys.modules.get("statsmodels.stats.multitest")
    # Replace with a module-like object whose `multipletests` raises.
    bad = type(_sys)("statsmodels.stats.multitest")

    def _raise(*a, **k):
        raise ImportError("statsmodels stubbed out")

    bad.multipletests = _raise  # type: ignore[attr-defined]
    _sys.modules["statsmodels.stats.multitest"] = bad
    try:
        return _arun(coro_factory())
    finally:
        if saved is None:
            _sys.modules.pop("statsmodels.stats.multitest", None)
        else:
            _sys.modules["statsmodels.stats.multitest"] = saved


def test_correct_pvalues_fallback_bonferroni_succeeds():
    # Arrange
    pvalues = [0.01, 0.02, 0.05]

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni")
    )

    # Assert
    assert out["success"] is True


def test_correct_pvalues_fallback_bonferroni_multiplies_by_n():
    # Arrange
    pvalues = [0.01, 0.02, 0.05]

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="bonferroni")
    )

    # Assert
    assert abs(out["corrected_pvalues"][0] - 0.03) < 1e-10


def test_correct_pvalues_fallback_holm_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05, 0.20]

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="holm")
    )

    # Assert
    assert out["success"] is True


def test_correct_pvalues_fallback_holm_rejects_smallest():
    # Arrange
    pvalues = [
        0.001,
        0.01,
        0.05,
        0.20,
    ]  # Holm n=4: smallest p * 4 = 0.004 -> significant

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="holm")
    )

    # Assert
    assert out["reject_null"][0] is True


def test_correct_pvalues_fallback_fdr_bh_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05, 0.20]

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="fdr_bh")
    )

    # Assert
    assert out["method"] == "fdr_bh"


def test_correct_pvalues_fallback_sidak_succeeds():
    # Arrange
    pvalues = [0.001, 0.01, 0.05]

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="sidak")
    )

    # Assert
    assert out["method"] == "sidak"


def test_correct_pvalues_fallback_unknown_method_uses_fdr_bh():
    # Arrange
    pvalues = [
        0.01,
        0.02,
        0.05,
    ]  # unknown methods fall back to fdr_bh, mirroring the statsmodels
    # path's method_map default (same contract as
    # test__corrections.test_unknown_method_falls_back_to_fdr_bh)

    # Act
    out = _arun_without_statsmodels(
        lambda: h.correct_pvalues_handler(pvalues=pvalues, method="not_a_real_method")
    )

    # Assert
    assert [round(v, 9) for v in out["corrected_pvalues"]] == [0.03, 0.03, 0.05]
    assert out["method"] == "not_a_real_method"
