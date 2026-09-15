#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_run_all.py
"""Run every applicable test: the primary first, the rest as sensitivity analyses.

Results keep a fixed order (primary, then catalogue order) and are never
ranked or selected by p-value.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

import numpy as np

from ._applicability import CATALOG, SPECS, welch_anova
from ._data import prepare
from ._decide import recommend_test
from ._messages import P_HACKING_WARNING, note
from ._result import as_result


def _run_one(test_id: str, groups: List[np.ndarray], table: Optional[np.ndarray], alternative: str) -> Dict[str, Any]:
    from scitex_stats import run_test

    if test_id == "welch_anova":
        return welch_anova(groups)
    if test_id == "anova_rm":
        import pandas as pd

        from scitex_stats.tests import test_anova_rm

        return test_anova_rm(pd.DataFrame(np.column_stack(groups)), decimals=12)
    if test_id in ("chi2", "fisher"):
        return run_test(test_id, groups=table.tolist())
    if test_id in ("anova", "kruskal", "friedman"):
        return run_test(test_id, groups=[g.tolist() for g in groups])
    return run_test(test_id, data=groups[0].tolist(), data2=groups[1].tolist(), alternative=alternative)


def run_all_applicable(
    data: Any,
    design: Optional[str] = None,
    *,
    scale: Optional[str] = None,
    group_names: Optional[List[str]] = None,
    primary: Optional[str] = None,
    alternative: str = "two-sided",
    assume_equal_variance: bool = False,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run every applicable test in sequence, labelled primary vs sensitivity.

    The primary test is fixed BEFORE any test runs: ``primary`` if the caller
    pre-registered one (it must be applicable), otherwise
    :func:`recommend_test`'s choice. Every other applicable test is labelled
    ``"sensitivity"``. Nothing here looks at p-values to choose, rank or
    reorder tests; the output carries an explicit p-hacking warning.

    Returns
    -------
    dict
        ``primary_test``, ``primary_source`` ("pre-registered" or
        "recommend_test"), ``warning`` (text) + ``warning_item``,
        ``results`` (primary first, then catalogue order; each with
        ``role``), ``agreement`` ({status: agree|disagree|single|none,
        significant, not_significant, alpha, summary}) and the
        ``recommendation`` it was based on.
    """
    rec = recommend_test(
        data, design, scale=scale, group_names=group_names,
        assume_equal_variance=assume_equal_variance, thresholds=thresholds,
    )
    applicable = [r["test_id"] for r in rec["applicability"] if r["applicable"]]
    if primary is not None:
        if primary not in SPECS:
            raise ValueError(f"unknown primary test {primary!r}; choose from {sorted(SPECS)}")
        if primary not in applicable:
            raise ValueError(f"pre-registered primary test {primary!r} is not applicable to these data")
        primary_id, source = primary, "pre-registered"
    else:
        primary_id = rec["primary"]["test_id"] if rec["primary"] else None
        source = "recommend_test"

    prep = prepare(data, design=design, scale=scale, group_names=group_names)
    alpha = rec["thresholds"]["alpha"]
    order = ([primary_id] if primary_id else []) + [s.test_id for s in CATALOG if s.test_id in applicable and s.test_id != primary_id]

    results = []
    for test_id in order:
        role = "primary" if test_id == primary_id else "sensitivity"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = _run_one(test_id, prep.groups, prep.table, alternative)
            results.append(as_result(raw, SPECS[test_id], role, alpha))
        except Exception as exc:  # noqa: BLE001 - one failing test must not hide the others
            results.append(as_result({"error": f"{type(exc).__name__}: {exc}"}, SPECS[test_id], role, alpha))

    return {
        "primary_test": primary_id,
        "primary_source": source,
        "warning": P_HACKING_WARNING["text"],
        "warning_item": P_HACKING_WARNING,
        "ordering": "primary first, then catalogue order; never ranked by p-value",
        "alternative": alternative,
        "results": results,
        "agreement": agreement(results, alpha),
        "recommendation": rec,
    }


def agreement(results: List[Dict[str, Any]], alpha: float) -> Dict[str, Any]:
    ran = [r for r in results if r.get("pvalue") is not None]
    sig = [r["test_id"] for r in ran if r["significant"]]
    nonsig = [r["test_id"] for r in ran if not r["significant"]]
    no_p = [r["test_id"] for r in results if r.get("pvalue") is None]
    out = _agreement_status(ran, sig, nonsig, alpha)
    out["no_p_value"] = no_p
    return out


def _agreement_status(ran, sig, nonsig, alpha) -> Dict[str, Any]:
    if not ran:
        status, item = "none", note("No test produced a p-value.")
    elif len(ran) == 1:
        status, item = "single", note("Only one applicable test; there is nothing to compare.")
    elif sig and nonsig:
        status = "disagree"
        item = note(
            "The tests disagree at α = %s (%s of %s significant). Report the primary test; the disagreement is itself a finding worth reporting.",
            alpha, len(sig), len(ran),
        )
    else:
        status = "agree"
        item = note(
            "All %s tests agree at α = %s (%s).", len(ran), alpha,
            "significant" if sig else "not significant",
        )
    return {"status": status, "alpha": alpha, "significant": sig, "not_significant": nonsig, "summary": item["text"], "summary_item": item}


# EOF
