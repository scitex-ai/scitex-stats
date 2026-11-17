"""Synchronous legacy result-line formatting shared by Python and MCP."""

from __future__ import annotations

from ._formatting import (
    EffectResultDict,
    TestResultDict,
    format_test_line,
    p_to_stars,
)
from ._styles import get_stat_style

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
    """Format supplied values with the existing legacy result-line presets.

    Return native data: formatted text, stars, requested style and style_used.
    No transport success/timestamp fields or coroutine are returned. APA,
    Nature and brief select APA LaTeX, Nature LaTeX and plain respectively;
    Science and unknown names retain the legacy APA fallback. This does not
    establish complete journal compliance or compute statistical corrections.

    Supplied effect intervals require a finite estimate and two finite ordered
    bounds; invalid intervals raise ValueError. Omitting both bounds preserves
    point-only output. No interval or confidence level is calculated/inferred.
    Broader legacy scalar validation remains outside this facade's scope.
    """
    test_result: TestResultDict = {
        "test_name": test_name,
        "stat": statistic,
        "p_raw": p_value,
    }
    if df is not None:
        test_result["df"] = df

    effects = None
    if effect_size is not None or ci_lower is not None or ci_upper is not None:
        effect = EffectResultDict(
            name=effect_size_name or "d",
            label=effect_size_name or "Cohen's d",
            ci_lower=ci_lower,
            ci_upper=ci_upper,
        )
        if effect_size is not None:
            effect["value"] = effect_size
        effects = [effect]

    style_map = {
        "apa": "apa_latex",
        "nature": "nature_latex",
        "science": "apa_latex",
        "brief": "plain",
    }
    selected_style = get_stat_style(style_map.get(style, "apa_latex"))
    return {
        "formatted": format_test_line(
            test_result, effects=effects, style=selected_style, include_n=False
        ),
        "stars": p_to_stars(p_value, style=selected_style),
        "style": style,
        "style_used": selected_style.id,
    }
