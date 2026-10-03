"""Tests for the less-common `_call_test` branches in `_dispatch`.

The integration tests cover two-sample / paired / one-sample / group
dispatch implicitly. These tests target the four still-uncovered
branches at lines 171, 208, 213-223:

- tuple unpacking when the test function returns `(result, fig)`
- `_ONE_SAMPLE_MEAN` (`ttest_1samp` with `popmean`)
- `_STACKED_GROUP` (Friedman expects column-stacked data)
- `_CONTINGENCY` (chi2 / fisher, with both `groups=` and
  `data + data2` paths)
- the final `raise ValueError` for an unrouted test_name.
"""

from __future__ import annotations

import numpy as np
import pytest

from scitex_stats._dispatch import _call_test, run_test

# ----- tuple unpacking (line 171) -------------------------------------- #


def test_run_test_unwraps_tuple_result_when_test_returns_pair_dict():
    """When `plot=True`, some test functions return `(result, fig)`.
    `run_test` should unwrap to the dict before normalising."""
    # Arrange
    rng = np.random.default_rng(0)
    g1 = rng.normal(0, 1, 25)
    g2 = rng.normal(0.5, 1, 25)
    g3 = rng.normal(1.0, 1, 25)
    # Act
    out = run_test("anova", groups=[g1, g2, g3], plot=True, json_safe=True)
    # Assert
    assert isinstance(out, dict)

def test_run_test_unwraps_tuple_result_when_test_returns_pair_value_pvalue():
    """When `plot=True`, some test functions return `(result, fig)`.
    `run_test` should unwrap to the dict before normalising."""
    # Arrange
    rng = np.random.default_rng(0)
    g1 = rng.normal(0, 1, 25)
    g2 = rng.normal(0.5, 1, 25)
    g3 = rng.normal(1.0, 1, 25)
    # Act
    out = run_test("anova", groups=[g1, g2, g3], plot=True, json_safe=True)
    # Assert
    assert "p_value" in out or "pvalue" in out


# ----- _ONE_SAMPLE_MEAN (line 208) ------------------------------------- #


def test_run_test_ttest_1samp_with_popmean_dict():
    # Arrange
    rng = np.random.default_rng(0)
    # Act
    out = run_test("ttest_1samp", data=rng.normal(3.0, 1, 50), popmean=3.0)
    # Assert
    assert isinstance(out, dict)

def test_run_test_ttest_1samp_with_popmean_value_pvalue():
    # Arrange
    rng = np.random.default_rng(0)
    # Act
    out = run_test("ttest_1samp", data=rng.normal(3.0, 1, 50), popmean=3.0)
    # Assert
    assert "p_value" in out or "pvalue" in out


# ----- _STACKED_GROUP (Friedman, line 213-214) ------------------------- #


def test_run_test_friedman_stacks_groups_into_2d():
    """Friedman expects subjects x conditions; `_call_test` builds
    that via `np.column_stack(groups)`."""
    # Arrange
    rng = np.random.default_rng(0)
    n_subj = 12
    cond1 = rng.normal(0, 1, n_subj)
    cond2 = cond1 + rng.normal(0.4, 0.3, n_subj)
    cond3 = cond1 + rng.normal(0.8, 0.3, n_subj)
    # Act
    out = run_test("friedman", groups=[cond1, cond2, cond3])
    # Assert
    assert isinstance(out, dict)


# ----- _CONTINGENCY (lines 216-221) ------------------------------------ #


def test_run_test_chi2_with_groups_2d_table_dict():
    # Arrange
    # Act
    out = run_test("chi2", groups=[[10, 20], [30, 40]])
    # Assert
    assert isinstance(out, dict)

def test_run_test_chi2_with_groups_2d_table_value_pvalue():
    # Arrange
    # Act
    out = run_test("chi2", groups=[[10, 20], [30, 40]])
    # Assert
    assert "p_value" in out or "pvalue" in out


