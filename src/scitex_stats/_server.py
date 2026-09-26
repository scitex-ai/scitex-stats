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


def _recommend_call(fn_name: str, **kwargs) -> str:
    import scitex_stats._recommend as rec

    try:
        return _json({"success": True, **_wrap(getattr(rec, fn_name)(**kwargs))})
    except (TypeError, ValueError) as exc:
        return _json({"success": False, "error": str(exc)})


def _wrap(out):
    return {"applicability": out} if isinstance(out, list) else out


@mcp.tool()
async def check_applicability(
    groups: List[List[float]],
    design: Optional[str] = None,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
) -> str:
    """Decide for every test whether it applies to the data (✓/✗ with reasons and assumption checks).

    groups: one list per group (with scale="categorical": a contingency table, rows of counts).
    design: "independent" or "paired" — state it; None is treated as independent and flagged.
    scale: "continuous", "ordinal" or "categorical".
    """
    return _recommend_call("check_applicability", data=groups, design=design, scale=scale, group_names=group_names)


@mcp.tool()
async def recommend_test(
    groups: List[List[float]],
    design: Optional[str] = None,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    assume_equal_variance: bool = False,
) -> str:
    """Recommend ONE primary test with a plain-language reason, the decision path and secondary alternatives."""
    return _recommend_call(
        "recommend_test", data=groups, design=design, scale=scale,
        group_names=group_names, assume_equal_variance=assume_equal_variance,
    )


@mcp.tool()
async def run_all_applicable(
    groups: List[List[float]],
    design: Optional[str] = None,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    primary: Optional[str] = None,
    alternative: str = "two-sided",
) -> str:
    """Run every applicable test: the pre-specified primary plus sensitivity analyses.

    Never selects by p-value; the output carries a p-hacking warning and an agreement report.
    """
    return _recommend_call(
        "run_all_applicable", data=groups, design=design, scale=scale,
        group_names=group_names, primary=primary, alternative=alternative,
    )


@mcp.tool()
async def generate_report(
    data: Optional[dict] = None,
    data_file: Optional[str] = None,
    output: str = "report.pdf",
    design: str = "between",
    group_names: Optional[List[str]] = None,
    alpha: float = 0.05,
    posthoc: str = "auto",
    formats: Optional[List[str]] = None,
    title: str = "Statistical report",
) -> str:
    """Write one bundled report (PDF, HTML, Markdown): assumptions, primary test, sensitivity, post-hoc, figure, methods."""
    from scitex_stats._mcp.handlers import generate_report_handler

    result = await generate_report_handler(
        data=data, data_file=data_file, output=output, design=design, group_names=group_names,
        alpha=alpha, posthoc=posthoc, formats=formats, title=title,
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
async def validate_apa(
    text: str = "",
    html: Optional[str] = None,
    result: Optional[dict] = None,
) -> str:
    """Check statistics text (and optional HTML) against APA 7; returns violations with fixes."""
    from scitex_stats._utils._apa import validate_apa as _validate

    return _json(_validate(text, html=html, result=result))


@mcp.tool()
async def verify_result(
    result: Optional[dict] = None,
    result_file: Optional[str] = None,
    data: Optional[list] = None,
    data2: Optional[List[float]] = None,
    groups: Optional[List[List[float]]] = None,
) -> str:
    """Verify a result's provenance receipt, input hashes and statistics by recomputing."""
    from scitex_stats._mcp.handlers import verify_result_handler

    report = await verify_result_handler(
        result=result, result_file=result_file, data=data, data2=data2, groups=groups
    )
    return _json(report)


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
