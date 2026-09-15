#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/_segments.py
"""Typed text segments and their plain / HTML / LaTeX renderings.

Kinds: ``text`` (upright), ``sym`` (italic Latin symbol, APA 7 §6.44),
``greek`` (upright Greek symbol), ``sub`` / ``sup`` (upright sub/superscript).
"""

from __future__ import annotations

import html
from typing import Dict, List

MINUS = "−"

Segment = Dict[str, str]

GREEK = set("αβγδεζηθικλμνξοπρστυφχψω")

_SUP = str.maketrans("0123456789+-−", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻")
_SUB_CHARS = dict(zip("0123456789+-aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ"))


def seg(text: str, kind: str = "text") -> Segment:
    return {"text": text, "kind": kind}


def T(text: str) -> Segment:
    return seg(text, "text")


def S(text: str) -> Segment:
    return seg(text, "sym")


def parse_symbol(symbol: str) -> List[Segment]:
    """``"r_s"`` -> r + sub s; ``"χ²_F"`` -> χ + sup 2 + sub F; ``"W+"`` -> W + sub +."""
    s = str(symbol or "").strip()
    if not s:
        return [T("statistic")]
    sub = ""
    if "_" in s:
        s, sub = s.split("_", 1)
    elif len(s) > 1 and s.endswith(("+", "-")) and s[:-1].isalpha():
        s, sub = s[:-1], s[-1]
    sup = ""
    if s.endswith("²"):
        s, sup = s[:-1], "2"
    out = [seg(s, "greek" if s and all(c in GREEK for c in s) else "sym")]
    if sup:
        out.append(seg(sup, "sup"))
    if sub:
        out.append(seg(sub, "sub"))
    return out


def plain(segments: List[Segment]) -> str:
    """Unicode plain text: no italics (pastes cleanly), real sub/superscripts."""
    out = []
    for s in segments:
        text, kind = s["text"], s["kind"]
        if kind == "sup":
            out.append(text.translate(_SUP))
        elif kind == "sub":
            if all(c in _SUB_CHARS for c in text):
                out.append("".join(_SUB_CHARS[c] for c in text))
            else:
                out.append("_" + text)
        else:
            out.append(text)
    return "".join(out)


_TAGS = {
    "sym": ('<i class="stx-sym">', "</i>"),
    "greek": ('<span class="stx-sym stx-sym--greek">', "</span>"),
    "sub": ("<sub>", "</sub>"),
    "sup": ("<sup>", "</sup>"),
}


def to_html(segments: List[Segment]) -> str:
    """Escaped HTML; Latin symbols ``<i>``, Greek upright, sub/sup tags."""
    out = []
    for s in segments:
        start, end = _TAGS.get(s["kind"], ("", ""))
        out.append(start + html.escape(s["text"]) + end)
    return "".join(out)


_GREEK_TEX = {
    "ρ": r"\rho", "τ": r"\tau", "χ": r"\chi", "η": r"\eta", "ε": r"\varepsilon",
    "ω": r"\omega", "μ": r"\mu", "α": r"\alpha", "δ": r"\delta",
}
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


def rendered(segments: List[Segment]) -> Dict[str, object]:
    return {"segments": segments, "plain": plain(segments), "html": to_html(segments)}


__all__ = ["MINUS", "GREEK", "Segment", "seg", "T", "S", "parse_symbol", "plain", "to_html", "to_latex", "rendered"]

# EOF
