#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_analysis.py
"""Adapter from the recommender (``scitex_stats._recommend``) to the report.

Applicability, the primary test and the sensitivity runs all come from
:func:`run_all_applicable`, so the report and the Stats app never disagree.
Only the full result of the primary test is re-run here, to get its APA table.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List

from ._inputs import Prepared


def _design(prep: Prepared) -> str:
    return "paired" if prep.design == "within" else "independent"


def _assumption_rows(checks: Dict[str, Any], th: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    norm = checks["normality"]
    for s in norm.get("samples", []):
        rows.append({"check": "normality", "test": th["normality_test"], "target": s["sample"], "symbol": "W",
                     "statistic": s["W"], "pvalue": s["p"], "ok": s["normal"], "alpha": th["normality_alpha"],
                     "note": "; ".join(c["text"].split(": ", 1)[-1] for c in s["caveats"]) or None})
    var = checks["equal_variance"]
    for key, name in (("brown_forsythe", "Brown–Forsythe"), ("levene", "Levene (mean-centred)")):
        entry = var.get(key)
        if entry:
            rows.append({"check": "variance", "test": name, "target": "all groups", "symbol": "F",
                         "statistic": entry["statistic"], "pvalue": entry["p"],
                         "ok": entry["p"] >= th["variance_alpha"] if key == "brown_forsythe" else None,
                         "alpha": th["variance_alpha"], "note": None if key == "brown_forsythe" else "reported only; the decision uses Brown–Forsythe"})
    return rows


_F_TESTS = ("welch_anova", "anova_rm")


def _f_apa(raw: Dict[str, Any]) -> Dict[str, Any]:
    """APA rendering for F tests without their own rule yet, in the F(df1, df2) layout APA prescribes."""
    from scitex_stats._utils._apa import apa_render

    df = raw.get("df") if isinstance(raw.get("df"), list) else [raw.get("df_effect"), raw.get("df_error")]
    return apa_render({"test_method": "one-way anova", "statistic": raw.get("statistic"), "pvalue": raw.get("pvalue"),
                       "df_between": df[0], "df_within": df[1], "effect_size": raw.get("effect_size"),
                       "effect_size_metric": raw.get("effect_size_metric")}) or {}


def _full_primary(test_id: str, prep: Prepared) -> Dict[str, Any]:
    """The primary test's complete result dict (with ``apa`` table where renderable)."""
    from scitex_stats import run_test
    from scitex_stats._recommend._run_all import _run_one
    from scitex_stats._utils._serialize import to_json_safe

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if test_id in _F_TESTS:
            raw = to_json_safe(_run_one(test_id, prep.groups, None, "two-sided"))
            raw["apa"] = _f_apa(raw)
            return raw
        if test_id in ("anova", "kruskal", "friedman"):
            return run_test(test_id, groups=[g.tolist() for g in prep.groups], group_names=prep.names)
        return run_test(test_id, data=prep.groups[0].tolist(), data2=prep.groups[1].tolist(), group_names=prep.names)


def analyse(prep: Prepared, alpha: float) -> Dict[str, Any]:
    from scitex_stats._recommend import run_all_applicable

    data = {n: g.tolist() for n, g in zip(prep.names, prep.groups)}
    th = {"alpha": alpha, "normality_alpha": alpha, "variance_alpha": alpha}
    out = run_all_applicable(data, _design(prep), scale="continuous", thresholds=th)
    rec = out["recommendation"]
    if not out["primary_test"]:
        raise ValueError("No test applies to these data: " + rec["summary"])
    th = rec["thresholds"]
    primary_id = out["primary_test"]
    results = out["results"]
    primary_res = results[0]
    for r in results:
        if r["test_id"] in _F_TESTS and not r.get("apa_segments") and r.get("pvalue") is not None:
            r["apa_segments"] = _f_apa(r).get("segments")
    others = [{"test": r["test_id"], "label": r["label"], "result": r} for r in results[1:]]
    primary_sig = primary_res.get("significant")
    ran = [o for o in others if o["result"].get("pvalue") is not None]
    agree = [o for o in ran if o["result"]["significant"] == primary_sig]
    relevant = {s.test_id for s in _catalog() if _fits(s, prep)}
    return {
        "thresholds": th,
        "checks": rec["checks"],
        "assumption_rows": _assumption_rows(rec["checks"], th),
        "normal": rec["checks"]["normality"]["status"] == "met",
        "equal_variances": {"met": True, "violated": False}.get(rec["checks"]["equal_variance"]["status"]),
        "applicability": [{"test": r["test_id"], "label": r["label"], "applicable": r["applicable"], "reasons": r["reasons"]}
                          for r in rec["applicability"] if r["test_id"] in relevant],
        "primary": {"test": primary_id, "label": rec["primary"]["label"], "rationale": rec["primary"]["reason"],
                    "path": rec["summary"]},
        "primary_result": _full_primary(primary_id, prep),
        "primary_summary": primary_res,
        "sensitivity": others,
        "agreement": {"primary_significant": bool(primary_sig), "n_agree": len(agree), "n_total": len(ran),
                      "all_agree": len(agree) == len(ran), "status": out["agreement"]["status"],
                      "summary": out["agreement"]["summary"]},
        "warning": out["warning"],
        "notes": [n["text"] for n in rec.get("notes", [])],
    }


def _catalog():
    from scitex_stats._recommend import CATALOG

    return CATALOG


def _fits(spec, prep: Prepared) -> bool:
    """Tests of this design and group count; the table lists those, not the whole catalogue."""
    if spec.table or spec.design != _design(prep):
        return False
    k = len(prep.groups)
    return spec.min_groups <= k and (spec.max_groups is None or k <= spec.max_groups)


__all__ = ["analyse"]

# EOF
