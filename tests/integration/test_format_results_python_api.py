"""Native formatting results, legacy style behavior and MCP delegation."""

import asyncio
import inspect

import pytest
import scitex_stats as ss


def test_python_formatter_returns_native_payload_and_significance_stars():
    # Arrange
    kwargs = dict(test_name="ttest_ind", statistic=2.5, p_value=0.0001, df=18)
    # Act
    result = ss.format_results(**kwargs)
    # Assert
    assert (inspect.iscoroutinefunction(ss.format_results), set(result),
            isinstance(result["formatted"], str), bool(result["formatted"]), result["stars"]) == (
                False, {"style", "formatted", "stars"}, True, True, "***",
            )


@pytest.mark.parametrize("style", ["apa", "nature", "science", "brief", "unknown_style"])
def test_formatter_mcp_payload_matches_native_python(style):
    # Arrange
    from scitex_stats._mcp._handlers._format import format_results_handler

    kwargs = dict(test_name="ttest_ind", statistic=-3.21, p_value=0.0022, df=58,
                  effect_size=-0.83, effect_size_name="d", style=style,
                  ci_lower=-1.2, ci_upper=-0.4)
    expected = ss.format_results(**kwargs)
    # Act
    result = asyncio.run(format_results_handler(**kwargs))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (result["success"], payload) == (True, expected)


def test_unknown_style_retains_apa_formatting_and_requested_label():
    # Arrange
    kwargs = dict(test_name="ttest_ind", statistic=2.5, p_value=0.03, df=18)
    expected = ss.format_results(**kwargs, style="apa")
    # Act
    result = ss.format_results(**kwargs, style="unknown_style")
    # Assert
    assert (result["formatted"], result["stars"], result["style"]) == (
        expected["formatted"], expected["stars"], "unknown_style",
    )


def test_native_formatter_propagates_the_owning_formatting_exception():
    # Arrange: a nonnumeric statistic reaches the real formatting implementation.
    kwargs = dict(test_name="ttest_ind", statistic=object(), p_value=0.03)
    # Act
    # Assert
    with pytest.raises(TypeError):
        ss.format_results(**kwargs)


def test_formatter_mcp_delegates_all_arguments(observe_native):
    # Arrange: observe the actual function entry; retain real calculations.
    from scitex_stats._mcp._handlers._format import format_results_handler

    kwargs = dict(test_name="ttest_ind", statistic=-3.21, p_value=0.0022, df=58, effect_size=-0.83, effect_size_name="d", style="brief", ci_lower=-1.2, ci_upper=-0.4)
    expected = ss.format_results(**kwargs)
    # Act
    with observe_native(ss.format_results) as calls:
        result = asyncio.run(format_results_handler(**kwargs))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (calls, result["success"], payload) == ([kwargs], True, expected)
