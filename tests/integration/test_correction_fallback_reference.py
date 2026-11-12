"""Fallback corrections must agree with the real statsmodels implementation."""

import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from scitex_stats._mcp._handlers._corrections import _correct_without_statsmodels

METHODS = ["bonferroni", "holm", "fdr_bh", "fdr_by", "sidak", "unknown"]
INPUTS = [
    pytest.param([0.01, 0.04, 0.03, 0.002], id="ordinary"),
    pytest.param([0.05], id="alpha-boundary"),
    pytest.param([1e-20, 1e-12, 0.2, 0.2, 1.0], id="tiny-ties-endpoint"),
    pytest.param([0.9, 0.7, 0.8, 0.9, 0.1], id="clipping"),
]


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("pvalues", INPUTS)
def test_fallback_values_match_reference(method, pvalues):
    # Arrange
    reference_method = "fdr_bh" if method == "unknown" else method
    _, expected, _, _ = multipletests(pvalues, alpha=0.05, method=reference_method)

    # Act
    result = _correct_without_statsmodels(pvalues, method, 0.05)

    # Assert
    assert np.allclose(result["corrected_pvalues"], expected, rtol=1e-12, atol=0)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("pvalues", INPUTS)
def test_fallback_decisions_match_reference(method, pvalues):
    # Arrange
    reference_method = "fdr_bh" if method == "unknown" else method
    reject, _, _, _ = multipletests(pvalues, alpha=0.05, method=reference_method)

    # Act
    result = _correct_without_statsmodels(pvalues, method, 0.05)

    # Assert
    observed = {
        key: result[key]
        for key in ["success", "method", "n_tests", "reject_null", "n_significant"]
    }
    assert observed == {
        "success": True,
        "method": method,
        "n_tests": len(pvalues),
        "reject_null": reject.tolist(),
        "n_significant": int(reject.sum()),
    }
