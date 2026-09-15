#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_applicability.py
"""Per-test applicability: every test gets ✓/✗ plus the reasons behind it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ._assumptions import run_checks, thresholds
from ._data import Prepared, prepare
from ._messages import fail, fmt_alpha, fmt_p, note, ok


@dataclass(frozen=True)
class Spec:
    test_id: str
    label: str
    symbol: str
    scales: Tuple[str, ...]
    design: Optional[str]  # "independent" | "paired"
    min_groups: int
    max_groups: Optional[int]
    needs_normality: bool = False
    needs_equal_variance: bool = False
    table: bool = False


_NUM = ("continuous",)
_RANK = ("continuous", "ordinal")

CATALOG: List[Spec] = [
    Spec("ttest_welch", "Welch's t-test", "t", _NUM, "independent", 2, 2, needs_normality=True),
    Spec("ttest_ind", "Student's t-test", "t", _NUM, "independent", 2, 2, needs_normality=True, needs_equal_variance=True),
    Spec("mannwhitneyu", "Mann–Whitney U test", "U", _RANK, "independent", 2, 2),
    Spec("brunner_munzel", "Brunner–Munzel test", "BM", _RANK, "independent", 2, 2),
    Spec("ttest_rel", "Paired t-test", "t", _NUM, "paired", 2, 2, needs_normality=True),
    Spec("wilcoxon", "Wilcoxon signed-rank test", "W", _RANK, "paired", 2, 2),
    Spec("welch_anova", "Welch's ANOVA", "F", _NUM, "independent", 3, None, needs_normality=True),
    Spec("anova", "One-way ANOVA", "F", _NUM, "independent", 3, None, needs_normality=True, needs_equal_variance=True),
    Spec("kruskal", "Kruskal–Wallis H test", "H", _RANK, "independent", 3, None),
    Spec("anova_rm", "Repeated-measures ANOVA", "F", _NUM, "paired", 3, None, needs_normality=True),
    Spec("friedman", "Friedman test", "χ²", _RANK, "paired", 3, None),
    Spec("chi2", "Chi-square test of independence", "χ²", ("categorical",), "independent", 2, None, table=True),
    Spec("fisher", "Fisher's exact test", "OR", ("categorical",), "independent", 2, 2, table=True),
]
SPECS: Dict[str, Spec] = {s.test_id: s for s in CATALOG}


def _scale_items(spec: Spec, prep: Prepared) -> List[Dict[str, Any]]:
    if prep.scale in spec.scales:
        return [ok("Scale: %s", prep.scale)]
    if spec.table:
        return [fail("Needs a contingency table of counts; the data are %s", prep.scale)]
    if spec.scales == _NUM:
        return [fail("Needs continuous data; the data are %s", prep.scale)]
    return [fail("Needs continuous or ordinal data; the data are %s", prep.scale)]


def _design_items(spec: Spec, prep: Prepared) -> List[Dict[str, Any]]:
    if spec.table and prep.table is not None and prep.design == "paired":
        return [fail("Needs independent observations; paired counts need McNemar's test (not covered here)")]
    if spec.table:
        return []
    if spec.design == prep.design:
        return [ok("Independent groups" if spec.design == "independent" else "Paired (repeated) measurements")]
    if spec.design == "independent":
        return [fail("Needs independent groups; the design is paired")]
    return [fail("Needs paired measurements; the design is independent")]


def _group_items(spec: Spec, prep: Prepared, th: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if spec.table:
        if prep.table is None:
            return items
        r, c = prep.table.shape
        if r < 2 or c < 2:
            return [fail("Needs a table with at least 2 rows and 2 columns; the table is %s × %s", r, c)]
        if spec.max_groups == 2 and (r, c) != (2, 2):
            return [fail("Needs a 2 × 2 table; the table is %s × %s", r, c)]
        return [ok("Table: %s × %s", r, c)]
    k = prep.k
    if spec.max_groups == 2 and k != 2:
        items.append(fail("Needs exactly 2 groups; there are %s", k))
    elif k < spec.min_groups:
        items.append(fail("Needs 3 or more groups; there are %s", k))
    else:
        items.append(ok("Groups: %s", k))
    if prep.groups:
        smallest = min(len(g) for g in prep.groups)
        if smallest < th["min_n_per_group"]:
            items.append(fail("Each group needs n ≥ %s; the smallest n = %s", th["min_n_per_group"], smallest))
    if spec.design == "paired" and prep.design == "paired" and prep.paired_length_mismatch:
        items.append(fail("Paired groups must have the same length (%s)", ", ".join(str(n) for n in prep.raw_n)))
    return items


def _normality_items(spec: Spec, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
    norm = checks["normality"]
    if spec.table:
        return []
    if not spec.needs_normality:
        return [ok("No normality assumption (rank-based)")]
    alpha = fmt_alpha(norm["alpha"]) if norm.get("alpha") is not None else None
    status = norm["status"]
    if status == "met":
        return [ok("Normality not rejected (Shapiro–Wilk p ≥ %s, %s)", alpha, norm["basis"])]
    if status == "violated":
        return [fail("Normality rejected (Shapiro–Wilk p < %s in %s)", alpha, ", ".join(norm["rejected_in"]))]
    return [fail("Normality cannot be assessed (fewer than 3 values or constant values)")]


def _variance_items(spec: Spec, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
    var = checks["equal_variance"]
    if spec.table or spec.design == "paired":
        return []
    bf = var.get("brown_forsythe")
    if not spec.needs_equal_variance:
        if spec.test_id in ("ttest_welch", "welch_anova"):
            return [ok("Does not assume equal variances")]
        if spec.test_id == "mannwhitneyu" and var["status"] == "violated":
            return [note("Spreads differ (Brown–Forsythe p %s): read the result as stochastic dominance, not a shift in location", bf["p_apa"])]
        return []
    if var["status"] == "met":
        return [ok("Equal variances not rejected (Brown–Forsythe p %s)", bf["p_apa"])]
    if var["status"] == "violated":
        return [fail("Variances differ (Brown–Forsythe p %s)", bf["p_apa"])]
    return [fail("Equal variances cannot be assessed")]


def _special_items(spec: Spec, prep: Prepared, checks: Dict[str, Any], th: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if spec.test_id == "chi2" and prep.table is not None:
        ec = checks["expected_counts"]
        if ec["status"] == "met":
            items.append(ok("All expected counts ≥ %s (minimum %s)", th["chi2_min_expected"], round(ec["min_expected"], 2)))
        elif ec["status"] == "violated":
            items.append(fail("Expected count below %s in %s of %s cells (minimum %s)", th["chi2_min_expected"], ec["cells_below"], ec["cells"], round(ec["min_expected"], 2)))
        else:
            items.append(fail("Expected counts cannot be computed (a row or column total is zero)"))
    if spec.test_id == "fisher" and prep.table is not None:
        items.append(ok("Exact test: valid at any expected count"))
    if spec.test_id == "wilcoxon" and prep.design == "paired" and prep.k == 2 and not prep.paired_length_mismatch and prep.groups:
        if len(prep.groups[0]) and np.all(prep.groups[0] == prep.groups[1]):
            items.append(fail("All paired differences are zero"))
    if spec.test_id == "brunner_munzel" and prep.groups and prep.k == 2 and min(len(g) for g in prep.groups):
        x, y = prep.groups
        if x.max() < y.min() or y.max() < x.min():
            items.append(fail("The groups do not overlap: the Brunner–Munzel variance estimate is zero, so the test is undefined"))
        if min(len(g) for g in prep.groups) < th["brunner_munzel_min_n"]:
            items.append(note("Small samples (n < %s): the Brunner–Munzel approximation is less accurate", th["brunner_munzel_min_n"]))
    if spec.test_id == "anova_rm" and prep.design == "paired":
        items.append(note("Sphericity is checked when the test runs (Greenhouse–Geisser correction if violated)"))
    return items


def _assumption_summary(spec: Spec, checks: Dict[str, Any]) -> Dict[str, Any]:
    def status(key: str, needed: bool) -> Dict[str, Any]:
        entry = dict(checks[key])
        entry["required"] = needed
        return entry

    return {
        "normality": status("normality", spec.needs_normality),
        "equal_variance": status("equal_variance", spec.needs_equal_variance),
        "expected_counts": status("expected_counts", spec.test_id == "chi2"),
    }


def evaluate(spec: Spec, prep: Prepared, checks: Dict[str, Any], th: Dict[str, Any]) -> Dict[str, Any]:
    items = _scale_items(spec, prep)
    if prep.scale in spec.scales:
        items += _design_items(spec, prep) + _group_items(spec, prep, th)
        items += _normality_items(spec, checks) + _variance_items(spec, checks)
        items += _special_items(spec, prep, checks, th)
    applicable = not any(i["status"] == "fail" for i in items)
    return {
        "test_id": spec.test_id,
        "label": spec.label,
        "applicable": applicable,
        "reasons": [i["text"] for i in items],
        "reason_items": items,
        "assumptions": _assumption_summary(spec, checks),
    }


def assess(
    data: Any,
    design: Optional[str] = None,
    *,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    thresholds_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Full report: data summary, every check, thresholds, per-test applicability."""
    th = thresholds(thresholds_override)
    prep = prepare(data, design=design, scale=scale, group_names=group_names)
    checks = run_checks(prep, th)
    tests = [evaluate(spec, prep, checks, th) for spec in CATALOG]
    caveats = [c for s in checks["normality"].get("samples", []) for c in s["caveats"]]
    if not prep.design_specified and prep.table is None and prep.k >= 2 and len({len(g) for g in prep.groups}) == 1:
        caveats.append(note("Groups have equal length: if these are repeated measurements on the same subjects, set the design to paired."))
    return {
        "data": prep.summary(),
        "checks": checks,
        "thresholds": th,
        "notes": prep.notes + caveats,
        "tests": tests,
        "_prep": prep,
    }


