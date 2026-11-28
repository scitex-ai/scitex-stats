#!/usr/bin/env python3
# File: src/scitex_stats/auto/_format_results.py

"""Format one test result as a journal-style line plus significance stars."""

from __future__ import annotations

from typing import Optional

from ._formatting import (
    EffectResultDict,
    TestResultDict,
    format_test_line,
    p_to_stars,
)

__all__ = ["format_results"]

_STYLE_IDS = {
    "apa": "apa_latex",
    "nature": "nature",
    "science": "science",
    "brief": "brief",
}


def format_results(
    test_name: str,
    statistic: float,
    p_value: float,
    df: Optional[float] = None,
    effect_size: Optional[float] = None,
    effect_size_name: Optional[str] = None,
    style: str = "apa",
    ci_lower: Optional[float] = None,
    ci_upper: Optional[float] = None,
) -> dict:
    """Format a statistic, p-value and optional effect size in journal style.

    Parameters
    ----------
    test_name, statistic, p_value, df
        The test and its result.
    effect_size, effect_size_name, ci_lower, ci_upper
        Optional effect size (default label "Cohen's d") and its CI.
    style
        ``"apa"`` (default; unknown names fall back to it), ``"nature"``,
        ``"science"`` or ``"brief"``.

    Returns
    -------
    dict
        ``style`` (as requested), ``formatted`` (the line) and ``stars``.
    """
    test_result: TestResultDict = {
        "test_name": test_name,
        "stat": statistic,
        "p_raw": p_value,
    }
    if df is not None:
        test_result["df"] = df

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

    formatted = format_test_line(
        test_result,
        effects=effects,
        style=_STYLE_IDS.get(style, "apa_latex"),
        include_n=False,
    )
    return {"style": style, "formatted": formatted, "stars": p_to_stars(p_value)}


# EOF
