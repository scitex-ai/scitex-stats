#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_result.py
"""Thin adapter from a raw test dict to the unified result shape.

The ``TestResult`` dataclass is not on develop yet; this returns the same
fields as a plain dict so callers switch by replacing this one function.
"""

from __future__ import annotations

from typing import Any, Dict

from ._messages import fmt_p


def _num(value: Any):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def as_result(raw: Dict[str, Any], spec, role: str, alpha: float) -> Dict[str, Any]:
    p = _num(raw.get("pvalue", raw.get("p_value")))
    df = raw.get("df")
    if df is None and raw.get("df_effect") is not None:
        df = [raw.get("df_effect"), raw.get("df_error")]
    if df is None and raw.get("df_between") is not None:
        df = [raw.get("df_between"), raw.get("df_within")]
    apa = raw.get("apa") if isinstance(raw.get("apa"), dict) else {}
    return {
        "test_id": spec.test_id,
        "label": spec.label,
        "role": role,
        "test_method": raw.get("test_method") or spec.label,
        "stat_symbol": raw.get("stat_symbol") or spec.symbol,
        "statistic": _num(raw.get("statistic")),
        "df": df,
        "pvalue": p,
        "p_apa": fmt_p(p) if p is not None else None,
        "significant": bool(p < alpha) if p is not None else None,
        "effect_size": _num(raw.get("effect_size")),
        "effect_size_metric": raw.get("effect_size_metric"),
        "apa_plain": apa.get("plain"),
        "apa_segments": apa.get("segments"),
        "error": raw.get("error"),
        "provenance": raw.get("provenance"),
    }


# EOF
