#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa.py
"""APA-style rendering of a test result: one structure, three renderings.

``apa_render(result)`` returns the summary as typed segments plus plain,
HTML and LaTeX renderings of the same segments, so the Python API, the
CLI/MCP and the GUI agree on symbols and number formatting:

- Latin statistical symbols italic (*t*, *p*, *d*, *F*, *U*, *W*, *r*,
  *H*, *z*, *n*); Greek letters upright (ρ, τ, η², χ²).
- ``p < .001`` below .001; no leading zero for p and for statistics
  bounded by 1 (r, ρ, τ, η², ...).
- A real minus sign (U+2212) for negative values.

Segment kinds: ``text`` (upright), ``sym`` (italic Latin symbol),
``greek`` (upright symbol), ``sub`` / ``sup`` (sub/superscript).
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, Dict, List, Optional

MINUS = "−"

Segment = Dict[str, str]


def _seg(text: str, kind: str = "text") -> Segment:
    return {"text": text, "kind": kind}


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def format_number(value: Any, digits: int = 3, leading_zero: bool = True) -> str:
    """Format a number with a real minus sign; ``—`` when missing."""
    if not _is_num(value):
        return "—"
    s = f"{abs(float(value)):.{digits}f}"
    if not leading_zero and s.startswith("0."):
        s = s[1:]
    negative = float(value) < 0 and s.strip("0.") != ""
    return (MINUS if negative else "") + s


def format_p(p: Any) -> str:
    """APA p-value relation: ``< .001``, ``= .042`` or ``> .999``."""
    if not _is_num(p):
        return "= —"
    if p < 0.001:
        return "< .001"
    if p >= 0.9995:
        return "> .999"
    return "= " + format_number(p, 3, leading_zero=False)


# Symbols whose magnitude never exceeds 1 lose the leading zero (APA 6.36).
_BOUNDED = {"r", "ρ", "τ", "η", "ε", "ω", "V", "P"}


def _stat_symbol(result: Dict[str, Any]) -> List[Segment]:
    method = str(result.get("test_method") or result.get("test") or "").lower()
    symbol = result.get("stat_symbol")
    if "spearman" in method:
        return [_seg("ρ", "greek")]
    if "tau" in method or "tau_squared" in result:
        return [_seg("τ", "greek")]
    if "friedman" in method or "n_conditions" in result or symbol in ("chi2", "χ²"):
        return [_seg("χ", "greek"), _seg("2", "sup")]
    if not symbol:
        return [_seg("stat")]
    return [_seg(str(symbol), "sym")]


_EFFECT_LABELS = [
    (re.compile(r"^cohen'?s d(.*)$", re.I), lambda m: [_seg("Cohen's "), _seg("d", "sym"), _seg(m.group(1))]),
    (re.compile(r"^hedges'? ?g(.*)$", re.I), lambda m: [_seg("Hedges' "), _seg("g", "sym"), _seg(m.group(1))]),
    (re.compile(r"^rank[- ]biserial( correlation)?$", re.I), lambda m: [_seg("r", "sym"), _seg("rb", "sub")]),
    (re.compile(r"^partial[ _-]eta[ _-]?squared$", re.I), lambda m: [_seg("η", "greek"), _seg("p", "sub"), _seg("2", "sup")]),
    (re.compile(r"^eta[ _-]?squared$", re.I), lambda m: [_seg("η", "greek"), _seg("2", "sup")]),
    (re.compile(r"^epsilon[ _-]?squared$", re.I), lambda m: [_seg("ε", "greek"), _seg("2", "sup")]),
    (re.compile(r"^omega[ _-]?squared$", re.I), lambda m: [_seg("ω", "greek"), _seg("2", "sup")]),
    (re.compile(r"^kendall'?s?[ _]w$", re.I), lambda m: [_seg("Kendall's "), _seg("W", "sym")]),
    (re.compile(r"^(kendall'?s?[ _])?tau(-b)?$", re.I), lambda m: [_seg("τ", "greek")]),
    (re.compile(r"^(spearman'?s? )?rho$", re.I), lambda m: [_seg("ρ", "greek")]),
    (re.compile(r"^(pearson )?r$", re.I), lambda m: [_seg("r", "sym")]),
    (re.compile(r"^cram[eé]r'?s v$", re.I), lambda m: [_seg("Cramér's "), _seg("V", "sym")]),
    (re.compile(r"^p\(x ?> ?y\)$", re.I), lambda m: [_seg("P", "sym"), _seg("("), _seg("X", "sym"), _seg(" > "), _seg("Y", "sym"), _seg(")")]),
]


def _effect_label(metric: Any) -> List[Segment]:
    text = str(metric or "").strip()
    for pattern, build in _EFFECT_LABELS:
        m = pattern.match(text)
        if m:
            return [s for s in build(m) if s["text"]]
    return [_seg(text)] if text else []


def _bounded(segments: List[Segment]) -> bool:
    symbols = {s["text"] for s in segments if s["kind"] != "text"}
    return bool(symbols & _BOUNDED) or plain(segments) == "Kendall's W"


def _df_text(result: Dict[str, Any]) -> str:
    between, within = result.get("df_between"), result.get("df_within")
    if _is_num(between) and _is_num(within):
        return f"({_int_or(between)}, {_int_or(within)})"
    if _is_num(result.get("df")):
        return f"({_int_or(result['df'])})"
    return ""


def _int_or(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else format_number(v, 2)


def plain(segments: List[Segment]) -> str:
    """Plain text (no Unicode italics, so it pastes cleanly into Word)."""
    sup = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    out = []
    for s in segments:
        if s["kind"] == "sup":
            out.append(s["text"].translate(sup))
        elif s["kind"] == "sub":
            out.append("_" + s["text"])
        else:
            out.append(s["text"])
    return "".join(out)


def to_html(segments: List[Segment]) -> str:
    """Escaped HTML; italic symbols as ``<i class="stx-sym">``."""
    tags = {
        "sym": ('<i class="stx-sym">', "</i>"),
        "greek": ('<span class="stx-sym stx-sym--greek">', "</span>"),
        "sub": ("<sub>", "</sub>"),
        "sup": ("<sup>", "</sup>"),
    }
    out = []
    for s in segments:
        start, end = tags.get(s["kind"], ("", ""))
        out.append(start + html.escape(s["text"]) + end)
    return "".join(out)


_GREEK_TEX = {"ρ": r"\rho", "τ": r"\tau", "χ": r"\chi", "η": r"\eta", "ε": r"\varepsilon", "ω": r"\omega", "μ": r"\mu"}
_TEX_ESCAPE = str.maketrans({c: "\\" + c for c in "&%$#_{}"})


def to_latex(segments: List[Segment]) -> str:
    """LaTeX: ``$t$``, ``$\\chi^{2}$``, ``$-$`` for the minus sign."""
    out = []
    for s in segments:
        text, kind = s["text"], s["kind"]
        if kind == "sym":
            out.append(f"${text}$")
        elif kind == "greek":
            out.append(f"${_GREEK_TEX.get(text, text)}$")
        elif kind in ("sub", "sup"):
            mark = "_" if kind == "sub" else "^"
            out.append(f"${mark}{{\\mathrm{{{text}}}}}$")
        else:
            text = text.translate(_TEX_ESCAPE).replace("<", "$<$").replace(">", "$>$")
            out.append(text.replace(MINUS, "$-$"))
    return "".join(out).replace("$$", "")


def apa_render(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """APA summary of a unified result dict, or ``None`` without a p-value.

    Returns ``{"segments", "plain", "html", "latex", "stat_symbol",
    "effect_size_label", "statistic", "p_value", "effect_size"}``; the
    three ``*_symbol``/``*_label`` entries are segment lists, the value
    entries are display strings (``p_value`` carries its relation,
    e.g. ``"< .001"``).
    """
    if not isinstance(result, dict):
        return None
    p = result.get("pvalue", result.get("p_value"))
    if "statistic" not in result and p is None:
        return None

    symbol = _stat_symbol(result)
    stat_str = format_number(result.get("statistic"), 3, leading_zero=not _bounded(symbol))
    p_str = format_p(p)

    segments: List[Segment] = [*symbol]
    df = _df_text(result)
    if df:
        segments.append(_seg(df))
    segments += [_seg(" = " + stat_str + ", "), _seg("p", "sym"), _seg(" " + p_str)]

    label = _effect_label(result.get("effect_size_metric"))
    effect = result.get("effect_size")
    effect_str = None
    if _is_num(effect) and label:
        effect_str = format_number(effect, 3, leading_zero=not _bounded(label))
        duplicate = plain(label) == plain(symbol) and effect_str == stat_str
        if not duplicate:
            segments += [_seg(", "), *label, _seg(" = " + effect_str)]

    stars = result.get("stars")
    if stars in ("*", "**", "***", "ns"):
        segments.append(_seg(", " + stars))

    return {
        "segments": segments,
        "plain": plain(segments),
        "html": to_html(segments),
        "latex": to_latex(segments),
        "stat_symbol": symbol,
        "effect_size_label": label,
        "statistic": stat_str,
        "p_value": p_str,
        "effect_size": effect_str,
    }


__all__ = ["MINUS", "apa_render", "format_number", "format_p", "plain", "to_html", "to_latex"]

# EOF
