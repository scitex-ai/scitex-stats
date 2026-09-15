#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_assumptions.py
"""Assumption checks: Shapiro–Wilk, Levene / Brown–Forsythe, expected counts.

All checks are closed-form (no resampling), so results are deterministic; the
seed is still recorded in the thresholds so any future randomised check uses it.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

from ._data import Prepared
from ._messages import fmt_p, note

DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "alpha": 0.05,
    "normality_test": "Shapiro–Wilk",
    "normality_alpha": 0.05,
    "normality_min_n": 3,
    "normality_low_power_n": 20,
    "normality_oversensitive_n": 300,
    "variance_test": "Brown–Forsythe (Levene, median-centred)",
    "variance_alpha": 0.05,
    "min_n_per_group": 2,
    "brunner_munzel_min_n": 10,
    "chi2_min_expected": 5,
    "seed": 42,
}


def thresholds(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    th = dict(DEFAULT_THRESHOLDS)
    if overrides:
        unknown = set(overrides) - set(th)
        if unknown:
            raise ValueError(f"unknown threshold(s): {sorted(unknown)}")
        th.update(overrides)
    return th


def _shapiro(label: str, x: np.ndarray, th: Dict[str, Any]) -> Dict[str, Any]:
    n = int(len(x))
    out: Dict[str, Any] = {"sample": label, "n": n, "W": None, "p": None, "normal": None, "caveats": []}
    if n < th["normality_min_n"]:
        out["caveats"].append(note("%s: too few values for Shapiro–Wilk (n = %s)", label, n))
        return out
    if float(np.ptp(x)) == 0.0:
        out["caveats"].append(note("%s: all values are identical; normality cannot be assessed", label))
        return out
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w, p = stats.shapiro(x)
    out.update(W=float(w), p=float(p), normal=bool(p >= th["normality_alpha"]))
    if n < th["normality_low_power_n"]:
        out["caveats"].append(note("%s: Shapiro–Wilk has low power at n = %s; a non-significant result does not show normality", label, n))
    if n > th["normality_oversensitive_n"]:
        out["caveats"].append(note("%s: Shapiro–Wilk is oversensitive at n = %s; trivial departures reach significance", label, n))
    return out


def _combine(samples: List[Dict[str, Any]], basis: str, th: Dict[str, Any]) -> Dict[str, Any]:
    flags = [s["normal"] for s in samples]
    if any(f is False for f in flags):
        status = "violated"
    elif flags and all(f is True for f in flags):
        status = "met"
    else:
        status = "unknown"
    return {
        "status": status,
        "basis": basis,
        "test": th["normality_test"],
        "alpha": th["normality_alpha"],
        "samples": samples,
        "rejected_in": [s["sample"] for s in samples if s["normal"] is False],
    }


def normality(prep: Prepared, th: Dict[str, Any]) -> Dict[str, Any]:
    """Per-group normality (independent), of differences (2 paired) or residuals (k paired)."""
    if prep.table is not None or not prep.groups:
        return {"status": "not_applicable", "basis": None, "samples": []}
    same_len = len({len(g) for g in prep.groups}) == 1
    if prep.design == "paired" and same_len and prep.k == 2:
        d = prep.groups[0] - prep.groups[1]
        return _combine([_shapiro("differences", d, th)], "paired differences", th)
    if prep.design == "paired" and same_len and prep.k >= 3:
        X = np.column_stack(prep.groups)
        resid = X - X.mean(axis=1, keepdims=True) - X.mean(axis=0, keepdims=True) + X.mean()
        return _combine([_shapiro("residuals", resid.ravel(), th)], "residuals (subject + condition)", th)
    return _combine([_shapiro(n, g, th) for n, g in zip(prep.names, prep.groups)], "each group", th)


def variance(prep: Prepared, th: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "status": "not_applicable", "test": th["variance_test"], "alpha": th["variance_alpha"],
        "brown_forsythe": None, "levene": None, "variance_ratio": None,
    }
    if prep.table is not None or prep.k < 2:
        return out
    if min(len(g) for g in prep.groups) < 2:
        out["status"] = "unknown"
        return out
    variances = [float(np.var(g, ddof=1)) for g in prep.groups]
    if min(variances) > 0:
        out["variance_ratio"] = max(variances) / min(variances)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bf = stats.levene(*prep.groups, center="median")
        lv = stats.levene(*prep.groups, center="mean")
    if not np.isfinite(bf.pvalue):
        out["status"] = "unknown"
        return out
    out["brown_forsythe"] = {"statistic": float(bf.statistic), "p": float(bf.pvalue), "p_apa": fmt_p(bf.pvalue)}
    if np.isfinite(lv.pvalue):
        out["levene"] = {"statistic": float(lv.statistic), "p": float(lv.pvalue), "p_apa": fmt_p(lv.pvalue)}
    out["status"] = "met" if bf.pvalue >= th["variance_alpha"] else "violated"
    return out


def expected_counts(prep: Prepared, th: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "not_applicable", "threshold": th["chi2_min_expected"]}
    t = prep.table
    if t is None:
        return out
    if t.ndim != 2 or t.shape[0] < 2 or t.shape[1] < 2 or (t.sum(axis=0) == 0).any() or (t.sum(axis=1) == 0).any():
        out["status"] = "unknown"
        return out
    exp = stats.contingency.expected_freq(t)
    below = int((exp < th["chi2_min_expected"]).sum())
    out.update(
        status="met" if below == 0 else "violated",
        min_expected=float(exp.min()),
        cells_below=below,
        cells=int(exp.size),
        expected=exp.tolist(),
    )
    return out


def run_checks(prep: Prepared, th: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "normality": normality(prep, th),
        "equal_variance": variance(prep, th),
        "expected_counts": expected_counts(prep, th),
    }


# EOF
