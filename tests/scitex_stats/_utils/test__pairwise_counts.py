#!/usr/bin/env python3
# File: tests/scitex_stats/_utils/test__pairwise_counts.py
"""Sort-and-search pairwise counts equal the brute-force pair matrix."""

import numpy as np

from scitex_stats._utils._pairwise_counts import pairwise_counts
from scitex_stats.effect_sizes import cliffs_delta


def _brute(x, y):
    return int(np.sum(x[:, None] > y)), int(np.sum(x[:, None] < y))


def test_counts_equal_the_pair_matrix_with_ties():
    # Arrange
    rng = np.random.default_rng(3)
    x, y = rng.integers(0, 6, 40).astype(float), rng.integers(0, 6, 25).astype(float)
    # Act
    counts = tuple(int(c) for c in pairwise_counts(x, y))
    # Assert
    assert counts == _brute(x, y)


def test_counts_equal_the_pair_matrix_without_ties():
    # Arrange
    rng = np.random.default_rng(4)
    x, y = rng.normal(size=30), rng.normal(size=33)
    # Act
    counts = tuple(int(c) for c in pairwise_counts(x, y))
    # Assert
    assert counts == _brute(x, y)


def test_cliffs_delta_of_disjoint_samples_is_one():
    # Arrange
    x, y = np.arange(10.0, 20.0), np.arange(0.0, 10.0)
    # Act
    delta = cliffs_delta(x, y)
    # Assert
    assert delta == 1.0


def test_cliffs_delta_handles_samples_too_large_for_a_pair_matrix():
    # Arrange
    x, y = np.arange(200_000.0), np.arange(200_000.0) + 0.5
    # Act
    delta = cliffs_delta(x, y)
    # Assert
    assert abs(delta) < 1e-4


# EOF
