"""Actual public line/MCP reporting keeps supplied effect intervals visible."""

import pytest

from scitex_stats.auto import format_test_line


@pytest.mark.parametrize(
    "value,lower,upper,expected",
    [
        (0.5, -0.25, 1.25, "t = 2.00, p = 0.040, d = 0.50, CI [-0.25, 1.25]"),
        (0.0, 0.0, 0.0, "t = 2.00, p = 0.040, d = 0.00, CI [0.00, 0.00]"),
    ],
)
def test_public_formatter_renders_supplied_interval(value, lower, upper, expected):
    # Arrange
    test = {"test_name": "ttest_ind", "stat": 2.0, "p_raw": 0.04}
    effects = [{"name": "d", "value": value, "ci_lower": lower, "ci_upper": upper}]
    # Act
    result = format_test_line(test, effects=effects, style="plain")
    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "effect",
    [
        {"name": "d", "value": 0.5, "ci_lower": 0.1},
        {"name": "d", "value": 0.5, "ci_lower": 1.0, "ci_upper": 0.0},
        {"name": "d", "value": 0.5, "ci_lower": 0.0, "ci_upper": float("nan")},
        {"name": "d", "ci_lower": 0.0, "ci_upper": 1.0},
    ],
)
def test_public_formatter_rejects_unusable_interval(effect):
    # Arrange
    test = {"test_name": "ttest_ind", "stat": 2.0, "p_raw": 0.04}
    # Act
    # Assert
    with pytest.raises(ValueError):
        format_test_line(test, effects=[effect], style="plain")
