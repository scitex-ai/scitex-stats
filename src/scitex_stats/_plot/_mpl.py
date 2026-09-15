#!/usr/bin/env python3
# File: scitex_stats/_plot/_mpl.py
"""Plain-matplotlib renderer for a plot spec (the no-FigRecipe fallback)."""

from __future__ import annotations

import io
from typing import Any, Dict, List, Tuple

MM = 1 / 25.4


def _fonts(style: Dict[str, Any]) -> List[str]:
    """Preferred Latin faces that exist, then a CJK face for Japanese labels."""
    from matplotlib import font_manager

    have = {f.name for f in font_manager.fontManager.ttflist}
    latin = [f for f in style.get("font_family", []) if f in have] or ["DejaVu Sans"]
    cjk = [f for f in style.get("font_family_cjk", []) if f in have]
    return latin[:1] + cjk[:1] + (["DejaVu Sans"] if "DejaVu Sans" not in latin[:1] else [])


def rc_params(style: Dict[str, Any]) -> Dict[str, Any]:
    size = float(style.get("font_size_pt", 7))
    lw = float(style.get("line_width_pt", 0.6))
    return {
        "font.family": "sans-serif",
        "font.sans-serif": _fonts(style),
        "font.size": size, "axes.labelsize": size, "axes.titlesize": size,
        "xtick.labelsize": size, "ytick.labelsize": size, "legend.fontsize": size,
        "mathtext.fontset": "custom", "mathtext.it": "sans:italic", "mathtext.rm": "sans",
        "mathtext.cal": "sans", "mathtext.bf": "sans:bold", "mathtext.sf": "sans",
        "axes.linewidth": lw, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.major.width": lw, "ytick.major.width": lw,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "lines.linewidth": lw * 1.4, "savefig.dpi": style.get("dpi", 300),
        "svg.fonttype": "path", "pdf.fonttype": 42, "ps.fonttype": 42,
        "axes.unicode_minus": True, "figure.facecolor": "white",
    }


def _light(color: str, amount: float = 0.72) -> Tuple[float, float, float]:
    from matplotlib.colors import to_rgb

    r, g, b = to_rgb(color)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def bracket_geometry(spec: Dict[str, Any]) -> Tuple[float, float, float]:
    """(base y, step, tick height) shared by both renderers so brackets stack alike."""
    ys = [v for g in spec.get("groups", []) for v in g["values"]]
    lo, hi = (min(ys), max(ys)) if ys else (0.0, 1.0)
    span = (hi - lo) or 1.0
    return hi + 0.08 * span, 0.11 * span, 0.025 * span


def _draw_groups(ax, spec: Dict[str, Any]) -> None:
    style = spec["style"]
    palette = style["palette"]
    lw = float(style.get("line_width_pt", 0.6))
    groups = spec["groups"]
    types = {layer["type"]: layer for layer in spec["layers"]}
    center = types.get("center", {}).get("estimator", "mean_ci")
    for g in groups:
        x, color = g["position"], palette[g["position"] % len(palette)]
        s = g["summary"]
        if "box" in types and s.get("n"):
            ax.bxp([{"med": s["median"], "q1": s["q1"], "q3": s["q3"], "whislo": s["whisker_low"],
                     "whishi": s["whisker_high"], "fliers": []}],
                   positions=[x], widths=0.5, showfliers=False, patch_artist=True,
                   boxprops={"facecolor": _light(color), "edgecolor": color, "linewidth": lw},
                   whiskerprops={"color": color, "linewidth": lw}, capprops={"color": color, "linewidth": lw},
                   medianprops={"color": color, "linewidth": lw * 2 if center == "median_iqr" else lw})
    if "paired_lines" in types and len(groups) >= 2:
        for k in range(min(len(g["values"]) for g in groups)):
            ax.plot([g["position"] + g["jitter"][k] for g in groups], [g["values"][k] for g in groups],
                    color="0.6", linewidth=lw * 0.8, alpha=0.7, zorder=2)
    if "points" in types:
        for g in groups:
            color = palette[g["position"] % len(palette)]
            ax.scatter([g["position"] + j for j in g["jitter"]], g["values"], s=9, color=color,
                       edgecolors="white", linewidths=0.3, alpha=0.9, zorder=3)
    if center == "mean_ci":
        for g in groups:
            s = g["summary"]
            if s.get("ci_lower") is None:
                continue
            ax.errorbar([g["position"] + 0.33], [s["mean"]],
                        yerr=[[s["mean"] - s["ci_lower"]], [s["ci_upper"] - s["mean"]]],
                        fmt="o", color="black", markersize=3, capsize=1.8, elinewidth=lw, capthick=lw, zorder=4)
    for layer in spec["layers"]:
        if layer["type"] == "reference_line":
            ax.axhline(layer["value"], color="0.4", linestyle=(0, (3, 2)), linewidth=lw)
    base, step, tick = bracket_geometry(spec)
    top = base
    for b in spec["annotations"]["brackets"]:
        y = base + b["tier"] * step
        x1, x2 = groups[b["group1"]]["position"], groups[b["group2"]]["position"]
        ax.plot([x1, x1, x2, x2], [y - tick, y, y, y - tick], color="black", linewidth=lw, clip_on=False)
        ax.text((x1 + x2) / 2, y + tick * 0.4, b["text"], ha="center", va="bottom")
        top = max(top, y + step * 0.75)
    ax.set_xticks([g["position"] for g in groups])
    labels = [g["name"] + ("\n" + g["n_text"] if spec["annotations"].get("n_labels") else "") for g in groups]
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    lo = min(v for g in groups for v in g["values"]) if groups and groups[0]["values"] else 0
    if spec["annotations"]["brackets"]:
        ax.set_ylim(top=top)
    ax.set_ylim(bottom=min(ax.get_ylim()[0], lo))


