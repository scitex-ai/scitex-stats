"""Style routing uses real presets and reports its actual fallback."""

import asyncio

import pytest

from scitex_stats._mcp._handlers._format import format_results_handler


@pytest.mark.parametrize(
    "style,expected",
    [
        ("apa", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
        ("nature", r"\mathit{t} = 2.00, \mathit{P} = 0.040"),
        ("brief", "t = 2.00, p = 0.040"),
        ("science", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
    ],
)
def test_transport_selects_the_actual_preset(style, expected):
    # Arrange
    request = format_results_handler("ttest_ind", 2.0, 0.04, style=style)
    # Act
    result = asyncio.run(request)
    # Assert
    assert (result["success"], result["formatted"]) == (True, expected)


@pytest.mark.parametrize(
    "requested,used",
    [
        ("apa", "apa_latex"),
        ("nature", "nature_latex"),
        ("brief", "plain"),
        ("science", "apa_latex"),
        ("legacy-unknown", "apa_latex"),
    ],
)
def test_transport_reports_actual_style_without_changing_request_echo(requested, used):
    # Arrange
    request = format_results_handler("ttest_ind", 2.0, 0.04, style=requested)
    # Act
    result = asyncio.run(request)
    # Assert
    assert (result["style"], result["style_used"]) == (requested, used)


@pytest.mark.parametrize(
    "style", ["apa", "nature", "brief", "science", "legacy-unknown"]
)
def test_transport_payload_matches_native_operation(style):
    # Arrange
    from scitex_stats import format_results

    arguments = {
        "test_name": "ttest_ind",
        "statistic": 2.0,
        "p_value": 0.04,
        "df": 12.0,
        "effect_size": 0.5,
        "ci_lower": -0.25,
        "ci_upper": 1.25,
        "style": style,
    }
    expected = format_results(**arguments)
    # Act
    result = asyncio.run(format_results_handler(**arguments))
    # Assert
    assert (
        result["success"],
        {
            key: value
            for key, value in result.items()
            if key not in {"success", "timestamp"}
        },
    ) == (True, expected)
