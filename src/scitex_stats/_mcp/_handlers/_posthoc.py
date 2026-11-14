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
        if len(groups) < 2:
            raise ValueError("At least two groups are required for post-hoc comparisons")
        if group_names and len(group_names) != len(groups):
            raise ValueError("group_names must match the number of groups")
        if method == "dunnett" and not 0 <= control_group < len(groups):
            raise ValueError("control_group must be an index from 0 to the number of groups minus 1")

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
    """Compare controls using the native pooled-t/Bonferroni approximation."""
    from scitex_stats.posthoc._dunnett import _dunnett_statistics

    indices = [i for i in range(len(group_arrays)) if i != control_group]
    rows = _dunnett_statistics(
        group_arrays[control_group], [group_arrays[i] for i in indices],
        alternative="two-sided",
    )
    return [{"group": names[i], "vs_control": names[control_group],
             "mean_diff": float(row["mean_diff"]), "t_statistic": float(row["t_statistic"]),
             "p_value": float(row["pvalue_raw"]), "p_adj": float(row["pvalue"]),
             "reject": bool(row["pvalue"] < .05)} for i, row in zip(indices, rows)]


def _games_howell(group_arrays, names):
    """Games-Howell test (doesn't assume equal variances)."""
    from scipy import stats as scipy_stats

    comparisons = []
    n_comparisons = len(group_arrays) * (len(group_arrays) - 1) // 2

    for i in range(len(group_arrays)):
        for j in range(i + 1, len(group_arrays)):
            g1, g2 = group_arrays[i], group_arrays[j]
            n1, n2 = len(g1), len(g2)
            m1, m2 = np.mean(g1), np.mean(g2)
            v1, v2 = np.var(g1, ddof=1), np.var(g2, ddof=1)

            se = np.sqrt(v1 / n1 + v2 / n2)
            t_stat = (m1 - m2) / se

            # Welch-Satterthwaite df
            df = (v1 / n1 + v2 / n2) ** 2 / (
                (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
            )

            p = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), df))
            p_adj = min(p * n_comparisons, 1.0)

            comparisons.append(
                {
                    "group1": names[i],
                    "group2": names[j],
                    "mean_diff": float(m1 - m2),
                    "t_statistic": float(t_stat),
                    "df": float(df),
                    "p_value": float(p),
                    "p_adj": float(p_adj),
                    "reject": p_adj < 0.05,
                }
            )

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