def _draw_correlation(ax, spec: Dict[str, Any]) -> None:
    style = spec["style"]
    color = style["palette"][0]
    lw = float(style.get("line_width_pt", 0.6))
    xy = spec["xy"]
    for layer in spec["layers"]:
        if layer["type"] == "regression":
            ax.fill_between(layer["x"], layer["lower"], layer["upper"], color=_light(color, 0.7), linewidth=0, zorder=1)
            ax.plot(layer["x"], layer["y"], color=color, linewidth=lw * 1.6, zorder=2)
    ax.scatter(xy["x"], xy["y"], s=10, color=color, edgecolors="white", linewidths=0.3, zorder=3)


def _draw_contingency(ax, spec: Dict[str, Any]) -> None:
    style = spec["style"]
    table = spec["table"]
    width = spec["layers"][0].get("bar_width", 0.4)
    k = len(table["rows"])
    for i, (row, counts) in enumerate(zip(table["rows"], table["counts"])):
        offset = (i - (k - 1) / 2) * width
        color = style["palette"][i % len(style["palette"])]
        ax.bar([j + offset for j in range(len(counts))], counts, width=width * 0.92, color=color,
               edgecolor="none", label=row)
    ax.set_xticks(range(len(table["columns"])))
    ax.set_xticklabels(table["columns"])
    ax.legend(frameon=False, loc="upper right")


def render_matplotlib(spec: Dict[str, Any]):
    """Draw ``spec`` onto a new matplotlib Figure (Agg; no pyplot state)."""
    from matplotlib import rc_context
    from matplotlib.figure import Figure

    style = spec["style"]
    with rc_context(rc_params(style)):
        fig = Figure(figsize=(style["width_mm"] * MM, style["height_mm"] * MM), layout="constrained")
        ax = fig.add_subplot()
        kind = spec["kind"]
        if kind in ("groups", "paired", "one_sample"):
            _draw_groups(ax, spec)
        elif kind == "correlation":
            _draw_correlation(ax, spec)
        elif kind == "contingency":
            _draw_contingency(ax, spec)
        ann = spec["annotations"]
        title = "\n".join(t for t in (ann.get("statistic"), ann.get("effect_size")) if t)
        if title:
            ax.set_title(title, loc="left", fontsize=style.get("font_size_pt", 7))
        ax.set_xlabel(spec["axes"]["x"].get("label", ""))
        ax.set_ylabel(spec["axes"]["y"].get("label", ""))
        fig._scitex_rc = rc_params(style)
    return fig


def figure_bytes(fig, fmt: str = "png", dpi: int = 300) -> bytes:
    from matplotlib import rc_context

    buf = io.BytesIO()
    with rc_context(getattr(fig, "_scitex_rc", {})):
        fig.savefig(buf, format=fmt, dpi=dpi, facecolor="white")
    return buf.getvalue()


__all__ = ["render_matplotlib", "figure_bytes", "rc_params", "bracket_geometry"]

# EOF
