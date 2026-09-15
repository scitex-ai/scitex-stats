#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_report.py
"""The explicit assumption-check section: every check per sample, its statistic,
p-value, threshold and decision, plus the neutral diagnostic note and Q-Q data.

Shared by the Stats app's one-glance summary and any report renderer (PDF).
"""

from __future__ import annotations

from typing import Any, Dict, List

from ._messages import fmt_p, note

DIAGNOSTIC_NOTE = note(
    "Assumption tests are diagnostic, not confirmatory: they are not corrected for "
    "multiplicity, have low power in small samples and flag trivial departures in large "
    "ones. Check the Q-Q plots and spreads visually as well."
)

WELCH_DEFAULT_NOTE = note(
    "Welch's correction is used by default whether or not the equal-variance test is "
    "significant; that test is reported, not used to switch tests. The classic equal-variance "
    "test is chosen only with a reason documented in advance."
)


def _decision(flag: Any) -> str:
    return "not assessable" if flag is None else ("not rejected" if flag else "rejected")


def _normality_rows(norm: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for s in norm.get("samples", []):
        rows.append({
            "check": "Shapiro–Wilk", "assumption": "normality", "sample": s["sample"], "n": s["n"],
            "symbol": "W", "statistic": s["W"], "df": None, "p": s["p"],
            "p_apa": fmt_p(s["p"]) if s["p"] is not None else None,
            "threshold": note("p ≥ %s: normality not rejected", norm["alpha"]),
            "decision": _decision(s["normal"]),
        })
    return rows


def _variance_rows(var: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for key, name, used in (("brown_forsythe", "Brown–Forsythe", True), ("levene", "Levene", False)):
        entry = var.get(key)
        if not entry:
            continue
        rows.append({
            "check": name, "assumption": "equal variance", "sample": "all groups", "n": None,
            "symbol": "F", "statistic": entry["statistic"], "df": entry["df"], "p": entry["p"], "p_apa": entry["p_apa"],
            "threshold": note("p ≥ %s: equal variances not rejected", var["alpha"]) if used else note("Reported only (mean-centred; less robust to non-normality)"),
            "decision": _decision(entry["p"] >= var["alpha"]) if used else "reported",
        })
    if var.get("variance_ratio") is not None:
        rows.append({
            "check": "Largest / smallest variance", "assumption": "equal variance", "sample": "all groups", "n": None,
            "symbol": None, "statistic": var["variance_ratio"], "df": None, "p": None, "p_apa": None,
            "threshold": note("Descriptive; no significance test"), "decision": "reported",
        })
    return rows


def _count_rows(ec: Dict[str, Any]) -> List[Dict[str, Any]]:
    if ec.get("status") not in ("met", "violated"):
        return []
    return [{
        "check": "Minimum expected count", "assumption": "expected counts", "sample": "all cells", "n": None,
        "symbol": None, "statistic": ec["min_expected"], "df": None, "p": None, "p_apa": None,
        "threshold": note("≥ %s in every cell (%s of %s cells below)", ec["threshold"], ec["cells_below"], ec["cells"]),
        "decision": "met" if ec["status"] == "met" else "not met",
    }]


def assumption_section(checks: Dict[str, Any], welch_default: bool) -> Dict[str, Any]:
    """Rows for every check that ran, the notes, and Q-Q coordinates per sample."""
    rows = _normality_rows(checks["normality"]) + _variance_rows(checks["equal_variance"]) + _count_rows(checks["expected_counts"])
    notes = [DIAGNOSTIC_NOTE] + ([WELCH_DEFAULT_NOTE] if welch_default else [])
    qq = [
        {"sample": s["sample"], **s["qq"]}
        for s in checks["normality"].get("samples", []) if s.get("qq")
    ]
    return {"rows": rows, "notes": notes, "qq": qq, "normality_basis": checks["normality"].get("basis")}


# EOF
