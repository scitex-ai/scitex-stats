#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/_messages.py
"""Translatable reason messages.

Each message keeps its English ``msg`` template (a gettext msgid with ``%s``
placeholders) and its ``args`` so the Stats app can translate it; ``text`` is
the rendered English for Python/CLI/MCP callers.
"""

from __future__ import annotations

from typing import Any, Dict


def _msg(status: str, msg: str, *args: Any) -> Dict[str, Any]:
    clean = [a if isinstance(a, (int, float, str)) else str(a) for a in args]
    return {"status": status, "msg": msg, "args": clean, "text": msg % tuple(clean) if clean else msg}


def ok(msg: str, *args: Any) -> Dict[str, Any]:
    return _msg("ok", msg, *args)


def fail(msg: str, *args: Any) -> Dict[str, Any]:
    return _msg("fail", msg, *args)


def note(msg: str, *args: Any) -> Dict[str, Any]:
    return _msg("note", msg, *args)


def fmt_p(p: Any) -> str:
    """APA p without the symbol: '= .043', '< .001'."""
    from scitex_stats._utils._apa import format_p

    return format_p(p) if p is not None else "n/a"


def fmt_alpha(alpha: Any) -> str:
    """APA α / p threshold: '.05' (no leading zero; a third decimal only when needed)."""
    from scitex_stats._utils._apa import format_number

    digits = 2 if round(float(alpha), 2) == float(alpha) else 3
    return format_number(alpha, digits, leading_zero=False)


def fmt_stat(value: Any, symbol: Any) -> str:
    """APA statistic: two decimals; no leading zero when the symbol is bounded by 1 (W, r, …)."""
    from scitex_stats._utils._apa import format_number
    from scitex_stats._utils._apa._rules import is_bounded

    return format_number(value, 2, leading_zero=not is_bounded(symbol))


P_HACKING_WARNING = note(
    "Sensitivity analyses only. The primary test was fixed before any p-value was seen. "
    "Choosing a test after seeing several p-values (for example, the smallest) inflates "
    "the false-positive rate; this is p-hacking. Report the primary test as the result "
    "and the others as sensitivity analyses."
)


# EOF
