"""Native Tukey cannot treat an undefined pooled error as no effect."""

from copy import deepcopy

import numpy as np
import pytest

from scitex_stats.posthoc import run_posthoc
from scitex_stats.posthoc._auto import _tukey


@pytest.mark.parametrize("second", [1.0, 2.0])
def test_zero_pooled_error_has_null_comparisons_with_an_explicit_reason(second):
    # Arrange
    groups = [[1.] * 4, [second] * 4, [3.] * 4]
    # Act
    rows = run_posthoc(groups, "anova", equal_variances=True, when="always")["comparisons"]
    # Assert
    assert [{"statistic": r["statistic"], "p": r["p_adjusted"], "df": r["df"],
             "significant": r["significant"], "ci": r["mean_diff_ci_lower"],
             "undefined": "standard error" in r.get("undefined", "")} for r in rows] == [
        {"statistic": None, "p": None, "df": None, "significant": False,
         "ci": None, "undefined": True},
    ] * 3


@pytest.mark.parametrize("groups", [
    [[1.], [2.], [3.]],
    [[float("inf"), 1., 2.], [3., 4., 5.], [6., 7., 8.]],
    [[1e308, -1e308], [3., 4.], [5., 6.]],
])
def test_core_unusable_pooled_error_or_degrees_of_freedom_is_undefined(groups):
    # Arrange
    arrays = [np.asarray(g) for g in groups]
    # Act
    rows = _tukey(arrays, alpha=.05, level=.95)
    # Assert
    assert [(r["statistic"], r["p_adjusted"], r["df"], r.get("diff_ci"),
             "standard error" in r.get("undefined", "")) for r in rows] == [
        (None, None, None, None, True),
    ] * 3


def test_two_constant_groups_still_have_defined_pairs_when_pooled_error_is_positive():
    # Arrange: Tukey uses the error pooled across ALL groups, unlike Games–Howell.
    groups = [[1.] * 4, [2.] * 4, [4., 5., 6., 8., 10.]]
    # Act
    rows = run_posthoc(groups, "anova", equal_variances=True, when="always")["comparisons"]
    # Assert
    assert [r["p_adjusted"] is not None and "undefined" not in r for r in rows] == [True] * 3


def test_zero_pooled_error_does_not_mutate_inputs_or_mean_differences():
    # Arrange
    groups = [[1.] * 4, [2.] * 4, [3.] * 4]
    before = deepcopy(groups)
    # Act
    rows = run_posthoc(groups, "anova", equal_variances=True, when="always")["comparisons"]
    # Assert
    assert {"preserved": groups == before, "differences": [r["mean_diff"] for r in rows]} == {
        "preserved": True, "differences": [-1., -2., -1.],
    }
