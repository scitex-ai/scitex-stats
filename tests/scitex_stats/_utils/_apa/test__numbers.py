#!/usr/bin/env python3
"""Number formatting for APA lines: p-value bounds and decimal places."""

import pytest

from scitex_stats._utils._apa import MINUS, format_number, format_p


@pytest.mark.parametrize(
    "p, expected", [(0.0, "< .001"), (0.00001, "< .001"), (0.0421, "= .042"), (1.0, "> .999")]
)
def test_format_p_never_prints_zero_or_leading_zero(p, expected):
    # Arrange
    value = p
    # Act
    text = format_p(value)
    # Assert
    assert text == expected


@pytest.mark.parametrize(
    "value, leading_zero, expected",
    [(-6.3542, True, MINUS + "6.35"), (-0.001, True, "0.00"), (0.239, False, ".24")],
)
def test_format_number_two_decimals_real_minus_optional_zero(value, leading_zero, expected):
    # Arrange
    kwargs = {"leading_zero": leading_zero}
    # Act
    text = format_number(value, **kwargs)
    # Assert
    assert text == expected
