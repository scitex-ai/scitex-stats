#!/usr/bin/env python3
# Timestamp: 2026-01-25
# File: src/scitex/stats/_mcp/_handlers/_posthoc.py

"""Post-hoc test handler."""

from __future__ import annotations

import asyncio
from datetime import datetime

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
    from scipy import stats as scipy_stats

    all_data = np.concatenate(group_arrays)
    group_labels = np.concatenate(
        [[names[i]] * len(g) for i, g in enumerate(group_arrays)]
    )

    comparisons = []

    try:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        tukey = pairwise_tukeyhsd(all_data, group_labels)

        for i in range(len(tukey.summary().data) - 1):
            row = tukey.summary().data[i + 1]
            comparisons.append(
                {
                    "group1": str(row[0]),
                    "group2": str(row[1]),
                    "mean_diff": float(row[2]),
                    "p_adj": float(row[3]),
                    "ci_lower": float(row[4]),
                    "ci_upper": float(row[5]),
                    "reject": bool(row[6]),
                }
            )
    except ImportError:
        # Fallback: Bonferroni-corrected t-tests
        n_comparisons = len(group_arrays) * (len(group_arrays) - 1) // 2
        for i in range(len(group_arrays)):
            for j in range(i + 1, len(group_arrays)):
                stat, p = scipy_stats.ttest_ind(group_arrays[i], group_arrays[j])
                p_adj = min(p * n_comparisons, 1.0)
                comparisons.append(
                    {
                        "group1": names[i],
                        "group2": names[j],
                        "mean_diff": float(
                            np.mean(group_arrays[i]) - np.mean(group_arrays[j])
                        ),
                        "t_statistic": float(stat),
                        "p_value": float(p),
                        "p_adj": float(p_adj),
                        "reject": p_adj < 0.05,
                    }
                )

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
    """Dunn's test for Kruskal-Wallis post-hoc."""
    from scipy import stats as scipy_stats

    all_data = np.concatenate(group_arrays)
    ranks = scipy_stats.rankdata(all_data)

    # Assign ranks to groups
    idx = 0
    group_ranks = []
    for g in group_arrays:
        group_ranks.append(ranks[idx : idx + len(g)])
        idx += len(g)

    n_total = len(all_data)
    n_comparisons = len(group_arrays) * (len(group_arrays) - 1) // 2

    comparisons = []
    for i in range(len(group_arrays)):
        for j in range(i + 1, len(group_arrays)):
            n_i, n_j = len(group_arrays[i]), len(group_arrays[j])
            r_i, r_j = np.mean(group_ranks[i]), np.mean(group_ranks[j])

            se = np.sqrt(n_total * (n_total + 1) / 12 * (1 / n_i + 1 / n_j))
            z = (r_i - r_j) / se
            p = 2 * (1 - scipy_stats.norm.cdf(abs(z)))
            p_adj = min(p * n_comparisons, 1.0)

            comparisons.append(
                {
                    "group1": names[i],
                    "group2": names[j],
                    "mean_rank_diff": float(r_i - r_j),
                    "z_statistic": float(z),
                    "p_value": float(p),
                    "p_adj": float(p_adj),
                    "reject": p_adj < 0.05,
                }
            )

    return comparisons


# EOF
