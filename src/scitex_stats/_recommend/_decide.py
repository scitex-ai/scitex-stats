#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_decide.py
"""One pre-specified primary test, with the decision path that led to it."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ._applicability import SPECS, assess
from ._data import Prepared
from ._messages import fail, note, ok

DECISION_RULES: List[Dict[str, str]] = [
    {"when": "2 independent groups, continuous, normality not rejected", "primary": "ttest_welch", "why": "Welch is the default; Student only with a documented equal-variance reason (assume_equal_variance=True)"},
    {"when": "2 independent groups, continuous, normality rejected or not assessable", "primary": "mannwhitneyu", "why": "rank-based; Brunner–Munzel instead when spreads differ and every n ≥ 10"},
    {"when": "2 independent groups, ordinal", "primary": "mannwhitneyu", "why": "ranks only"},
    {"when": "2 paired groups, continuous, differences normal", "primary": "ttest_rel", "why": ""},
    {"when": "2 paired groups, differences not normal, or ordinal", "primary": "wilcoxon", "why": ""},
    {"when": "3+ independent groups, continuous, normal, equal variances not rejected", "primary": "anova", "why": ""},
    {"when": "3+ independent groups, continuous, normal, variances differ", "primary": "welch_anova", "why": ""},
    {"when": "3+ independent groups, not normal, or ordinal", "primary": "kruskal", "why": ""},
    {"when": "3+ paired groups, continuous, residuals normal", "primary": "anova_rm", "why": "Greenhouse–Geisser if sphericity fails"},
    {"when": "3+ paired groups, residuals not normal, or ordinal", "primary": "friedman", "why": ""},
    {"when": "contingency table, all expected counts ≥ 5", "primary": "chi2", "why": ""},
    {"when": "2 × 2 table, some expected count < 5", "primary": "fisher", "why": ""},
]

_REASON = {
    "ttest_welch": "Welch's t-test compares two independent means without assuming equal variances. It is the default over Student's t-test: it loses little power when variances are equal and keeps the false-positive rate when they are not.",
    "ttest_ind": "Student's t-test was chosen because equal variances were declared in advance (a documented reason) and are not rejected by the data.",
    "mannwhitneyu": "The Mann–Whitney U test compares two independent groups by ranks, so it does not rely on normality.",
    "brunner_munzel": "The Brunner–Munzel test compares two independent groups by ranks without assuming equal spreads, which differ here.",
    "ttest_rel": "The paired t-test compares two related measurements; the paired differences are consistent with normality.",
    "wilcoxon": "The Wilcoxon signed-rank test compares two related measurements by ranks, so it does not rely on normal differences.",
    "anova": "One-way ANOVA compares three or more independent means; normality and equal variances are not rejected.",
    "welch_anova": "Welch's ANOVA compares three or more independent means without assuming equal variances, which differ here.",
    "kruskal": "The Kruskal–Wallis H test compares three or more independent groups by ranks, so it does not rely on normality.",
    "anova_rm": "Repeated-measures ANOVA compares three or more related conditions; the residuals are consistent with normality.",
    "friedman": "The Friedman test compares three or more related conditions by ranks, so it does not rely on normality.",
    "chi2": "The chi-square test of independence applies because every expected count is at least 5.",
    "fisher": "Fisher's exact test is used because some expected counts are below 5, where the chi-square approximation is unreliable.",
}

_SECONDARY = {
    ("ttest_welch", "ttest_ind"): "Assumes equal variances; use only with a documented reason stated before seeing the data.",
    ("ttest_ind", "ttest_welch"): "Does not assume equal variances; a natural sensitivity analysis.",
    ("ttest_welch", "mannwhitneyu"): "Rank-based: less power when normality holds, and it tests stochastic ordering rather than means.",
    ("ttest_ind", "mannwhitneyu"): "Rank-based: less power when normality holds, and it tests stochastic ordering rather than means.",
    ("ttest_welch", "brunner_munzel"): "Rank-based and robust to unequal spreads, but it tests P(X < Y) = 0.5 rather than means.",
    ("ttest_ind", "brunner_munzel"): "Rank-based and robust to unequal spreads, but it tests P(X < Y) = 0.5 rather than means.",
    ("mannwhitneyu", "brunner_munzel"): "Preferred when spreads differ; here they do not, or the samples are too small for its approximation.",
    ("brunner_munzel", "mannwhitneyu"): "Assumes equal spreads under the null hypothesis; the spreads differ here.",
    ("ttest_rel", "wilcoxon"): "Rank-based: less power when the differences are normal.",
    ("anova", "welch_anova"): "Does not assume equal variances; slightly less power when they are equal. A natural sensitivity analysis.",
    ("anova", "kruskal"): "Rank-based: less power when normality holds.",
    ("welch_anova", "kruskal"): "Rank-based: less power when normality holds, and it tests stochastic ordering rather than means.",
    ("anova_rm", "friedman"): "Rank-based: less power when the residuals are normal.",
    ("chi2", "fisher"): "Exact and always valid, but conservative; not needed when every expected count is at least 5.",
}


def _path_and_primary(prep: Prepared, checks: Dict[str, Any], th: Dict[str, Any], assume_equal_variance: bool) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    path: List[Dict[str, Any]] = []
    if prep.table is not None:
        path.append(ok("Contingency table (%s × %s)", *prep.table.shape))
        if prep.design == "paired":
            path.append(fail("Paired counts need McNemar's test, which this recommender does not cover"))
            return path, None
        ec = checks["expected_counts"]
        if ec["status"] == "met":
            path.append(ok("All expected counts ≥ %s", th["chi2_min_expected"]))
            return path, "chi2"
        if ec["status"] == "violated":
            path.append(fail("Expected count below %s in %s of %s cells", th["chi2_min_expected"], ec["cells_below"], ec["cells"]))
            if prep.table.shape == (2, 2):
                return path, "fisher"
            path.append(fail("No exact test for tables larger than 2 × 2 here: combine categories or collect more data"))
            return path, None
        path.append(fail("Expected counts cannot be computed (a row or column total is zero)"))
        return path, None

    k = prep.k
    path.append(ok("Groups: %s", k))
    if k < 2:
        path.append(fail("At least 2 groups are needed to compare"))
        return path, None
    if min(len(g) for g in prep.groups) < th["min_n_per_group"]:
        path.append(fail("Each group needs n ≥ %s", th["min_n_per_group"]))
        return path, None
    paired = prep.design == "paired"
    if paired:
        path.append(ok("Paired (repeated) measurements"))
        if prep.paired_length_mismatch:
            path.append(fail("Paired groups must have the same length (%s)", ", ".join(str(n) for n in prep.raw_n)))
            return path, None
    else:
        path.append(ok("Independent groups") if prep.design_specified else note("Design not specified: treated as independent groups"))
    path.append(ok("Scale: %s", prep.scale))

    norm = checks["normality"]
    parametric = prep.scale == "continuous" and norm["status"] == "met"
    if prep.scale == "ordinal":
        path.append(ok("Ordinal data: rank-based test"))
    elif norm["status"] == "met":
        path.append(ok("Normality not rejected (Shapiro–Wilk, %s)", norm["basis"]))
    elif norm["status"] == "violated":
        path.append(fail("Normality rejected (Shapiro–Wilk) in %s", ", ".join(norm["rejected_in"])))
    else:
        path.append(fail("Normality cannot be assessed: rank-based test"))

    var = checks["equal_variance"]
    bf = var.get("brown_forsythe") or {}
    if paired:
        if k == 2:
            if not parametric and len(prep.groups[0]) and (prep.groups[0] == prep.groups[1]).all():
                path.append(fail("All paired differences are zero"))
                return path, None
            return path, "ttest_rel" if parametric else "wilcoxon"
        return path, "anova_rm" if parametric else "friedman"

    if var["status"] == "met":
        path.append(ok("Equal variances not rejected (Brown–Forsythe p %s)", bf["p_apa"]))
    elif var["status"] == "violated":
        path.append(fail("Variances differ (Brown–Forsythe p %s)", bf["p_apa"]))
    if k == 2:
        if parametric:
            if assume_equal_variance and var["status"] == "met":
                path.append(ok("Equal variances declared in advance (documented reason)"))
                return path, "ttest_ind"
            path.append(ok("Default: Welch's t-test (no documented reason to assume equal variances)"))
            return path, "ttest_welch"
        if var["status"] == "violated" and min(len(g) for g in prep.groups) >= th["brunner_munzel_min_n"]:
            return path, "brunner_munzel"
        return path, "mannwhitneyu"
    if parametric:
        return path, "anova" if var["status"] == "met" else "welch_anova"
    return path, "kruskal"


def recommend_test(
    data: Any,
    design: Optional[str] = None,
    *,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    assume_equal_variance: bool = False,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recommend ONE primary test, with a plain-language reason and decision path.

    Parameters are those of :func:`check_applicability`, plus
    ``assume_equal_variance`` — the documented reason that switches two
    independent normal groups from Welch's to Student's t-test (only when the
    data do not reject equal variances).

    Returns
    -------
    dict
        ``primary`` ({test_id, label, reason, reason_item}) or None;
        ``summary`` (e.g. "2 independent groups → ... → Welch's t-test");
        ``decision_path`` (translatable items); ``alternatives`` (other
        applicable tests, each with ``why_secondary``); ``applicability``
        (every test, ✓/✗ with reasons); ``checks``; ``thresholds``;
        ``data``; ``notes``; ``rules`` (the decision table).

    Examples
    --------
    >>> rec = recommend_test([[5.1, 4.9, 5.6, 5.8, 6.0], [6.3, 6.8, 6.1, 7.0, 6.6]], design="independent")
    >>> rec["primary"]["test_id"]
    'ttest_welch'
    """
    report = assess(data, design, scale=scale, group_names=group_names, thresholds_override=thresholds)
    prep: Prepared = report.pop("_prep")
    path, primary_id = _path_and_primary(prep, report["checks"], report["thresholds"], assume_equal_variance)
    rows = {r["test_id"]: r for r in report["tests"]}

    if primary_id == "brunner_munzel" and not rows[primary_id]["applicable"]:
        path.append(note("Brunner–Munzel is undefined for these data (the groups do not overlap): Mann–Whitney U instead"))
        primary_id = "mannwhitneyu"
    if primary_id is not None and not rows[primary_id]["applicable"]:
        # The decision tree and the applicability table must never disagree.
        path.append(fail("Internal check: %s is not applicable", SPECS[primary_id].label))
        primary_id = None

    primary = None
    if primary_id is not None:
        reason = note(_REASON[primary_id])
        primary = {"test_id": primary_id, "label": SPECS[primary_id].label, "reason": reason["text"], "reason_item": reason}
        path.append(ok("Primary test: %s", SPECS[primary_id].label))

    alternatives = []
    for row in report["tests"]:
        if not row["applicable"] or row["test_id"] == primary_id:
            continue
        why = _SECONDARY.get((primary_id, row["test_id"]), "Applicable, but not the pre-specified choice for this design.")
        alternatives.append({"test_id": row["test_id"], "label": row["label"], "why_secondary": why, "why_item": note(why)})

    summary = " → ".join(i["text"] for i in path)
    return {
        "primary": primary,
        "summary": summary,
        "decision_path": path,
        "alternatives": alternatives,
        "applicability": report["tests"],
        "checks": report["checks"],
        "thresholds": report["thresholds"],
        "data": report["data"],
        "notes": report["notes"],
        "rules": DECISION_RULES,
    }


# EOF
