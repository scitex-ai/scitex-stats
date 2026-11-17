#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_posthoc.py

"""Post-hoc test handler."""

from __future__ import annotations

import asyncio
from datetime import datetime
from itertools import combinations

import numpy as np

__all__ = ["posthoc_test_handler"]


async def posthoc_test_handler(
    groups: list[list[float]],
    group_names: list[str] | None = None,
    method: str = "tukey",
    control_group: int = 0,
) -> dict:
    """Run post-hoc pairwise comparisons."""
    try:
        loop = asyncio.get_event_loop()

        def do_posthoc():
            if group_names is not None and (
                len(group_names) != len(groups)
                or len(set(group_names)) != len(group_names)
            ):
                raise ValueError("group_names must contain one unique name per group")
            group_arrays = [np.array(g, dtype=float) for g in groups]
            names = group_names or [f"Group_{i + 1}" for i in range(len(groups))]

            if method == "tukey":
                comparisons = _tukey_hsd(group_arrays, names)
            elif method == "dunnett":
                comparisons = _dunnett(group_arrays, names, control_group)
            elif method == "games_howell":
                comparisons = _games_howell(group_arrays, names)
            elif method == "dunn":
                comparisons = _dunn(group_arrays, names)
            else:
                raise ValueError(f"Unknown method: {method}")

            return comparisons

        comparisons = await loop.run_in_executor(None, do_posthoc)

        return {
            "success": True,
            "method": method,
            "n_groups": len(groups),
            "n_comparisons": len(comparisons),
            "comparisons": comparisons,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _tukey_hsd(group_arrays, names):
    """Tukey HSD test."""
    all_data = np.concatenate(group_arrays)
    group_labels = np.concatenate(
        [[names[i]] * len(g) for i, g in enumerate(group_arrays)]
    )

    comparisons = []

    try:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        tukey = pairwise_tukeyhsd(all_data, group_labels)

        # Numeric arrays retain precision lost by the formatted summary table.
        for i, (group1, group2) in enumerate(combinations(tukey.groupsunique, 2)):
            comparisons.append(
                {
                    "group1": str(group1),
                    "group2": str(group2),
                    "mean_diff": float(tukey.meandiffs[i]),
                    "p_adj": float(tukey.pvalues[i]),
                    "ci_lower": float(tukey.confint[i, 0]),
                    "ci_upper": float(tukey.confint[i, 1]),
                    "reject": bool(tukey.reject[i]),
                }
            )
    except ImportError as error:
        raise ImportError(
            "Tukey HSD backend is unavailable; cannot run the requested method."
        ) from error

    return comparisons


def _dunnett(group_arrays, names, control_group):
    """Dunnett's test (compare all to control)."""
    from scipy import stats as scipy_stats

    control = group_arrays[control_group]
    n_comparisons = len(group_arrays) - 1

    comparisons = []
    for i, (name, group) in enumerate(zip(names, group_arrays)):
        if i == control_group:
            continue
        stat, p = scipy_stats.ttest_ind(group, control)
        p_adj = min(p * n_comparisons, 1.0)
        comparisons.append(
            {
                "group": name,
                "vs_control": names[control_group],
                "mean_diff": float(np.mean(group) - np.mean(control)),
                "t_statistic": float(stat),
                "p_value": float(p),
                "p_adj": float(p_adj),
                "reject": p_adj < 0.05,
            }
        )

    return comparisons


def _games_howell(group_arrays, names):
    """Adapt the native studentized-range Games–Howell comparisons."""
    from scipy import stats as scipy_stats

    from scitex_stats.posthoc._auto import _games_howell as native_games_howell

    if len(group_arrays) < 2 or any(
        group.ndim != 1 or group.size < 2 or not np.isfinite(group).all()
        for group in group_arrays
    ):
        raise ValueError("Games-Howell requires at least two finite 1D groups of size >= 2")
    variances = [float(np.var(group, ddof=1)) for group in group_arrays]
    if not np.isfinite(variances).all():
        raise ValueError("Games-Howell sample variances must be finite")
    if any(
        variances[i] == variances[j] == 0
        for i in range(len(variances)) for j in range(i + 1, len(variances))
    ):
        raise ValueError("Games-Howell is undefined for a pair of constant groups")

    comparisons = []
    for row in native_games_howell(group_arrays, alpha=0.05, level=0.95):
        # Retain the signed Welch diagnostic fields. The decision uses the
        # native Games–Howell family-wise p, not a Bonferroni multiplier.
        t_stat = float(np.copysign(row["statistic"] / np.sqrt(2), row["mean_diff"]))
        raw_p = float(2 * scipy_stats.t.sf(abs(t_stat), row["df"]))
        comparisons.append({
            "group1": names[row["i"]], "group2": names[row["j"]],
            "mean_diff": row["mean_diff"], "t_statistic": t_stat,
            "df": row["df"], "p_value": raw_p, "p_adj": row["p_adjusted"],
            "reject": bool(row["p_adjusted"] < 0.05),
            "q_statistic": row["statistic"],
            "ci_lower": row["diff_ci"][0], "ci_upper": row["diff_ci"][1],
            "confidence_level": 0.95,
        })
    return comparisons


def _dunn(group_arrays, names):
    """Adapt the native tie-corrected Dunn calculation with Bonferroni adjustment."""
    from scitex_stats.posthoc._auto import _dunn as native_dunn

    rows = native_dunn(group_arrays, alpha=0.05, level=0.95, correction="bonferroni")
    return [{
        "group1": names[row["i"]], "group2": names[row["j"]],
        "mean_rank_diff": row["mean_rank_diff"], "z_statistic": row["statistic"],
        "p_value": row["p_unadjusted"], "p_adj": row["p_adjusted"],
        "reject": bool(row["p_adjusted"] < 0.05),
    } for row in rows]


# EOF
