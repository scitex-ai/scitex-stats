"""Exact large-count controls prevent integer overflow in Dunn rank variance."""

import math

import numpy as np
import pytest

from scitex_stats.posthoc._auto import _dunn

GROUP_SIZE = 2**20 + 1


def test_large_all_tied_population_is_undefined():
    # Arrange: the pooled tie count is just above the signed-int64 cube boundary.
    groups = [np.zeros(GROUP_SIZE), np.zeros(GROUP_SIZE)]
    # Act
    def compare():
        return _dunn(groups, alpha=.05, level=.95)

    # Assert
    with pytest.raises(ValueError, match="rank variance"):
        compare()


def test_large_single_outlier_has_exact_rank_z_of_minus_one():
    # Arrange: N=2m, tie counts=(N-1,1), sigma2=N/4; mean-rank difference=-1.
    groups = [np.zeros(GROUP_SIZE), np.zeros(GROUP_SIZE)]
    groups[1][-1] = 1
    expected_p = math.erfc(1 / math.sqrt(2))
    # Act
    row = _dunn(groups, alpha=.05, level=.95, correction="bonferroni")[0]
    # Assert: pairwise standard error is exactly 1; one comparison needs no factor.
    assert [row["statistic"], row["p_unadjusted"], row["p_adjusted"]] == pytest.approx(
        [-1., expected_p, expected_p], rel=1e-12, abs=1e-14,
    )
