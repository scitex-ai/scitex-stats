#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_build.py
"""Assemble the report model: ordered sections of typed blocks made of APA segments.

Renderers (HTML, Markdown, PDF) only lay the model out; every number and
word is decided here, so all formats say the same thing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from scitex_stats._utils._apa import format_number, format_p
from scitex_stats._utils._apa._segments import S, Segment, T, plain, seg
from scitex_stats.posthoc._auto import RANK_METHODS

from . import _analysis, _figure, _methods
from ._inputs import Prepared, prepare
from ._render import pdf_renderer

SECTIONS = (
    ("meta", "Report information"),
    ("data", "Data summary"),
    ("assumptions", "Assumption checks"),
    ("selection", "Test selection"),
    ("primary", "Primary result"),
    ("sensitivity", "Sensitivity analyses"),
    ("posthoc", "Post-hoc comparisons"),
    ("figures", "Figures"),
    ("methods", "Methods"),
    ("references", "References"),
)
CHECK, CROSS = "✓", "✗"


def _t(text: Any) -> List[Segment]:
    return [T(str(text))]


def _num(v: Any, digits: int = 2, lead: bool = True) -> List[Segment]:
    return [T(format_number(v, digits, lead))]


def _p_cell(p: Any) -> List[Segment]:
    s = format_p(p)
    return [T(s[2:] if s.startswith("= ") else s)]


def _table(columns: List[List[Segment]], rows: List[List[List[Segment]]], caption: str = "",
           note: Optional[List[Segment]] = None, cls: str = "") -> Dict[str, Any]:
    return {"type": "table", "columns": columns, "rows": rows, "caption": caption, "note": note, "class": cls}


def _para(segments: List[Segment], style: str = "") -> Dict[str, Any]:
    return {"type": "paragraph", "segments": segments, "style": style}


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _meta(prep: Prepared, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    v = ctx["versions"]
    libs = ", ".join(f"{k} {v[k]}" for k in ("scitex-stats", "numpy", "scipy", "pandas", "matplotlib") if v.get(k))
    rows = [
        (_t("Generated (UTC)"), _t(ctx["generated_at"])),
        (_t("Input"), _t(prep.source)),
        (_t("Input SHA-256"), [seg(prep.input_sha256, "code")]),
        (_t("Analysis data SHA-256"), [seg(prep.analysis_sha256, "code")]),
        (_t("Design"), _t(("Within-subject (repeated measures)" if prep.design == "within" else "Between-group (independent)")
                          + f", {len(prep.names)} {'conditions' if prep.design == 'within' else 'groups'}")),
        (_t("Groups"), _t(", ".join(prep.names))),
        ([T("Significance level ("), seg("α", "greek"), T(")")], _t(format_number(ctx["alpha"], 2, False))),
        (_t("Random seed"), _t(ctx["seed"])),
        (_t("Python"), _t(f"{v.get('python')} ({v.get('platform')})")),
        (_t("Libraries"), _t(libs)),
        (_t("Renderer"), _t(ctx["renderer"])),
        (_t("Primary result SHA-256"), [seg(ctx["primary_sha256"] or "—", "code")]),
    ]
    blocks: List[Dict[str, Any]] = [{"type": "kv", "rows": [list(r) for r in rows]}]
    return blocks + _font_warning(prep.names)


def _font_warning(names: List[str]) -> List[Dict[str, Any]]:
    """Warn, in the report itself, when its own text cannot be drawn.

    A Japanese group name on an image with no CJK font renders as missing glyphs
    and nothing says so - the reader just sees boxes. The check is measured (a
    font query), not assumed, so it appears exactly where the problem exists.
    """
    from ._fonts import cjk_font_available, has_cjk

    text = " ".join(str(name) for name in names)
    if not has_cjk(text) or cjk_font_available():
        return []
    return [
        _para(
            _t("Warning: this report contains Japanese text but no CJK font is installed "
               "(Noto Sans CJK JP, IPAexGothic, ...), so those characters render as missing "
               "glyphs in the PDF and in the figure."),
            "caution",
        )
    ]


def _data(prep: Prepared, primary: str) -> List[Dict[str, Any]]:
    cols = [_t("Group"), [S("n")], _t("Excluded"), [S("M")], [S("SD")], [S("Mdn")], [S("IQR")], _t("Min"), _t("Max")]
    excluded = {n: sum(1 for e in prep.exclusions if e["group"] == n) for n in prep.names}
    rows = []
    for name, g in zip(prep.names, prep.groups):
        q1, q3 = np.percentile(g, [25, 75])
        rows.append([_t(name), _t(g.size), _t(excluded[name]), _num(g.mean()), _num(g.std(ddof=1)),
                     _num(np.median(g)), _num(q3 - q1), _num(g.min()), _num(g.max())])
    blocks = [_table(cols, rows, "Descriptive statistics after exclusions")]
    if prep.exclusions:
        ex_rows = [[_t(e["group"]), _t(e["row"]), _t(e["value"] or "(empty)"), _t(e["reason"])] for e in prep.exclusions]
        blocks.append(_table([_t("Group"), _t("Row"), _t("Value"), _t("Reason")], ex_rows, "Excluded values"))
    else:
        blocks.append(_para(_t("No values were excluded: every cell was a finite number."), "note"))
    return blocks


def _assumptions(an: Dict[str, Any]) -> List[Dict[str, Any]]:
    cols = [_t("Check"), _t("Test"), _t("Applied to"), _t("Statistic"), [S("p")], _t("Threshold"), _t("Met")]
    rows, caveats = [], []
    for r in an["assumption_rows"]:
        if r["statistic"] is not None:
            stat = [S(r["symbol"]), T(" = " + format_number(r["statistic"], 2, r["symbol"] != "W"))]
        else:
            stat = _t("not testable")
        met = CHECK if r["ok"] is True else CROSS if r["ok"] is False else "—"
        threshold = [S("p"), T(f" ≥ {format_number(r['alpha'], 2, False)}")] if r["ok"] is not None or r["statistic"] is None else _t("—")
        rows.append([_t("Normality" if r["check"] == "normality" else "Equal variances"), _t(r["test"]), _t(r["target"]),
                     stat, _p_cell(r["pvalue"]) if r["pvalue"] is not None else _t("—"), threshold, _t(met)])
        if r.get("note") and r["note"] not in caveats:
            caveats.append(f"{r['target']}: {r['note']}" if r["check"] == "normality" else f"{r['test']}: {r['note']}")
    alpha = format_number(an["thresholds"]["alpha"], 2, False)
    note = [T("A check is met when its test does not reject at "), seg("α", "greek"),
            T(f" = {alpha}. Failing to reject is not proof that the assumption holds. ")]
    note += _methods.marked(" ".join(c.rstrip(".") + "." for c in caveats))
    return [_table(cols, rows, "Assumption checks", note)]


def _selection(an: Dict[str, Any]) -> List[Dict[str, Any]]:
    primary = an["primary"]
    rows = [[_t(r["label"] + (" (primary)" if r["test"] == primary["test"] else "")),
             _t(CHECK if r["applicable"] else CROSS), _t("; ".join(r["reasons"]))] for r in an["applicability"]]
    return [
        _table([_t("Test"), _t("Applicable"), _t("Reason")], rows, "Applicability of candidate tests", cls="applicability"),
        _para([T("Recommended primary test: "), seg(primary["label"], "strong")], "lead"),
        _para(_methods.marked(primary["rationale"])),
        _para([T("Decision path: "), T(primary["path"])], "note"),
    ]


def _primary(an: Dict[str, Any]) -> List[Dict[str, Any]]:
    label, result, summary = an["primary"]["label"], an["primary_result"], an["primary_summary"]
    apa = result.get("apa") or {}
    segments = apa.get("segments") or summary.get("apa_segments") or _t(summary.get("apa_plain") or result.get("formatted") or "")
    blocks = [_para([T(f"{label}: "), *segments], "apa")]
    rows = [[r["label"], r["value"]] for r in apa.get("table", []) if r.get("key") not in ("h0",)]
    if not rows:
        rows = [[_t("Statistic"), _t(format_number(summary.get("statistic")))], [[S("p")], _t(summary.get("p_apa") or "—")]]
    blocks.append(_table([_t("Quantity"), _t("Value")], rows, f"{label}: full result"))
    return blocks


def _sensitivity(others: List[Dict[str, Any]], agree: Dict[str, Any], alpha: float, warning: str) -> List[Dict[str, Any]]:
    if not others:
        return [_para(_t("No other test is applicable to this design and data, so no sensitivity analysis was run."), "note")]
    rows = []
    for o in others:
        r = o["result"]
        sig = r.get("significant")
        verdict = "not run" if r.get("pvalue") is None else "significant" if sig else "not significant"
        agrees = "—" if r.get("pvalue") is None else CHECK if sig == agree["primary_significant"] else CROSS
        rows.append([_t(o["label"]), r.get("apa_segments") or _t(r.get("apa_plain") or r.get("error") or ""),
                     _t(verdict), _t(agrees)])
    decision = "significant" if agree["primary_significant"] else "not significant"
    summary = (f"{agree['n_agree']} of {agree['n_total']} sensitivity {'analysis agrees' if agree['n_total'] == 1 else 'analyses agree'} "
               f"with the primary conclusion ({decision} at α = {format_number(alpha, 2, False)}).")
    if not agree["all_agree"]:
        summary += " The conclusion depends on the choice of test; report it with that caveat."
    return [
        _para(_t("Label: SENSITIVITY ANALYSIS. These tests are reported for robustness only."), "label"),
        _table([_t("Test"), _t("Result (APA)"), _t("Decision"), _t("Agrees with primary")], rows, "Other applicable tests"),
        _para(_methods.marked(summary), "lead"),
        _para(_methods.marked(_italic_p(warning) + " See Simmons et al. (2011)."), "caution"),
    ]


def _italic_p(text: str) -> str:
    return text.replace("p-value", "*p* value").replace("p-hacking", "*p*-hacking")


_EFFECT_SYM = {"Hedges' g": [S("g")], "Cliff's delta": [seg("δ", "greek")], "Cohen's d_z": [S("d"), seg("z", "sub")],
               "matched-pairs rank-biserial r": [S("r"), seg("rb", "sub")]}


def _posthoc(ph: Optional[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    if ph is None:
        return [_para(_t(f"Not applicable: post-hoc comparisons follow an omnibus test on 3 or more groups (this report has {k})."), "note")]
    omni = ph.get("omnibus") or {}
    blocks = []
    if omni:
        state = "significant" if omni["significant"] else "not significant"
        blocks.append(_para([T(f"Omnibus test ({omni['name']}) was {state}: "), S("p"), T(f" {omni['p_apa']}.")]))
    if ph.get("method"):
        blocks.append(_para([T("Procedure: "), seg(ph["label"], "strong"), T(f". Multiplicity correction: {ph['correction']}. "),
                             *_methods.marked(ph["reason"])]))
    if ph.get("variance_check"):
        vc = ph["variance_check"]
        blocks.append(_para([T(f"{vc['test']}: "), S("F"), T(f" = {format_number(vc['statistic'])}, "), S("p"),
                             T(f" {format_p(vc['pvalue'])}.")], "note"))
    if "omnibus_not_significant" in ph.get("flags", []):
        blocks.append(_para(_t("Flag: the omnibus test was not significant. These comparisons were requested anyway and are exploratory."), "caution"))
    if not ph.get("ran"):
        if not ph.get("method") or not omni:
            blocks.append(_para(_t(ph.get("reason", "Not run.")), "note"))
        elif not omni.get("significant"):
            blocks.append(_para(_t("Pairwise comparisons were not run because the omnibus test was not significant."), "note"))
        return blocks
    rank = ph["method"] in RANK_METHODS
    first = ph["comparisons"][0]
    eff_sym = _EFFECT_SYM.get(first["effect_size_metric"], _t(first["effect_size_metric"]))
    has_raw = any(c.get("p_unadjusted") is not None for c in ph["comparisons"])
    cols = [_t("Comparison"), [S("n"), seg("1", "sub"), T(", "), S("n"), seg("2", "sub")], _t("Statistic")]
    cols += [[S("p"), T(" (unadjusted)")]] if has_raw else []
    cols += [[S("p"), T(" (adjusted)")], [*eff_sym, T(" [95% CI]")]]
    if not rank:
        cols.append([T("Mean difference [95% CI]")])
    cols.append(_t("Significant"))
    rows = []
    for c in ph["comparisons"]:
        stat = [S(c["stat_symbol"]), T(" = " + format_number(c["statistic"]))]
        if c.get("df") is not None:
            stat.insert(1, T(f"({format_number(c['df'], 2) if not float(c['df']).is_integer() else int(c['df'])})"))
        eff = format_number(c["effect_size"], 2, not rank)
        eff_ci = c["effect_ci_apa"].split(" ", 2)[2] if c.get("effect_ci_apa") else ""
        row = [_t(f"{c['group_i']} vs {c['group_j']}"), _t(f"{c['n_i']}, {c['n_j']}"), stat]
        if has_raw:
            row.append(_p_cell(c["p_unadjusted"]))
        row += [_p_cell(c["p_adjusted"]), _t(f"{eff} {eff_ci}".strip())]
        if not rank:
            diff_ci = c["mean_diff_ci_apa"].split(" ", 2)[2] if c.get("mean_diff_ci_apa") else ""
            row.append(_t(f"{format_number(c['mean_diff'])} {diff_ci}".strip()))
        row.append(_t(CHECK if c["significant"] else "—"))
        rows.append(row)
    note = [T(f"Correction: {ph['correction']}. The adjusted "), S("p"), T(" is the family-wise value used for decisions at "),
            seg("α", "greek"), T(f" = {format_number(ph['alpha'], 2, False)}. ")]
    if first.get("effect_ci_method"):
        note.append(T(f"Effect-size CIs: {first['effect_ci_method']}. "))
    if first.get("mean_diff_ci_kind") == "simultaneous":
        note.append(T("Mean-difference CIs are simultaneous (family-wise) intervals."))
    elif first.get("mean_diff_ci_kind"):
        note.append(T("Mean-difference CIs are per-comparison (unadjusted) intervals."))
    blocks.append(_table(cols, rows, f"{ph['label']} pairwise comparisons", note, cls="posthoc"))
    return blocks


def build_report(
    data: Any,
    design: Any = "between",
    *,
    group_names: Optional[Sequence[str]] = None,
    alpha: float = 0.05,
    seed: int = 42,
    posthoc: str = "auto",
    friedman_method: str = "nemenyi",
    equal_variances: Optional[bool] = None,
    title: str = "Statistical report",
    y_label: str = "Value",
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the whole analysis and return the renderer-neutral report model.
    ``equal_variances`` is the caller's ADVANCE DECLARATION for the ANOVA path; it defaults to
    ``None`` ("not declared"), which keeps the post-hoc on Games-Howell. The report never infers
    it from the observed Brown-Forsythe result.
"""
    from scitex_stats import __version__, _provenance
    from scitex_stats.posthoc import run_posthoc

    if posthoc not in ("auto", "always", "never"):
        raise ValueError("posthoc must be 'auto', 'always' or 'never'")
    prep = prepare(data, design, group_names)
    k = len(prep.groups)
    an = _analysis.analyse(prep, alpha)
    primary_test = an["primary"]["test"]
    primary = an["primary_result"]
    primary_p = an["primary_summary"].get("pvalue")
    others = an["sensitivity"]
    agree = an["agreement"]

    ph = None
    if k >= 3 and posthoc != "never":
        ph = run_posthoc(prep.groups, primary_test, group_names=prep.names, alpha=alpha,
                         omnibus_pvalue=primary_p,
                         # The caller's DECLARATION, never the observed check: passing
                         # an["equal_variances"] made Tukey a data-dependent choice.
                         equal_variances=equal_variances,
                         friedman_method=friedman_method, when="always" if posthoc == "always" else "significant", seed=seed)
        if ph.get("omnibus"):
            ph["omnibus"]["name"] = an["primary"]["label"]

    comparisons = (ph or {}).get("comparisons", []) if k >= 3 else None
    spec = _figure.plot_spec(primary, prep.names, prep.groups, comparisons, y_label)
    brackets = spec["annotations"]["brackets"]
    svg = _figure.render_svg(spec)
    bracket_note = ("Brackets mark pairwise comparisons significant after correction." if k >= 3 else "The bracket shows the primary test.")
    if k >= 3 and not brackets:
        bracket_note = "No pairwise comparison was significant after correction, so no brackets are drawn."

    versions = _provenance.library_versions()
    renderer = pdf_renderer() or "HTML/Markdown only (WeasyPrint not installed)"
    ctx = {"generated_at": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "alpha": alpha,
           "seed": seed, "versions": versions, "renderer": renderer,
           "primary_sha256": (primary.get("provenance") or {}).get("result_sha256")}
    methods_ctx = {"primary": primary_test, "design": prep.design, "alpha": alpha, "k": k, "seed": seed,
                   "rationale_short": _short_rationale(an, prep), "version": __version__,
                   "python": versions.get("python"), "scipy": versions.get("scipy"),
                   "posthoc": {"method": ph["method"], "forced": posthoc == "always"} if ph and ph.get("ran") else None,
                   "sensitivity": [o["test"] for o in others]}

    content = {
        "meta": _meta(prep, ctx),
        "data": _data(prep, primary_test),
        "assumptions": _assumptions(an),
        "selection": _selection(an),
        "primary": _primary(an),
        "sensitivity": _sensitivity(others, agree, alpha, an["warning"]),
        "posthoc": _posthoc(ph, k),
        "figures": [{"type": "figure", "svg": svg, "spec": spec,
                     "caption": _t(f"Figure 1. {y_label} by {'condition' if prep.design == 'within' else 'group'}: boxes show median and IQR, "
                                   f"points are observations{', dots with bars are means with 95% CIs' if _mean_ci(spec) else ''}. {bracket_note}")}],
        "methods": [_para(_methods.methods_segments(methods_ctx), "methods")],
        "references": [{"type": "list", "items": [_t(r) for r in _methods.references(
            primary_test, [o["test"] for o in others], (ph or {}).get("references", []), prep.design)]}],
    }
    sections = [{"id": sid, "title": stitle, "blocks": content[sid]} for sid, stitle in SECTIONS]
    return {
        "schema": "scitex-stats/report/v1",
        "title": title,
        "subtitle": f"{an['primary']['label']} · {', '.join(prep.names)}",
        "generated_at": ctx["generated_at"],
        "sections": sections,
        "summary": {
            "design": prep.design, "groups": prep.names, "n": [int(g.size) for g in prep.groups],
            "input_sha256": prep.input_sha256, "primary_test": primary_test,
            "primary_pvalue": primary_p,
            "primary_apa": (primary.get("apa") or {}).get("plain") or an["primary_summary"].get("apa_plain"),
            "sensitivity": [{"test": o["test"], "pvalue": o["result"].get("pvalue")} for o in others],
            "agreement": agree,
            "posthoc": None if ph is None else {
                "method": ph.get("method"), "correction": ph.get("correction"), "ran": ph.get("ran"),
                "omnibus_significant": (ph.get("omnibus") or {}).get("significant"), "flags": ph.get("flags", []),
                "comparisons": [{k2: c[k2] for k2 in ("group_i", "group_j", "p_adjusted", "p_apa", "effect_size",
                                                      "effect_size_metric", "significant")} for c in ph.get("comparisons", [])]},
            "seed": seed, "alpha": alpha,
        },
    }


