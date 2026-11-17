"""The legacy Bonferroni approximation must retain its stated t bound."""

import numpy as np
import pytest
from scipy import stats

from scitex_stats.posthoc import posthoc_dunnett
from scitex_stats.posthoc._dunnett import dunnett_critical_value


@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
@pytest.mark.parametrize("k", [1, 2, 5])
def test_legacy_bound_is_the_bonferroni_t_quantile_without_arbitrary_shrink(k, alternative):
    # Arrange: one comparison reduces to the ordinary t-test bound.
    tail_alpha = .05 / (2 * k) if alternative == "two-sided" else .05 / k
    expected = stats.t.isf(tail_alpha, 20)
    # Act
    actual = dunnett_critical_value(k, 20, .05, alternative)
    # Assert
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-14)


@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
def test_legacy_non_significant_probability_keeps_zero_in_confidence_set(alternative):
    # Arrange: t lies between the former 0.95-shrunken bound and the true bound.
    control = np.asarray([-2., -1., 0., 0., 1., 2.])
    expected_bound = stats.t.isf(.025 if alternative == "two-sided" else .05, 10)
    target_t = .975 * expected_bound
    shift = target_t * np.sqrt(2 * np.var(control, ddof=1) / len(control))
    treatment = control + (-shift if alternative == "less" else shift)
    reference = stats.ttest_ind(treatment, control, alternative=alternative)
    # Act
    row = posthoc_dunnett(control, [treatment], alternative=alternative).iloc[0]
    # Assert
    assert {"reference_not_significant": reference.pvalue > .05,
            "reported_p": row["pvalue"], "significant": bool(row["significant"]),
            "zero_in_interval": ((row["ci_lower"] == "-inf" or row["ci_lower"] <= 0)
                                 and (row["ci_upper"] == "inf" or row["ci_upper"] >= 0))} == {
        "reference_not_significant": True, "reported_p": round(float(reference.pvalue), 4),
        "significant": False, "zero_in_interval": True,
    }
