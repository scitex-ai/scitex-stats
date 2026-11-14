"""A single control comparison must agree with the ordinary pooled t-test."""

import numpy as np
import pytest
from scipy import stats

from scitex_stats.posthoc import posthoc_dunnett


@pytest.mark.parametrize(
    "alternative, shift",
    [
        ("two-sided", 2.2),
        ("greater", 1.7),
        ("less", -1.7),
        ("two-sided", 3.0),
        ("greater", 2.5),
        ("less", -2.5),
    ],
)
def test_single_comparison_decision_and_interval_agree_with_t_test(
    alternative, shift
):
    # Arrange
    control = np.array([-1.0, 0.0, 1.0])
    treatment = control + shift
    reference = stats.ttest_ind(treatment, control, alternative=alternative)
    expected_rejection = bool(reference.pvalue < 0.05)
    # Act
    row = posthoc_dunnett(
        control=control, treatments=[treatment], alternative=alternative,
        return_as="dict",
    )[0]
    # Assert
    assert (
        row["significant"],
        row["pvalue"],
        float(row["ci_lower"]) <= 0 <= float(row["ci_upper"]),
    ) == (
        expected_rejection,
        pytest.approx(float(reference.pvalue), abs=0.00005),
        not expected_rejection,
    )
