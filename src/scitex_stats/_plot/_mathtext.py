#!/usr/bin/env python3
# File: scitex_stats/_plot/_mathtext.py
"""APA segments -> matplotlib mathtext (italic Latin symbols, upright Greek)."""

from __future__ import annotations

from typing import Dict, List

def _escape(text: str) -> str:
    return text.replace("$", r"\$")


def segments_to_mathtext(segments: List[Dict[str, str]]) -> str:
    """``[sym t, text (14) = 2.1]`` -> ``$\\mathit{t}$(14) = 2.1``.

    Sub/superscripts attach to the preceding math group so ``d_z`` and ``χ²``
    render as one symbol.
    """
    out: List[str] = []
    for seg in segments:
        text, kind = str(seg.get("text", "")), seg.get("kind", "text")
        if kind == "sym":
            body = r"\mathit{%s}" % text.replace(" ", r"\ ")
        elif kind == "greek":
            # Unicode, not \eta: upright per APA, and survives recipe round-trips.
            out.append(_escape(text))
            continue
        elif kind == "sup" and text == "2" and out and not out[-1].endswith("$"):
            out.append("²")
            continue
        elif kind == "sub":
            body = r"_{\mathrm{%s}}" % text
        elif kind == "sup":
            body = r"^{\mathrm{%s}}" % text
        else:
            out.append(_escape(text))
            continue
        if kind in ("sub", "sup") and out and out[-1].endswith("$"):
            out[-1] = out[-1][:-1] + body + "$"
        else:
            out.append(f"${body}$")
    return "".join(out)


def p_mathtext(p_apa: str) -> str:
    """``"< .001"`` -> ``$\\mathit{p}$ < .001``."""
    return r"$\mathit{p}$ " + _escape(p_apa)


def n_mathtext(n: int) -> str:
    return r"$\mathit{n}$ = %d" % int(n)


__all__ = ["segments_to_mathtext", "p_mathtext", "n_mathtext"]

# EOF
