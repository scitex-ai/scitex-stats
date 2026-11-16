"""Native result formatting shares the real legacy presets and interval rules."""

import inspect

import pytest

import scitex_stats as sst


@pytest.mark.parametrize(
    "requested,used,expected",
    [
        ("apa", "apa_latex", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
        ("nature", "nature_latex", r"\mathit{t} = 2.00, \mathit{P} = 0.040"),
        ("brief", "plain", "t = 2.00, p = 0.040"),
        ("science", "apa_latex", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
        ("legacy-unknown", "apa_latex", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
    ],
)
def test_native_result_has_data_without_transport_envelope(requested, used, expected):
    # Arrange
    # Act
    result = sst.format_results("ttest_ind", 2.0, 0.04, style=requested)
    # Assert
    assert result == {
        "formatted": expected,
        "stars": "*",
        "style": requested,
        "style_used": used,
    }


def test_native_operation_is_synchronous_and_owned_by_formatter():
    # Arrange
    operation = sst.format_results
    # Act
    identity = (inspect.iscoroutinefunction(operation), operation.__module__)
    # Assert
    assert identity == (False, "scitex_stats.auto._format_results")


def test_native_zero_effect_bounds_and_p_value_remain_visible():
    # Arrange
    # Act
    result = sst.format_results(
        "ttest_ind",
        2.0,
        0.0,
        effect_size=0.0,
        ci_lower=0.0,
        ci_upper=0.0,
        style="brief",
    )
    # Assert
    assert result == {
        "formatted": "t = 2.00, p < 0.001, d = 0.00, CI [0.00, 0.00]",
        "stars": "***",
        "style": "brief",
        "style_used": "plain",
    }


@pytest.mark.parametrize(
    "effect",
    [
        {"effect_size": 0.5, "ci_lower": 0.0},
        {"effect_size": 0.5, "ci_upper": 1.0},
        {"effect_size": 0.5, "ci_lower": 1.0, "ci_upper": 0.0},
        {"effect_size": 0.5, "ci_lower": float("nan"), "ci_upper": 1.0},
        {"ci_lower": 0.0, "ci_upper": 1.0},
    ],
)
def test_native_interval_errors_raise_without_transport_envelope(effect):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError):
        sst.format_results("ttest_ind", 2.0, 0.04, **effect)
