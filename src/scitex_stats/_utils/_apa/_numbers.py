#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/_numbers.py
"""APA 7 number formatting (§6.36 decimals and leading zeros, §6.43 p and CI)."""

from __future__ import annotations

import math
from typing import Any, Optional

from ._segments import MINUS

STAT_DECIMALS = 2
P_DECIMALS = 3
MISSING = "—"


def is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def format_number(value: Any, digits: int = STAT_DECIMALS, leading_zero: bool = True) -> str:
    """Round to ``digits``; real minus sign; ``.45`` when ``leading_zero`` is False."""
    if not is_num(value):
        return MISSING
    s = f"{abs(float(value)):.{digits}f}"
    if not leading_zero and s.startswith("0."):
        s = s[1:]
    negative = float(value) < 0 and s.strip("0.") != ""
    return (MINUS if negative else "") + s


def format_p(p: Any) -> str:
    """Relation plus value: ``< .001``, ``= .042``, ``> .999`` (never ``= .000``)."""
    if not is_num(p):
        return "= " + MISSING
    if p < 0.001:
        return "< .001"
    if p >= 0.9995:
        return "> .999"
    return "= " + format_number(p, P_DECIMALS, leading_zero=False)


def format_p_exact(p: Any) -> str:
    """Exact p for tables: three significant digits, no leading zero; ``1.79 × 10⁻⁵`` below .001."""
    if not is_num(p):
        return MISSING
    if p == 0:
        return "0"
    if p < 0.001:
        mant, exp = f"{p:.2e}".split("e")
        sup = str(int(exp)).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
        return f"{mant} × 10{sup}"
    if p >= 1:
        return "1"
    return f"{p:.3g}"[1:]


def format_df(df: Any) -> Optional[str]:
    """Integer df as integers; fractional (Welch, Brunner–Munzel) to two decimals."""
    if not is_num(df):
        return None
    return str(int(df)) if float(df).is_integer() else format_number(df, STAT_DECIMALS)


def format_ci(lo: Any, hi: Any, level: Any = 0.95, leading_zero: bool = True) -> Optional[str]:
    """``95% CI [−4.12, −2.24]`` (APA 7 §6.43)."""
    if not (is_num(lo) and is_num(hi)):
        return None
    pct = round(float(level) * 100) if is_num(level) else 95
    lo_s = format_number(lo, STAT_DECIMALS, leading_zero)
    hi_s = format_number(hi, STAT_DECIMALS, leading_zero)
    return f"{pct}% CI [{lo_s}, {hi_s}]"


__all__ = [
    "STAT_DECIMALS", "P_DECIMALS", "MISSING", "is_num", "format_number",
    "format_p", "format_p_exact", "format_df", "format_ci",
]

# EOF
