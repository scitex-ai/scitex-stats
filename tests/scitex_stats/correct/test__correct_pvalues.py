"""Tests for `scitex_stats.correct_pvalues` (method-dispatched correction)."""

import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from scitex_stats.correct import correct_pvalues

PVALUES = [0.01, 0.04, 0.03, 0.002]


@pytest.mark.parametrize("method", ["bonferroni", "holm", "sidak", "fdr_bh", "fdr_by"])
def test_corrected_values_match_statsmodels(method):
    # Arrange
    _, expected, _, _ = multipletests(PVALUES, alpha=0.05, method=method)
    # Act
    result = correct_pvalues(PVALUES, method=method)
    # Assert
    assert np.allclose(result["corrected_pvalues"], expected, rtol=1e-12, atol=0)


def test_unknown_method_falls_back_to_fdr_bh_but_echoes_name():
    # Arrange
    _, expected, _, _ = multipletests(PVALUES, alpha=0.05, method="fdr_bh")
    # Act
    result = correct_pvalues(PVALUES, method="unknown")
    # Assert
    assert (result["method"], np.allclose(result["corrected_pvalues"], expected)) == (
        "unknown",
        True,
    )


def test_counts_significant_after_bonferroni():
    # Arrange
    pvalues = [0.001, 0.02, 0.5]
    # Act
    result = correct_pvalues(pvalues, method="bonferroni", alpha=0.05)
    # Assert
    assert (result["n_tests"], result["n_significant"]) == (3, 1)


def test_is_exported_at_top_level():
    # Arrange
    import scitex_stats
    # Act
    exported = scitex_stats.correct_pvalues
    # Assert
    assert exported is correct_pvalues
