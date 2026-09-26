#!/usr/bin/env python3
"""validate_apa: the validator agrees with the renderer and flags bad strings."""

import pytest

from .conftest import CASES

from scitex_stats._utils._apa import validate_apa


@pytest.mark.parametrize("name", list(CASES))
def test_formatter_output_passes_validator(results, name):
    # Arrange
    apa = results[name]["apa"]
    # Act
    report = validate_apa(apa["plain"], html=apa["html"], result=results[name])
    # Assert
    assert report["violations"] == []


@pytest.mark.parametrize(
    "text, code",
    [
        ("t(14) = -6.354, p = 0.0000, d = 3.2, n = 16", "APA-P-ZERO"),
        ("t(14) = -6.35, p < .001, d = -3.18, n = 16", "APA-MINUS"),
        ("t = 6.35, p < .001, d = 3.18, n = 16", "APA-MISSING-DF"),
        ("t(14) = 6.354, p < .001, d = 3.18, n = 16", "APA-DECIMALS"),
        ("r(28) = 0.45, p = .012", "APA-LEADING-ZERO"),
        ("t(14) = 2.35, p = 0.032, d = 0.90, n = 16", "APA-LEADING-ZERO"),
        ("t(14) = 2.35, p = .032, d = .90, n = 16", "APA-MISSING-ZERO"),
        ("t(14) = 2.35, p = .032*, d = 0.90, n = 16", "APA-ASTERISK"),
        ("χ²(2) = 5.12, p = .077, V = .29", "APA-CHI2-N"),
        ("F(2) = 4.51, p = .020, η² = .25, N = 30", "APA-DF-PAIR"),
        ("t(14) = 2.35, p = .032, n = 16", "APA-MISSING-EFFECT"),
        ("t(14) = 2.35, p = .032, d = 0.90", "APA-MISSING-N"),
        ("U = 12.00, z = −2.35, p = .0192, r_rb = .59, n₁ = 8, n₂ = 8", "APA-P-DECIMALS"),
        ("t(14) = 2.35, p=.032, d = 0.90, n = 16", "APA-SPACING"),
    ],
)
def test_validator_flags_bad_strings(text, code):
    # Arrange
    report_text = text
    # Act
    codes = {v["code"] for v in validate_apa(report_text)["violations"]}
    # Assert
    assert code in codes


@pytest.mark.parametrize(
    "html, code",
    [
        ("t(14) = 2.35, <i>p</i> = .032, <i>d</i> = 0.90, <i>n</i> = 16", "APA-NOT-ITALIC"),
        ("<i>χ</i><sup>2</sup>(1, <i>N</i> = 30) = 3.23, <i>p</i> = .072, <i>V</i> = .33", "APA-GREEK-ITALIC"),
    ],
)
def test_validator_checks_italics_in_html(html, code):
    # Arrange
    markup = html
    # Act
    codes = {v["code"] for v in validate_apa(html=markup)["violations"]}
    # Assert
    assert code in codes
