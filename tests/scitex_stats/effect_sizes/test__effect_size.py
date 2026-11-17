"""Native synchronous effect-size dispatch shared by public interfaces."""

import inspect

import numpy as np
import pytest

import scitex_stats as ss


@pytest.mark.parametrize(
    "measure,expected",
    [("cohens_d", -3.0), ("hedges_g", -2.4), ("glass_delta", -3.0), ("cliffs_delta", -1.0)],
)
def test_public_effect_size_matches_closed_form(measure, expected):
    # Arrange
    first, second = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
    # Act
    result = ss.effect_size(first, second, measure=measure)
    # Assert
    assert (result["value"], result["group1_n"], result["group2_n"]) == (
        pytest.approx(expected, abs=1e-12, rel=0), 3, 3,
    )


def test_public_effect_size_is_native_synchronous_api():
    # Arrange
    operation = ss.effect_size
    # Act
    result = operation([1, 2, 3], [4, 5, 6])
    # Assert
    assert (
        inspect.iscoroutinefunction(operation), isinstance(result, dict),
        "success" in result, "timestamp" in result,
        operation.__module__.startswith("scitex_stats.effect_sizes."),
    ) == (False, True, False, False, True)


@pytest.mark.parametrize("measure", ["cohens_d", "hedges_g"])
def test_public_effect_size_rejects_unimplemented_unpooled_mode(measure):
    # Arrange
    groups = ([1, 2, 3], [4, 5, 6])
    # Act
    # Assert
    with pytest.raises(ValueError, match="pooled=False"):
        ss.effect_size(*groups, measure=measure, pooled=False)


@pytest.mark.parametrize(
    "first,second",
    [([], [1, 2]), ([1], [2, 3]), ([[1, 2]], [2, 3]),
     ([1, np.nan], [2, 3]), ([1, np.inf], [2, 3])],
)
def test_public_effect_size_rejects_invalid_groups(first, second):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError, match="group"):
        ss.effect_size(first, second)


def test_cliffs_delta_accepts_single_observation_groups():
    # Arrange
    groups = ([1.0], [2.0])
    # Act
    result = ss.effect_size(*groups, measure="cliffs_delta")
    # Assert
    assert (result["value"], "ci_lower" in result, "ci_upper" in result) == (-1.0, False, False)


def test_public_effect_size_rejects_unknown_measure():
    # Arrange
    groups = ([1, 2, 3], [4, 5, 6])
    # Act
    # Assert
    with pytest.raises(ValueError, match="Unknown measure"):
        ss.effect_size(*groups, measure="bogus")


def test_glass_delta_accepts_one_treatment_and_two_control_observations():
    # Arrange
    groups = ([0.0], [1.0, 3.0])
    # Act
    result = ss.effect_size(*groups, measure="glass_delta")
    # Assert
    assert (result["value"], result["group1_n"], result["group2_n"]) == (
        pytest.approx(-np.sqrt(2), abs=1e-12, rel=0), 1, 2,
    )
