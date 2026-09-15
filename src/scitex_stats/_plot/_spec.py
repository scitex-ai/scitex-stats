#!/usr/bin/env python3
# File: scitex_stats/_plot/_spec.py
"""Neutral, library-agnostic plot spec for a test result (schema v1).

The spec carries everything a renderer needs — raw data, precomputed summary
geometry (box stats, mean ± CI, regression band), annotation text as mathtext,
and style tokens — so renderers (matplotlib, FigRecipe, a JS chart) draw it
without doing statistics. See ``PLOT_SPEC_JSON_SCHEMA``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .._utils._apa._numbers import format_p
from .._utils._apa._render import apa_render
from .._utils._apa._rules import rule_for
from ._mathtext import n_mathtext, p_mathtext, segments_to_mathtext

SCHEMA_ID = "scitex-stats.plot-spec"
SCHEMA_VERSION = 1
JITTER_SEED = 42

# Okabe & Ito (2008): distinguishable under all common colour-vision deficiencies.
OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]

SINGLE_COLUMN_MM = 85.0
DOUBLE_COLUMN_MM = 180.0

# rule key -> (kind, center). center: "mean_ci" (parametric) or "median_iqr" (rank-based).
FAMILIES = {
    "ttest_ind": ("groups", "mean_ci"), "ttest_welch": ("groups", "mean_ci"),
    "mannwhitneyu": ("groups", "median_iqr"), "brunner_munzel": ("groups", "median_iqr"),
    "ks_2samp": ("groups", "median_iqr"),
    "anova": ("groups", "mean_ci"), "kruskal": ("groups", "median_iqr"),
    "ttest_rel": ("paired", "mean_ci"), "wilcoxon": ("paired", "median_iqr"),
    "friedman": ("paired", "median_iqr"),
    "ttest_1samp": ("one_sample", "mean_ci"), "shapiro": ("one_sample", "median_iqr"),
    "ks_1samp": ("one_sample", "median_iqr"),
    "pearson": ("correlation", None), "spearman": ("correlation", None), "kendall": ("correlation", None),
    "chi2": ("contingency", None), "fisher": ("contingency", None),
}


def _floats(values: Any) -> List[float]:
    arr = np.asarray(values, dtype=float).ravel()
    return [float(v) for v in arr[np.isfinite(arr)]]


def _t_crit(df: int, level: float = 0.95) -> float:
    from scipy import stats

    return float(stats.t.ppf(0.5 + level / 2, df)) if df > 0 else float("nan")


def _finite_or_none(v: float) -> Optional[float]:
    return float(v) if v is not None and math.isfinite(v) else None


def _summary(values: List[float]) -> Dict[str, Any]:
    """Box stats (Tukey 1.5 IQR whiskers) plus mean ± 95% CI (t)."""
    arr = np.asarray(values, dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"n": 0}
    q1, med, q3 = (float(v) for v in np.percentile(arr, [25, 50, 75]))
    iqr = q3 - q1
    inside = arr[(arr >= q1 - 1.5 * iqr) & (arr <= q3 + 1.5 * iqr)]
    mean = float(arr.mean())
    half = _t_crit(n - 1) * float(arr.std(ddof=1)) / math.sqrt(n) if n > 1 else float("nan")
    return {
        "n": n, "mean": mean,
        "ci_lower": _finite_or_none(mean - half), "ci_upper": _finite_or_none(mean + half),
        "ci_level": 0.95, "median": med, "q1": q1, "q3": q3,
        "whisker_low": float(inside.min()) if inside.size else q1,
        "whisker_high": float(inside.max()) if inside.size else q3,
        "min": float(arr.min()), "max": float(arr.max()),
    }


def _jitter(n: int, index: int, width: float, seed: int) -> List[float]:
    """Deterministic per-group offsets: same data -> same picture, every renderer."""
    rng = np.random.default_rng(seed + index)
    return [float(v) for v in rng.uniform(-width, width, n)]


def stack_brackets(pairs: Sequence[Sequence[int]]) -> List[int]:
    """Tier per bracket: short spans low, overlapping spans stacked above."""
    order = sorted(range(len(pairs)), key=lambda k: (abs(pairs[k][1] - pairs[k][0]), min(pairs[k])))
    tiers = [0] * len(pairs)
    placed: List[int] = []
    for k in order:
        lo, hi = sorted(pairs[k])
        clash = [tiers[m] for m in placed if not (hi < min(pairs[m]) or lo > max(pairs[m]))]
        tiers[k] = (max(clash) + 1) if clash else 0
        placed.append(k)
    return tiers


def _group_names(result: Dict[str, Any], count: int, given: Optional[Sequence[str]]) -> List[str]:
    if given and len(given) >= count:
        return [str(g) for g in given[:count]]
    desc = result.get("descriptives")
    if isinstance(desc, list) and len(desc) >= count:
        return [str(d.get("name", f"Group {i + 1}")) for i, d in enumerate(desc[:count])]
    names = result.get("var_names")
    if isinstance(names, list) and len(names) >= count:
        return [str(n) for n in names[:count]]
    xy = [result.get("var_x"), result.get("var_y")]
    if count <= 2 and all(xy[:count]):
        return [str(v) for v in xy[:count]]
    return [f"Group {i + 1}" for i in range(count)]


def _summary_lines(result: Dict[str, Any]) -> Dict[str, str]:
    """APA summary split into test statistic/p and effect size/CI, as mathtext."""
    apa = apa_render(result) or {}
    segs = apa.get("segments") or []
    out = {"summary": segments_to_mathtext(segs), "statistic": "", "effect_size": ""}
    # Split before the effect-size symbol: "t(14) = −6.35, p < .001" | "d = −3.18, 95% CI [...]".
    eff_label = apa.get("effect_size_label") or []
    cut = None
    if eff_label and apa.get("effect_size"):
        for i in range(len(segs) - len(eff_label) + 1):
            if segs[i:i + len(eff_label)] == eff_label and i > 0 and any(s.get("text") == "p" for s in segs[:i]):
                cut = i
                break
    if cut is not None:
        head = segs[:cut]
        if head and head[-1].get("kind") == "text":
            head = head[:-1] + [{"text": head[-1]["text"].rstrip(", "), "kind": "text"}]
        tail = segs[cut:]
        # Sample sizes are drawn under each group; keep the effect line short.
        for j, s in enumerate(tail):
            if s.get("kind") == "text" and s.get("text", "").startswith(", ") and j + 1 < len(tail) \
                    and tail[j + 1].get("text") in ("n", "N"):
                tail = tail[:j]
                break
        out["statistic"] = segments_to_mathtext(head)
        out["effect_size"] = segments_to_mathtext(tail)
    else:
        out["statistic"] = out["summary"]
    return out


def _bracket(i: int, j: int, p: Any, stars: str, show_stars: bool, source: str) -> Dict[str, Any]:
    p_text = p_mathtext(format_p(p))
    return {
        "group1": int(i), "group2": int(j),
        "p_value": float(p) if isinstance(p, (int, float)) and math.isfinite(p) else None,
        "p_text": p_text, "stars": stars or "",
        "text": (stars or "n.s.") if show_stars else p_text,
        "source": source, "tier": 0,
    }


def _stars(p: Any) -> str:
    if not isinstance(p, (int, float)) or not math.isfinite(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


def _groups_block(names: List[str], groups: List[List[float]], seed: int, width: float) -> List[Dict[str, Any]]:
    return [
        {"name": name, "position": i, "values": vals, "jitter": _jitter(len(vals), i, width, seed),
         "summary": _summary(vals), "n_text": n_mathtext(len(vals))}
        for i, (name, vals) in enumerate(zip(names, groups))
    ]


def _regression(x: List[float], y: List[float]) -> Optional[Dict[str, Any]]:
    """OLS fit with the 95% confidence band of the mean response."""
    xa, ya = np.asarray(x), np.asarray(y)
    n = xa.size
    if n < 3 or np.ptp(xa) == 0:
        return None
    slope, intercept = (float(v) for v in np.polyfit(xa, ya, 1))
    resid = ya - (slope * xa + intercept)
    s = math.sqrt(float(resid @ resid) / (n - 2))
    sxx = float(((xa - xa.mean()) ** 2).sum())
    grid = np.linspace(xa.min(), xa.max(), 50)
    fit = slope * grid + intercept
    half = _t_crit(n - 2) * s * np.sqrt(1 / n + (grid - xa.mean()) ** 2 / sxx)
    return {
        "method": "ols", "slope": slope, "intercept": intercept, "ci_level": 0.95,
        "x": [float(v) for v in grid], "y": [float(v) for v in fit],
        "lower": [float(v) for v in fit - half], "upper": [float(v) for v in fit + half],
    }


def build_plot_spec(
    result: Dict[str, Any],
    *,
    data: Any = None,
    data2: Any = None,
    groups: Optional[Sequence[Any]] = None,
    group_names: Optional[Sequence[str]] = None,
    table: Any = None,
    posthoc: Optional[Sequence[Dict[str, Any]]] = None,
    stars: bool = False,
    popmean: Optional[float] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    width_mm: float = SINGLE_COLUMN_MM,
    height_mm: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a JSON-serialisable plot spec from a test result and its raw data.

    Parameters
    ----------
    result : dict
        A result from ``run_test`` / ``test_*`` (unified result dict).
    data, data2, groups, table :
        The raw data the test was run on (same shapes as ``run_test``).
    posthoc : list of dict, optional
        Pairwise comparisons (``posthoc_tukey(..., return_as="list")``); drawn
        as stacked brackets.
    stars : bool
        Bracket text as significance stars instead of the APA p text.
    """
    rule = rule_for(result)
    kind, center = FAMILIES.get(rule.key, ("groups", "mean_ci"))
    lines = _summary_lines(result)
    p = result.get("pvalue", result.get("p_value"))
    seed = JITTER_SEED
    spec: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": SCHEMA_VERSION,
        "kind": kind,
        "test": {"key": rule.key, "method": result.get("test_method") or rule.name,
                 "p_value": _finite_or_none(p) if isinstance(p, (int, float)) else None},
        "layers": [],
        "annotations": {"brackets": [], "summary": lines["summary"], "statistic": lines["statistic"],
                        "effect_size": lines["effect_size"], "show_stars": bool(stars), "n_labels": True},
        "axes": {"x": {"label": x_label or ""}, "y": {"label": y_label or ""}},
        "style": {
            "width_mm": float(width_mm), "height_mm": float(height_mm or width_mm * 0.8),
            "font_family": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
            "font_family_cjk": ["Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "TakaoGothic"],
            "font_size_pt": 7, "line_width_pt": 0.6, "palette": list(OKABE_ITO),
            "dpi": 300, "jitter_seed": seed, "jitter_width": 0.12,
            "spines": ["left", "bottom"], "tick_direction": "out",
        },
    }

    if kind in ("groups", "paired", "one_sample"):
        if groups is not None:
            raw = [_floats(g) for g in groups]
        else:
            raw = [_floats(d) for d in (data, data2) if d is not None]
        names = _group_names(result, len(raw), group_names)
        spec["groups"] = _groups_block(names, raw, seed, spec["style"]["jitter_width"])
        spec["axes"]["x"]["label"] = x_label or ("Condition" if kind == "paired" else "")
        spec["axes"]["y"]["label"] = y_label or "Value"
        spec["axes"]["x"]["ticks"] = list(range(len(raw)))
        spec["axes"]["x"]["tick_labels"] = names
        spec["layers"] = [{"type": "box", "center": center}, {"type": "points"}]
        if kind == "paired":
            spec["layers"].insert(1, {"type": "paired_lines"})
        spec["layers"].append({"type": "center", "estimator": center})
        if kind == "one_sample" and popmean is not None:
            spec["layers"].append({"type": "reference_line", "axis": "y", "value": float(popmean),
                                   "label": r"$\mu_{0}$ = %g" % float(popmean)})
        pairs: List[Dict[str, Any]] = []
        if posthoc:
            index = {name: i for i, name in enumerate(names)}
            for c in posthoc:
                i, j = index.get(str(c.get("group_i"))), index.get(str(c.get("group_j")))
                if i is None or j is None:
                    continue
                cp = c.get("pvalue_adjusted", c.get("pvalue"))
                pairs.append(_bracket(i, j, cp, c.get("pstars") or _stars(cp), stars, "posthoc"))
        elif len(raw) == 2 and kind in ("groups", "paired"):
            pairs.append(_bracket(0, 1, p, result.get("stars") or _stars(p), stars, "test"))
        tiers = stack_brackets([(b["group1"], b["group2"]) for b in pairs])
        for b, t in zip(pairs, tiers):
            b["tier"] = t
        spec["annotations"]["brackets"] = pairs

    elif kind == "correlation":
        x, y = _floats(data), _floats(data2)
        if len(x) != len(y):
            raise ValueError("correlation plot needs x and y of equal length")
        names = _group_names(result, 2, group_names)
        spec["xy"] = {"x": x, "y": y, "n": len(x), "n_text": n_mathtext(len(x))}
        if not spec["annotations"]["effect_size"]:
            spec["annotations"]["effect_size"] = n_mathtext(len(x))
        spec["axes"]["x"]["label"] = x_label or names[0]
        spec["axes"]["y"]["label"] = y_label or names[1]
        spec["layers"] = [{"type": "scatter"}]
        reg = _regression(x, y)
        if reg:
            spec["layers"].append({"type": "regression", **reg})

    elif kind == "contingency":
        if table is None:
            table = groups if groups is not None else np.vstack([data, data2])
        counts = np.asarray(table, dtype=float)
        if counts.ndim != 2:
            raise ValueError("contingency plot needs a 2-D table")
        rows = [str(n) for n in (group_names or [])][: counts.shape[0]]
        rows += [f"Row {i + 1}" for i in range(len(rows), counts.shape[0])]
        cols = [f"Column {j + 1}" for j in range(counts.shape[1])]
        spec["table"] = {"rows": rows, "columns": cols, "counts": counts.tolist(),
                         "n": int(counts.sum())}
        spec["axes"]["x"]["label"] = x_label or ""
        spec["axes"]["y"]["label"] = y_label or "Count"
        spec["axes"]["x"]["ticks"] = list(range(counts.shape[1]))
        spec["axes"]["x"]["tick_labels"] = cols
        spec["layers"] = [{"type": "grouped_bars", "series": "rows", "bar_width": 0.8 / counts.shape[0]}]

    return spec


