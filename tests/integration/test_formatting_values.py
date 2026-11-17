"""Public reporting preserves values and selects the requested real preset."""

import pytest

from scitex_stats.auto import format_test_line


@pytest.mark.parametrize(
    "adjusted,raw,expected",
    [
        (0.0, 0.04, "t = 2.00, p < 0.001"),
        (0.0, None, "t = 2.00, p < 0.001"),
        (None, 0.04, "t = 2.00, p = 0.040"),
        (0.03, 0.04, "t = 2.00, p = 0.030"),
        (None, 0.0, "t = 2.00, p < 0.001"),
    ],
)
def test_adjusted_value_precedes_raw_even_when_zero(adjusted, raw, expected):
    # Arrange
    data = {"test_name": "ttest_ind", "stat": 2.0, "p_raw": raw, "p_adj": adjusted}
    # Act
    result = format_test_line(data, style="plain")
    # Assert
    assert result == expected
