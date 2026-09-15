"""Fixture datasets for the recommender: one per branch of the decision table."""

from __future__ import annotations

import numpy as np
import pytest


def _rng():
    return np.random.default_rng(42)


@pytest.fixture
def normal_equal_var():
    # Arrange: two normal groups, same SD
    rng = _rng()
    return [rng.normal(10, 2, 30).tolist(), rng.normal(11, 2, 30).tolist()]


@pytest.fixture
def normal_unequal_var():
    rng = _rng()
    return [rng.normal(10, 1, 30).tolist(), rng.normal(11, 5, 30).tolist()]


@pytest.fixture
def nonnormal_small():
    # Skewed, n = 12 per group, similar spread
    return [
        [0.1, 0.2, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.1, 1.6, 2.9, 9.0],
        [0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.7, 2.2, 2.9, 4.1, 11.5],
    ]


@pytest.fixture
def paired_normal():
    rng = _rng()
    pre = rng.normal(10, 2, 20)
    return [pre.tolist(), (pre + rng.normal(0.5, 1, 20)).tolist()]


@pytest.fixture
def paired_nonnormal():
    pre = [5.0, 6.1, 5.5, 7.2, 6.3, 5.9, 6.8, 5.2, 6.0, 6.6, 5.7, 6.4]
    post = [p + d for p, d in zip(pre, [0.1, 0.2, 0.1, 0.3, 0.2, 0.1, 0.2, 0.1, 0.3, 0.2, 0.1, 6.0])]
    return [pre, post]


@pytest.fixture
def three_normal_equal():
    rng = _rng()
    return [rng.normal(m, 2, 25).tolist() for m in (10, 11, 12)]


@pytest.fixture
def three_normal_unequal():
    rng = _rng()
    return [rng.normal(10, 1, 25).tolist(), rng.normal(11, 4, 25).tolist(), rng.normal(12, 8, 25).tolist()]


@pytest.fixture
def three_nonnormal():
    rng = _rng()
    return [rng.exponential(1, 20).tolist() for _ in range(3)]


@pytest.fixture
def small_expected_table():
    return [[3, 1], [1, 4]]


@pytest.fixture
def large_expected_table():
    return [[30, 10], [12, 28]]


@pytest.fixture
def sample_ui():
    # The Stats app's "Sample data"
    return [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]]
