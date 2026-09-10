#!/usr/bin/env python3
# File: src/scitex_stats/_server.py

"""MCP server for SciTeX Stats - Statistical testing framework.

This is the main server entry point. Tools are defined here using FastMCP.
"""

from __future__ import annotations

import json
from typing import List, Optional

from fastmcp import FastMCP

# =============================================================================
# FastMCP Server
# =============================================================================

mcp = FastMCP(
    name="scitex-stats",
    instructions=(
        "Statistical testing framework for publication-ready analysis. "
        "Provides 23 tests (parametric, nonparametric, correlation, categorical, normality), "
        "effect sizes, power analysis, multiple comparison corrections, and APA formatting."
    ),
)


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def recommend_tests(
    n_groups: int = 2,
    sample_sizes: Optional[List[int]] = None,
    outcome_type: str = "continuous",
    design: str = "between",
    paired: bool = False,
    has_control_group: bool = False,
    top_k: int = 3,
) -> str:
    """Recommend appropriate statistical tests based on data characteristics."""
    from scitex_stats._mcp.handlers import recommend_tests_handler

    result = await recommend_tests_handler(
        n_groups=n_groups,
        sample_sizes=sample_sizes,
        outcome_type=outcome_type,
        design=design,
        paired=paired,
        has_control_group=has_control_group,
        top_k=top_k,
    )
    return _json(result)


@mcp.tool()
async def run_test(
    test_name: str,
    data: Optional[List[List[float]]] = None,
    data_file: Optional[str] = None,
    columns: Optional[List[str]] = None,
    alternative: str = "two-sided",
) -> str:
    """Execute a statistical test on provided data."""
    from scitex_stats._mcp.handlers import run_test_handler

    result = await run_test_handler(
        test_name=test_name,
        data=data,
        data_file=data_file,
        columns=columns,
        alternative=alternative,
    )
    return _json(result)


@mcp.tool()
async def format_results(
    test_name: str,
    statistic: float,
    p_value: float,
    df: Optional[float] = None,
    effect_size: Optional[float] = None,
    effect_size_name: Optional[str] = None,
    style: str = "apa",
    ci_lower: Optional[float] = None,
    ci_upper: Optional[float] = None,
) -> str:
    """Format statistical results in journal style (APA, Nature, etc.)."""
    from scitex_stats._mcp.handlers import format_results_handler

    result = await format_results_handler(
        test_name=test_name,
        statistic=statistic,
        p_value=p_value,
        df=df,
        effect_size=effect_size,
        effect_size_name=effect_size_name,
        style=style,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
    )
    return _json(result)


@mcp.tool()
async def power_analysis(
    test_type: str = "ttest",
    effect_size: Optional[float] = None,
    alpha: float = 0.05,
    power: float = 0.8,
    n: Optional[int] = None,
    n_groups: int = 2,
    ratio: float = 1.0,
) -> str:
    """Calculate statistical power or required sample size."""
    from scitex_stats._mcp.handlers import power_analysis_handler

    result = await power_analysis_handler(
        test_type=test_type,
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        n=n,
        n_groups=n_groups,
        ratio=ratio,
    )
    return _json(result)


@mcp.tool()
async def correct_pvalues(
    pvalues: List[float],
    method: str = "fdr_bh",
    alpha: float = 0.05,
) -> str:
    """Apply multiple comparison correction to p-values."""
    from scitex_stats._mcp.handlers import correct_pvalues_handler

    result = await correct_pvalues_handler(
        pvalues=pvalues,
        method=method,
        alpha=alpha,
    )
    return _json(result)


@mcp.tool()
async def describe(
    data: List[float],
    percentiles: Optional[List[float]] = None,
) -> str:
    """Calculate descriptive statistics for data."""
    from scitex_stats._mcp.handlers import describe_handler

    result = await describe_handler(
        data=data,
        percentiles=percentiles,
    )
    return _json(result)


@mcp.tool()
async def effect_size(
    group1: List[float],
    group2: List[float],
    measure: str = "cohens_d",
    pooled: bool = True,
) -> str:
    """Calculate effect size between groups."""
    from scitex_stats._mcp.handlers import effect_size_handler

    result = await effect_size_handler(
        group1=group1,
        group2=group2,
        measure=measure,
        pooled=pooled,
    )
    return _json(result)


@mcp.tool()
async def normality_test(
    data: List[float],
    method: str = "shapiro",
) -> str:
    """Test whether data follows a normal distribution."""
    from scitex_stats._mcp.handlers import normality_test_handler

    result = await normality_test_handler(
        data=data,
        method=method,
    )
    return _json(result)


@mcp.tool()
async def posthoc_test(
    groups: List[List[float]],
    group_names: Optional[List[str]] = None,
    method: str = "tukey",
    control_group: int = 0,
) -> str:
    """Run post-hoc pairwise comparisons after significant ANOVA/Kruskal."""
    from scitex_stats._mcp.handlers import posthoc_test_handler

    result = await posthoc_test_handler(
        groups=groups,
        group_names=group_names,
        method=method,
        control_group=control_group,
    )
    return _json(result)


@mcp.tool()
async def p_to_stars(
    p_value: float,
    thresholds: Optional[List[float]] = None,
) -> str:
    """Convert p-value to significance stars (*, **, ***, ns)."""
    from scitex_stats._mcp.handlers import p_to_stars_handler

    result = await p_to_stars_handler(
        p_value=p_value,
        thresholds=thresholds,
    )
    return _json(result)


# =============================================================================
# Skills Tools
# =============================================================================


@mcp.tool()
async def skills_list() -> str:
    """List available skill pages for scitex-stats."""
    try:
        from scitex_dev.ecosystem import list_skills

        result = list_skills(package="scitex-stats")
        return _json({"success": True, "skills": result.get("scitex-stats", [])})
    except ImportError:
        return _json({"success": False, "error": "scitex-dev not installed"})


@mcp.tool()
async def skills_get(name: Optional[str] = None) -> str:
    """Get a skill page for scitex-stats. Without name, returns main SKILL.md."""
    try:
        from scitex_dev.ecosystem import get_skill

        content = get_skill(package="scitex-stats", name=name)
        if content:
            return _json({"success": True, "name": name, "content": content})
        target = f"'{name}'" if name else "SKILL.md"
        return _json({"success": False, "error": f"Skill {target} not found"})
    except ImportError:
        return _json({"success": False, "error": "scitex-dev not installed"})


# =============================================================================
# Server Entry Point
# =============================================================================


def run_server(transport: str = "stdio") -> None:
    """Run the MCP server."""
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_server()

# EOF
