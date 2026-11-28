"""Tests for `scitex_stats.format_results` (journal-style result line)."""

from scitex_stats.auto._format_results import format_results


def test_returns_line_and_stars_for_significant_result():
    # Arrange
    p_value = 0.003
    # Act
    result = format_results("t-test", 3.2, p_value, df=18)
    # Assert
    assert (result["style"], result["stars"], bool(result["formatted"])) == (
        "apa",
        "**",
        True,
    )


def test_effect_size_appears_in_formatted_line():
    # Arrange
    kwargs = dict(effect_size=0.81, effect_size_name="d")
    # Act
    result = format_results("t-test", 3.2, 0.003, df=18, **kwargs)
    # Assert
    assert "0.81" in result["formatted"]


def test_unknown_style_is_echoed():
    # Arrange
    style = "unknown-journal"
    # Act
    result = format_results("t-test", 1.0, 0.5, style=style)
    # Assert
    assert result["style"] == style
