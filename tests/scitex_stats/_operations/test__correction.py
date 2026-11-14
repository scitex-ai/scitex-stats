"""Compare the real NumPy correction kernel with statsmodels."""

import pytest
from statsmodels.stats.multitest import multipletests

METHODS = ["bonferroni", "holm", "sidak", "fdr_bh", "fdr_by"]


@pytest.fixture
def pvalues():
    return [0.0, 0.001, 0.04, 0.03, 0.20, 0.005, 1.0]


@pytest.mark.parametrize("method", METHODS)
def test_native_numpy_fallback_matches_reference_backend(pvalues, method):
    # Arrange: exercise the real NumPy fallback against an independent backend.
    from scitex_stats._operations._correction import _correct_pvalues_numpy

    reject, expected, _, _ = multipletests(pvalues, alpha=0.05, method=method)
    # Act
    result = _correct_pvalues_numpy(pvalues=pvalues, method=method, alpha=0.05)
    # Assert
    assert (result["corrected_pvalues"], result["reject_null"],
            set(result) & {"success", "timestamp"}) == (
                pytest.approx(expected.tolist()), reject.tolist(), set(),
            )