PLOT_SPEC_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://scitex.ai/schemas/scitex-stats/plot-spec/v1.json",
    "title": "scitex-stats plot spec",
    "type": "object",
    "required": ["schema", "version", "kind", "test", "layers", "annotations", "axes", "style"],
    "properties": {
        "schema": {"const": SCHEMA_ID},
        "version": {"const": SCHEMA_VERSION},
        "kind": {"enum": ["groups", "paired", "one_sample", "correlation", "contingency"]},
        "test": {"type": "object", "required": ["key", "method"]},
        "groups": {"type": "array", "items": {"type": "object", "required": ["name", "position", "values", "jitter", "summary"]}},
        "xy": {"type": "object", "required": ["x", "y"]},
        "table": {"type": "object", "required": ["rows", "columns", "counts"]},
        "layers": {"type": "array", "items": {"type": "object", "required": ["type"], "properties": {
            "type": {"enum": ["box", "violin", "points", "paired_lines", "center", "reference_line",
                              "scatter", "regression", "grouped_bars"]}}}},
        "annotations": {"type": "object", "required": ["brackets"], "properties": {
            "brackets": {"type": "array", "items": {"type": "object",
                         "required": ["group1", "group2", "text", "tier"]}}}},
        "axes": {"type": "object"},
        "style": {"type": "object", "required": ["width_mm", "height_mm", "palette", "jitter_seed"]},
    },
}


__all__ = ["SCHEMA_ID", "SCHEMA_VERSION", "JITTER_SEED", "OKABE_ITO", "FAMILIES",
           "build_plot_spec", "stack_brackets", "PLOT_SPEC_JSON_SCHEMA"]

# EOF
