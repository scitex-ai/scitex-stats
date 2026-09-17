#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_figure.py
"""Report figure through the plot module (``scitex_stats._plot``): spec -> deterministic SVG.

Brackets: the significant post-hoc pairs for 3+ groups, the primary test for 2.
FigRecipe draws when installed (``backend="auto"``); either way the SVG is
written with a fixed hash salt and no date, so the same data give the same bytes.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import numpy as np

_CJK_FAMILIES = ("Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "IPAGothic", "TakaoGothic")
_CJK_FILE_HINTS = ("notosanscjk", "notosansjp", "ipaexg", "ipag", "takaogothic")
_SVG_SALT = "scitex-stats-report"
WIDTH_MM = 120.0


def register_cjk_fonts() -> List[str]:
    """Make user-installed Japanese fonts visible to matplotlib; returns the CJK families it knows."""
    from matplotlib import font_manager

    known = {f.name for f in font_manager.fontManager.ttflist}
    if not known.intersection(_CJK_FAMILIES):
        # matplotlib's font cache can predate fonts installed later (e.g. ~/.fonts).
        for path in font_manager.findSystemFonts(fontext="ttf") + font_manager.findSystemFonts(fontext="otf"):
            if any(h in path.lower().replace("-", "").replace("_", "") for h in _CJK_FILE_HINTS):
                try:
                    font_manager.fontManager.addfont(path)
                except Exception:  # noqa: BLE001 - an unreadable font file is not fatal
                    continue
        known = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in _CJK_FAMILIES if f in known]


def plot_spec(result: Dict[str, Any], names: List[str], groups: List[np.ndarray],
              comparisons: Optional[List[Dict[str, Any]]] = None, y_label: str = "Value") -> Dict[str, Any]:
    from scitex_stats._plot import build_plot_spec

    posthoc = None
    if comparisons is not None:
        posthoc = [{"group_i": c["group_i"], "group_j": c["group_j"], "pvalue_adjusted": c["p_adjusted"]}
                   for c in comparisons if c.get("significant")]
    spec = build_plot_spec(result, groups=[g.tolist() for g in groups], group_names=names,
                           posthoc=posthoc, y_label=y_label, width_mm=WIDTH_MM, height_mm=WIDTH_MM * 0.62)
    if comparisons is not None and not posthoc:
        spec["annotations"]["brackets"] = []
    cjk = register_cjk_fonts()
    spec["style"]["font_family_cjk"] = list(dict.fromkeys(cjk + spec["style"].get("font_family_cjk", [])))
    spec["style"]["font_size_pt"] = 8
    return spec


def render_svg(spec: Dict[str, Any]) -> str:
    from matplotlib import rc_context

    from scitex_stats._plot import render_spec
    from scitex_stats._plot._mpl import rc_params

    try:
        drawn = render_spec(spec, backend="auto")
    except Exception:  # noqa: BLE001 - a FigRecipe failure falls back to plain matplotlib
        drawn = render_spec(spec, backend="matplotlib")
    fig = getattr(drawn.figure, "fig", drawn.figure)
    buf = io.StringIO()
    with rc_context({**rc_params(spec["style"]), "svg.hashsalt": _SVG_SALT, "svg.fonttype": "path"}):
        fig.savefig(buf, format="svg", facecolor="white", metadata={"Date": None, "Creator": None})
    drawn.close()
    return buf.getvalue()


__all__ = ["WIDTH_MM", "plot_spec", "register_cjk_fonts", "render_svg"]

# EOF