def test_run_test_chi2_via_data_plus_data2_rows():
    """When `groups` is None, `_call_test` builds the table via
    `np.vstack([data, data2])`."""
    # Arrange
    # Act
    out = run_test("chi2", data=[10, 20], data2=[30, 40])
    # Assert
    assert isinstance(out, dict)


def test_run_test_fisher_with_groups_2x2():
    # Arrange
    # Act
    out = run_test("fisher", groups=[[2, 5], [8, 3]])
    # Assert
    assert isinstance(out, dict)


# ----- unknown dispatch (line 223) ------------------------------------- #


def test_call_test_raises_on_unrouted_test_name():
    """`_call_test` should raise when a test_name slips through
    `run_test`'s alias check but isn't in any category set."""
    # Arrange
    def _stub(*a, **kw):
        return {"unused": True}
    # Act
    # Assert
    with pytest.raises(ValueError, match="No dispatch rule"):
        _call_test(
            _stub,
            "_definitely_unrouted_",
            data=None,
            data2=None,
            groups=None,
            alternative="two-sided",
            plot=False,
            popmean=0.0,
            return_as="dict",
        )


@pytest.mark.parametrize("test_name", ["ttest_rel", "ttest_paired", "wilcoxon"])
@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
def test_paired_dispatch_preserves_requested_hypothesis(test_name, alternative):
    # Arrange
    import scitex_stats

    x = np.array([8, 10, 13, 17, 21, 25, 30, 35], dtype=float)
    y = np.array([5, 9, 9, 15, 16, 19, 23, 26], dtype=float)
    engine_name = "test_wilcoxon" if test_name == "wilcoxon" else "test_ttest_rel"
    expected = getattr(scitex_stats, engine_name)(x, y, alternative=alternative)
    # Act
    actual = run_test(test_name, data=x, data2=y, alternative=alternative)
    # Assert
    assert (
        actual["alternative"],
        actual["provenance"]["test"]["parameters"]["alternative"],
        actual["statistic"],
        actual["pvalue"],
    ) == (
        alternative,
        alternative,
        pytest.approx(expected["statistic"]),
        pytest.approx(expected["pvalue"]),
    )


@pytest.mark.parametrize("test_name", ["ttest_rel", "ttest_paired", "wilcoxon"])
@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
def test_paired_dispatch_matches_scipy_hypothesis(test_name, alternative):
    # Arrange
    from scipy import stats

    x = np.array([8, 10, 13, 17, 21, 25, 30, 35], dtype=float)
    y = np.array([5, 9, 9, 15, 16, 19, 23, 26], dtype=float)
    scipy_name = "wilcoxon" if test_name == "wilcoxon" else "ttest_rel"
    expected = getattr(stats, scipy_name)(x, y, alternative=alternative)
    # Act
    actual = run_test(test_name, data=x, data2=y, alternative=alternative)
    # Assert
    np.testing.assert_allclose(
        [actual["statistic"], actual["pvalue"]],
        [expected.statistic, expected.pvalue],
        rtol=1e-12,
        atol=1e-14,
    )


@pytest.mark.parametrize("test_name", ["ttest_rel", "ttest_paired", "wilcoxon"])
def test_paired_dispatch_omitted_alternative_remains_two_sided(test_name):
    # Arrange
    import scitex_stats

    x = np.array([8, 10, 13, 17, 21, 25, 30, 35], dtype=float)
    y = np.array([5, 9, 9, 15, 16, 19, 23, 26], dtype=float)
    engine_name = "test_wilcoxon" if test_name == "wilcoxon" else "test_ttest_rel"
    expected = getattr(scitex_stats, engine_name)(x, y)
    # Act
    actual = run_test(test_name, data=x, data2=y)
    # Assert
    assert (
        actual["alternative"],
        actual["provenance"]["test"]["parameters"]["alternative"],
        actual["statistic"],
        actual["pvalue"],
    ) == (
        "two-sided",
        "two-sided",
        pytest.approx(expected["statistic"]),
        pytest.approx(expected["pvalue"]),
    )