def check_applicability(
    data: Any,
    design: Optional[str] = None,
    *,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Decide, for every test in the catalogue, whether it applies to ``data``.

    Parameters
    ----------
    data : list of sequences | dict | pandas.DataFrame | 2-D array
        One sequence per group. With ``scale="categorical"`` a contingency
        table (rows of counts).
    design : {"independent", "paired"} or None
        Aliases: between/unpaired, within/repeated/related. ``None`` is
        treated as independent and says so in every test's ``assumptions``
        and in :func:`recommend_test`'s notes; it is never guessed from data.
    scale : {"continuous", "ordinal", "categorical"} or None
        ``None`` is treated as continuous (recorded the same way).
    group_names : list of str, optional
    thresholds : dict, optional
        Override any of :data:`DEFAULT_THRESHOLDS` (alpha levels, minimum n, …).

    Returns
    -------
    list of dict
        ``{test_id, label, applicable, reasons, reason_items, assumptions}``
        per test. ``assumptions`` holds the full evidence (Shapiro–Wilk per
        sample, Levene and Brown–Forsythe, expected counts) with the
        thresholds used.

    Examples
    --------
    >>> rows = check_applicability([[5.1, 4.9, 5.6, 5.8], [6.3, 6.8, 6.1, 7.0]], design="independent")
    >>> [r["test_id"] for r in rows if r["applicable"]][:2]
    ['ttest_welch', 'ttest_ind']
    """
    report = assess(data, design, scale=scale, group_names=group_names, thresholds_override=thresholds)
    for row in report["tests"]:
        row["assumptions"]["thresholds"] = report["thresholds"]
    return report["tests"]


def welch_anova(groups: List[np.ndarray]) -> Dict[str, Any]:
    """Welch's heteroscedastic one-way ANOVA (Welch, 1951)."""
    from scipy import stats

    k = len(groups)
    n = np.array([len(g) for g in groups], dtype=float)
    m = np.array([np.mean(g) for g in groups])
    v = np.array([np.var(g, ddof=1) for g in groups])
    w = n / v
    sw = w.sum()
    grand = (w * m).sum() / sw
    a = (w * (m - grand) ** 2).sum() / (k - 1)
    lam = (((1 - w / sw) ** 2) / (n - 1)).sum()
    b = 1 + 2 * (k - 2) * lam / (k**2 - 1)
    f = a / b
    df2 = (k**2 - 1) / (3 * lam)
    return {
        "test_method": "Welch's ANOVA",
        "statistic": float(f),
        "stat_symbol": "F",
        "df": [float(k - 1), float(df2)],
        "pvalue": float(stats.f.sf(f, k - 1, df2)),
    }


# EOF
