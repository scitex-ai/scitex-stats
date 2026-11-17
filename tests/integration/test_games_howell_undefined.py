"""Undefined Games–Howell pairs cannot be reported as evidence of no effect."""

import numpy as np
import pytest

from scitex_stats.posthoc import run_posthoc


@pytest.mark.parametrize("second", [1.0, 2.0])
def test_constant_pair_has_null_values_and_explicit_reason(second):
    # Arrange
    groups = [[1.] * 4, [second] * 4, [4., 5., 6., 7.]]
    # Act
    result = run_posthoc(groups, omnibus="anova", when="always")
    first = result["comparisons"][0]
    # Assert
    assert {"statistic": first["statistic"], "p": first["p_adjusted"],
            "df": first["df"], "significant": first["significant"],
            "ci": first["mean_diff_ci_lower"],
            "undefined": "standard error" in first.get("undefined", "")} == {
        "statistic": None, "p": None, "df": None,
        "significant": False, "ci": None, "undefined": True,
    }


def test_later_constant_pair_keeps_other_comparisons_available():
    # Arrange
    groups = [[4., 5., 6., 7.], [1.] * 4, [2.] * 4]
    # Act
    rows = run_posthoc(groups, omnibus="anova", when="always")["comparisons"]
    # Assert
    assert [row["p_adjusted"] is not None for row in rows] == [True, True, False]


def test_defined_single_constant_comparisons_match_independent_reference():
    # Arrange
    groups = [[1.] * 4, [2., 3., 4., 6.], [4., 5., 6., 8., 10.]]
    # Independent SciPy 1.18.1 tukey_hsd(equal_var=False) reference.
    expected = [0.09554685028674237, 0.014232661625067755, 0.16566237747969348]
    # Act
    result = run_posthoc(groups, omnibus="anova", when="always")
    # Assert
    assert np.allclose(
        [row["p_adjusted"] for row in result["comparisons"]], expected,
        rtol=1e-10, atol=1e-12,
    )


def test_undefined_pair_does_not_mutate_group_arrays():
    # Arrange
    groups = [np.ones(4), np.full(4, 2.), np.array([4., 5., 6., 7.])]
    before = np.stack(groups).copy()
    # Act
    run_posthoc(groups, omnibus="anova", when="always")
    # Assert
    assert np.array_equal(np.stack(groups), before)


@pytest.mark.parametrize("bad", [[float("inf"), 1., 2.], [1e308, -1e308], [1.]])
def test_core_marks_unusable_standard_error_or_degrees_of_freedom_undefined(bad):
    # Arrange
    from scitex_stats.posthoc._auto import _games_howell
    groups = [np.asarray(bad), np.array([3., 4., 5.])]
    # Act
    row = _games_howell(groups, alpha=.05, level=.95)[0]
    # Assert
    assert {"statistic": row["statistic"], "p": row["p_adjusted"], "df": row["df"],
            "undefined": "standard error" in row.get("undefined", "")} == {
        "statistic": None, "p": None, "df": None, "undefined": True,
    }
