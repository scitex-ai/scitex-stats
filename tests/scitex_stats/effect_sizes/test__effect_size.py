"""Tests for `scitex_stats.effect_size` (measure-dispatched effect size)."""

import numpy as np
import pytest

from scitex_stats.effect_sizes import cliffs_delta, cohens_d, effect_size

G1 = [5.1, 5.5, 6.0, 6.2, 6.8, 7.1]
G2 = [4.0, 4.4, 4.9, 5.0, 5.3, 5.6]


def test_cohens_d_value_matches_primitive():
    # Arrange
    expected = cohens_d(np.array(G1), np.array(G2))
    # Act
    result = effect_size(G1, G2, measure="cohens_d")
    # Assert
    assert result["value"] == pytest.approx(expected)


def test_hedges_g_is_smaller_than_d_for_small_samples():
    # Arrange
    d = effect_size(G1, G2, measure="cohens_d")["value"]
    # Act
    g = effect_size(G1, G2, measure="hedges_g")["value"]
    # Assert
    assert abs(g) < abs(d)


def test_cliffs_delta_matches_primitive_and_has_no_ci():
    # Arrange
    expected = cliffs_delta(np.array(G1), np.array(G2))
    # Act
    result = effect_size(G1, G2, measure="cliffs_delta")
    # Assert
    assert (result["value"], "ci_lower" in result) == (pytest.approx(expected), False)


def test_unknown_measure_raises():
    # Arrange
    measure = "bogus"
    # Act
    call = lambda: effect_size(G1, G2, measure=measure)  # noqa: E731
    # Assert
    with pytest.raises(ValueError, match="Unknown measure"):
        call()