def _mean_ci(spec: Dict[str, Any]) -> bool:
    return any(layer.get("type") == "center" and layer.get("estimator") == "mean_ci" for layer in spec.get("layers", []))


def _short_rationale(an: Dict[str, Any], prep: Prepared) -> str:
    basis = an["checks"]["normality"].get("basis") or "the data"
    normal = f"normality not rejected for {basis}" if an["normal"] else f"normality rejected or not assessable for {basis}"
    if prep.design == "within":
        return normal
    var = {True: "equal variances not rejected", False: "variances differ", None: "variance equality not assessable"}[an["equal_variances"]]
    return f"{normal}; {var}"


def model_text(model: Dict[str, Any]) -> str:
    """Plain text of every block, for determinism checks and search."""
    out = [model["title"], model["subtitle"]]
    for s in model["sections"]:
        out.append(s["title"])
        for b in s["blocks"]:
            if b["type"] == "paragraph":
                out.append(plain(b["segments"]))
            elif b["type"] == "table":
                out += [b.get("caption") or ""] + [" | ".join(plain(c) for c in row) for row in [b["columns"], *b["rows"]]]
                out += [plain(b["note"])] if b.get("note") else []
            elif b["type"] == "kv":
                out += [f"{plain(a)}: {plain(v)}" for a, v in b["rows"]]
            elif b["type"] == "list":
                out += [plain(i) for i in b["items"]]
            elif b["type"] == "figure":
                out.append(plain(b["caption"]))
    return "\n".join(out)


__all__ = ["SECTIONS", "build_report", "model_text"]

# EOF
