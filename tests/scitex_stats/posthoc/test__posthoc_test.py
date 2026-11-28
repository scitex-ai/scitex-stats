"""Tests for `scitex_stats.posthoc_test` (method-dispatched pairwise post-hoc)."""

import pytest

from scitex_stats.posthoc import posthoc_test

GROUPS = [[1.0, 2.0, 3.0, 2.5, 1.5], [4.0, 5.0, 6.0, 5.5, 4.5], [7.0, 8.0, 9.0, 8.5, 7.5]]


@pytest.mark.parametrize(("method", "n_pairs"), [("tukey", 3), ("games_howell", 3), ("dunn", 3), ("dunnett", 2)])
def test_number_of_comparisons_per_method(method, n_pairs):
    # Arrange
    groups = GROUPS
    # Act
    result = posthoc_test(groups, method=method)
    # Assert
    assert result["n_comparisons"] == n_pairs


def test_default_group_names_are_numbered():
    # Arrange
    groups = GROUPS
    # Act
    result = posthoc_test(groups, method="games_howell")
    # Assert
    assert result["comparisons"][0]["group1"] == "Group_1"


def test_unknown_method_raises():
    # Arrange
    method = "bogus"
    # Act
    call = lambda: posthoc_test(GROUPS, method=method)  # noqa: E731
    # Assert
    with pytest.raises(ValueError, match="Unknown method"):
        call()
