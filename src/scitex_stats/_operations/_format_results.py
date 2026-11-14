"""Native statistical result formatting shared by Python and MCP."""

from __future__ import annotations

__all__ = ["format_results"]


def format_results(
    test_name: str,
    statistic: float,
    p_value: float,
    df: float | None = None,
    effect_size: float | None = None,
    effect_size_name: str | None = None,
    style: str = "apa",
    ci_lower: float | None = None,
    ci_upper: float | None = None,
) -> dict:
    """Return a formatted result, significance stars and the requested style.

    Styles are apa, nature, science and brief. Other names use APA formatting;
    the style field echoes the requested name. Supply an effect size and its
    optional interval to include them. Return native values without transport
    status or timestamps; formatting exceptions propagate to the caller.
    """
    from scitex_stats.auto import format_test_line, p_to_stars
    from scitex_stats.auto._formatting import EffectResultDict, TestResultDict

    # Build test result dict
    test_result: TestResultDict = {
        "test_name": test_name,
        "stat": statistic,
        "p_raw": p_value,
    }
    if df is not None:
        test_result["df"] = df

    # Build effect result if provided
    effects = None
    if effect_size is not None:
        effects = [
            EffectResultDict(
                name=effect_size_name or "d",
                label=effect_size_name or "Cohen's d",
                value=effect_size,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
            )
        ]

    # Map style names
    style_map = {
        "apa": "apa_latex",
        "nature": "nature",
        "science": "science",
        "brief": "brief",
    }
    style_id = style_map.get(style, "apa_latex")

    # Format the line
    formatted = format_test_line(
        test_result,
        effects=effects,
        style=style_id,
        include_n=False,
    )

    # Get stars representation
    stars = p_to_stars(p_value)

    return {
        "style": style,
        "formatted": formatted,
        "stars": stars,
    }
