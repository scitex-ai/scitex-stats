"""Effect intervals are supplied data with explicit validation and precision."""

import pytest

from scitex_stats.auto._format_ci import format_effect_interval


@pytest.mark.parametrize(
    "effect,precision,expected",
    [
        ({"value": 0.5}, 2, ""),
        ({"value": 0.5, "ci_lower": None, "ci_upper": None}, 2, ""),
        (
            {"value": 0.5, "ci_lower": -0.1234, "ci_upper": 0.9876},
            3,
            "CI [-0.123, 0.988]",
        ),
        ({"value": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}, 2, "CI [0.00, 0.00]"),
    ],
)
def test_interval_rendering_contract(effect, precision, expected):
    # Arrange
    # Act
    result = format_effect_interval(effect, precision)
    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "effect",
    [
        {"value": 0.5, "ci_lower": 0.0},
        {"value": 0.5, "ci_upper": 1.0},
        {"value": 0.5, "ci_lower": 1.0, "ci_upper": 0.0},
        {"value": 0.5, "ci_lower": float("nan"), "ci_upper": 1.0},
        {"value": 0.5, "ci_lower": 0.0, "ci_upper": float("inf")},
        {"value": float("inf"), "ci_lower": 0.0, "ci_upper": 1.0},
        {"ci_lower": 0.0, "ci_upper": 1.0},
    ],
)
def test_unusable_supplied_interval_fails(effect):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError):
        format_effect_interval(effect)


def test_interval_rendering_preserves_input_mapping():
    # Arrange
    effect = {"value": 0.5, "ci_lower": 0.0, "ci_upper": 1.0}
    before = effect.copy()
    # Act
    format_effect_interval(effect)
    # Assert
    assert effect == before
