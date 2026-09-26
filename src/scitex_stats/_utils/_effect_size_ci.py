#!/usr/bin/env python3
# File: scitex_stats/_utils/_effect_size_ci.py
"""Confidence intervals for effect sizes the tests report."""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import stats


def cohens_d_ci(
    d: float, n1: int, n2: Optional[int] = None, alpha: float = 0.05
) -> dict:
    """Normal-approximation CI for Cohen's d (Hedges & Olkin, 1985, eq. 5.14).

    ``n2=None`` is the one-sample / paired (d_z) case with n = ``n1``.
    Returns ``effect_size_ci_lower``, ``effect_size_ci_upper`` and
    ``ci_level``; an empty dict when n is too small or d is not finite.
    """
    if d is None or not np.isfinite(d) or n1 < 2 or (n2 is not None and n2 < 2):
        return {}
    if n2 is None:
        se = np.sqrt(1 / n1 + d**2 / (2 * n1))
    else:
        se = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    z = stats.norm.ppf(1 - alpha / 2)
    return {
        "effect_size_ci_lower": float(d - z * se),
        "effect_size_ci_upper": float(d + z * se),
        "ci_level": 1 - alpha,
    }


def mannwhitney_z(u: float, x, y) -> Optional[float]:
    """Tie-corrected normal approximation z for U of ``x`` (no continuity)."""
    n1, n2 = len(x), len(y)
    n = n1 + n2
    if n1 == 0 or n2 == 0:
        return None
    _, counts = np.unique(np.concatenate([x, y]), return_counts=True)
    tie = float(np.sum(counts**3 - counts))
    var = n1 * n2 / 12 * ((n + 1) - tie / (n * (n - 1)))
    if var <= 0:
        return None
    return float((u - n1 * n2 / 2) / np.sqrt(var))


def wilcoxon_z(diff) -> Optional[float]:
    """Tie-corrected normal approximation z for W+ over non-zero differences."""
    d = np.asarray(diff, dtype=float)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return None
    ranks = stats.rankdata(np.abs(d))
    w_plus = float(np.sum(ranks[d > 0]))
    _, counts = np.unique(np.abs(d), return_counts=True)
    var = n * (n + 1) * (2 * n + 1) / 24 - float(np.sum(counts**3 - counts)) / 48
    if var <= 0:
        return None
    return float((w_plus - n * (n + 1) / 4) / np.sqrt(var))


def brunner_munzel_df(x, y) -> Optional[float]:
    """Satterthwaite df of the Brunner–Munzel statistic (as scipy computes it)."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return None
    rankc = stats.rankdata(np.concatenate([x, y]))
    rcx, rcy = rankc[:nx], rankc[nx:]
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    sx = np.sum((rcx - rx - rcx.mean() + rx.mean()) ** 2) / (nx - 1)
    sy = np.sum((rcy - ry - rcy.mean() + ry.mean()) ** 2) / (ny - 1)
    denom = (nx * sx) ** 2 / (nx - 1) + (ny * sy) ** 2 / (ny - 1)
    if denom == 0:
        return None
    return float((nx * sx + ny * sy) ** 2 / denom)


__all__ = ["cohens_d_ci", "mannwhitney_z", "wilcoxon_z", "brunner_munzel_df"]

# EOF
