#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/_render.py
"""Build the APA 7 summary line, table rows and descriptives from a result dict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._numbers import (
    MISSING, STAT_DECIMALS, format_ci, format_df, format_number, format_p,
    format_p_exact, is_num,
)
from ._rules import TestRule, effect_symbol, is_bounded, rule_for
from ._segments import Segment, S, T, parse_symbol, plain, seg, to_html, to_latex

_EFFECT_NAMES = {
    "d": [T("Cohen's "), S("d")], "d_z": [T("Cohen's "), S("d"), seg("z", "sub")],
    "g": [T("Hedges' "), S("g")], "V": [T("Cramér's "), S("V")],
    "W": [T("Kendall's "), S("W")], "OR": [T("odds ratio, "), S("OR")],
    "r_rb": [T("rank-biserial "), S("r"), seg("rb", "sub")], "δ": [T("Cliff's "), seg("δ", "greek")],
}


def symbol_segments(symbol: str) -> List[Segment]:
    if symbol == "P(X>Y)":
        return [S("P"), T("("), S("X"), T(" > "), S("Y"), T(")")]
    return parse_symbol(symbol)


def _stat_symbol(rule: TestRule, result: Dict[str, Any]) -> str:
    if rule.symbol:
        return rule.symbol
    given = str(result.get("stat_symbol") or "")
    if rule.key == "kendall" and not given:
        return "τ_b"
    return given or "stat"


def _n(result: Dict[str, Any], *keys: str) -> Optional[int]:
    for k in keys:
        if is_num(result.get(k)):
            return int(result[k])
    return None


def _total_n(result: Dict[str, Any]) -> Optional[int]:
    total = _n(result, "n_total", "n", "n_subjects")
    if total is None and isinstance(result.get("n_samples"), list):
        total = int(sum(result["n_samples"]))
    return total


def _df_segments(rule: TestRule, result: Dict[str, Any]) -> List[Segment]:
    if rule.df == "two":
        a = format_df(result.get("df_between", result.get("df_effect")))
        b = format_df(result.get("df_within", result.get("df_error")))
        return [T(f"({a}, {b})")] if a and b else []
    df = format_df(result.get("df"))
    if rule.df == "one_N":
        n = _n(result, "n", "n_subjects")
        if df and n is not None:
            return [T(f"({df}, "), S("N"), T(f" = {n})")]
    if rule.df in ("one", "one_N") and df:
        return [T(f"({df})")]
    return []


def _sample_segments(rule: TestRule, result: Dict[str, Any]) -> List[Segment]:
    if rule.sample == "n1n2":
        n1, n2 = _n(result, "n_x"), _n(result, "n_y")
        if n1 is None or n2 is None:
            return []
        return [S("n"), seg("1", "sub"), T(f" = {n1}, "), S("n"), seg("2", "sub"), T(f" = {n2}")]
    if rule.sample == "n":
        n = _n(result, "n_pairs", "n_x", "n")
        return [S("n"), T(f" = {n}")] if n is not None else []
    if rule.sample == "N":
        n = _total_n(result)
        return [S("N"), T(f" = {n}")] if n is not None else []
    return []


def _ci(result: Dict[str, Any], bounded: bool) -> Optional[str]:
    lo = result.get("effect_size_ci_lower", result.get("ci_lower"))
    hi = result.get("effect_size_ci_upper", result.get("ci_upper"))
    return format_ci(lo, hi, result.get("ci_level", 0.95), leading_zero=not bounded)


def _parts(rule: TestRule, result: Dict[str, Any]) -> Dict[str, Any]:
    sym = _stat_symbol(rule, result)
    stat_bounded = rule.bounded_stat or is_bounded(sym)
    stat = format_number(result.get("statistic"), STAT_DECIMALS, not stat_bounded)
    eff_sym = effect_symbol(result.get("effect_size_metric"))
    eff_bounded = is_bounded(eff_sym)
    eff = result.get("effect_size")
    eff_str = format_number(eff, STAT_DECIMALS, not eff_bounded) if is_num(eff) and eff_sym else None
    duplicate = eff_str is not None and (
        (eff_sym == sym or not rule.show_statistic) and eff_str == stat
    )
    return {
        "symbol": sym, "stat": stat, "stat_bounded": stat_bounded,
        "effect_symbol": eff_sym, "effect": eff_str, "effect_bounded": eff_bounded,
        "duplicate_effect": duplicate and rule.show_statistic,
        "ci": _ci(result, eff_bounded if eff_sym else stat_bounded),
        "df": _df_segments(rule, result),
        "z": format_number(result.get("z"), STAT_DECIMALS) if rule.z and is_num(result.get("z")) else None,
        "p": format_p(result.get("pvalue", result.get("p_value"))),
    }


def summary_segments(rule: TestRule, result: Dict[str, Any], parts: Dict[str, Any]) -> List[Segment]:
    out: List[Segment] = []
    if rule.show_statistic:
        out += [*symbol_segments(parts["symbol"]), *parts["df"], T(f" = {parts['stat']}")]
        if parts["duplicate_effect"] and parts["ci"]:
            out.append(T(", " + parts["ci"]))
        out.append(T(", "))
    if parts["z"]:
        out += [S("z"), T(f" = {parts['z']}, ")]
    out += [S("p"), T(" " + parts["p"])]
    if parts["effect"] and not parts["duplicate_effect"]:
        out += [T(", "), *symbol_segments(parts["effect_symbol"]), T(f" = {parts['effect']}")]
        if parts["ci"]:
            out.append(T(", " + parts["ci"]))
    sample = _sample_segments(rule, result)
    if sample:
        out += [T(", "), *sample]
    return out


def _group_names(result: Dict[str, Any], count: int) -> List[str]:
    desc = result.get("descriptives")
    names = [g.get("name") for g in desc] if isinstance(desc, list) and desc else None
    names = names or result.get("var_names") or result.get("condition_names")
    if not names:
        names = [result.get("var_x"), result.get("var_y")]
    names = [str(n) for n in names if n is not None]
    return names[:count] if len(names) >= count else [f"Group {i + 1}" for i in range(count)]


def descriptives(rule: TestRule, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Per-group n, M/SD (or Mdn/IQR for rank-based tests), APA 7 §6.43 / Table 6.5."""
    groups = result.get("descriptives")
    if not isinstance(groups, list) or not groups:
        return None
    median = rule.center == "median"
    keys = ("median", "iqr") if median else ("mean", "sd")
    columns = [[T("Group")], [S("n")], [S("Mdn")] if median else [S("M")], [S("IQR")] if median else [S("SD")]]
    rows, sentence = [], []
    for g in groups:
        a, b = (format_number(g.get(k), STAT_DECIMALS) for k in keys)
        rows.append([[T(str(g.get("name", "")))], [T(str(g.get("n", MISSING)))], [T(a)], [T(b)]])
        sentence += [T(f"{g.get('name', '')} ("), S("n"), T(f" = {g.get('n')}, "), *columns[2],
                     T(f" = {a}, "), *columns[3], T(f" = {b})"), T("; ")]
    sentence = sentence[:-1]
    return {"columns": columns, "rows": rows, "segments": sentence, "plain": plain(sentence), "html": to_html(sentence)}


def table_rows(rule: TestRule, result: Dict[str, Any], parts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Label/value segment pairs for a results table (asterisks allowed here, §7.14)."""
    rows: List[Dict[str, Any]] = []

    def add(key: str, label: List[Segment], value: Any) -> None:
        if value is None or value == "" or value == MISSING or value == []:
            return
        val = value if isinstance(value, list) else [T(str(value))]
        rows.append({"key": key, "label": label, "value": val,
                     "label_plain": plain(label), "value_plain": plain(val)})

    sym = symbol_segments(parts["symbol"])
    if rule.show_statistic:
        add("statistic", [T("Statistic"), T(" ("), *sym, T(")")], parts["stat"])
    if rule.df == "two":
        a, b = format_df(result.get("df_between")), format_df(result.get("df_within"))
        add("df", [T("Degrees of freedom"), T(" ("), S("df"), T(")")], f"{a}, {b}" if a and b else None)
    elif rule.df != "none":
        add("df", [T("Degrees of freedom"), T(" ("), S("df"), T(")")], format_df(result.get("df")))
    if parts["z"]:
        add("z", [T("Standardized statistic"), T(" ("), S("z"), T(")")], parts["z"])
    add("p", [S("p"), T(" value")], parts["p"].replace("= ", ""))
    add("p_exact", [T("Exact "), S("p")], format_p_exact(result.get("pvalue", result.get("p_value"))))
    if parts["effect"]:
        eff = parts["effect_symbol"]
        name = _EFFECT_NAMES.get(eff, symbol_segments(eff))
        add("effect_size", [T("Effect size"), T(" ("), *name, T(")")], parts["effect"])
        add("interpretation", [T("Interpretation")], result.get("effect_size_interpretation"))
    if parts["ci"]:
        level, bounds = parts["ci"].split(" [", 1)
        add("ci", [T(level)], "[" + bounds)
    if rule.sample == "n1n2":
        names = _group_names(result, 2)
        for i, k in enumerate(("n_x", "n_y")):
            add(f"n_{i + 1}", [S("n"), seg(str(i + 1), "sub"), T(f" ({names[i]})")], _n(result, k))
    elif rule.sample == "n":
        add("n", [T("Sample size"), T(" ("), S("n"), T(")")], _n(result, "n_pairs", "n_x", "n"))
    else:
        ns = result.get("n_samples")
        if isinstance(ns, list):
            for i, (name, n) in enumerate(zip(_group_names(result, len(ns)), ns)):
                add(f"n_{i + 1}", [S("n"), seg(str(i + 1), "sub"), T(f" ({name})")], int(n))
        add("N", [T("Total sample size"), T(" ("), S("N"), T(")")], _total_n(result))
    if is_num(result.get("power")):
        add("power", [T("Power")], format_number(result["power"], STAT_DECIMALS, leading_zero=False))
    if "stars" in result and is_num(result.get("pvalue", result.get("p_value"))):
        alpha = format_number(result.get("alpha", 0.05), 2, leading_zero=False)
        verdict = "significant" if result.get("significant") else "not significant"
        add("significance", [T("Significance"), T(" ("), seg("α", "greek"), T(f" = {alpha})")],
            f"{verdict} ({result['stars']})")
    for note in method_notes(rule, result):
        add("note", [T("Note")], note)
    add("h0", [T("Null hypothesis")], result.get("H0"))
    return rows


def method_notes(rule: TestRule, result: Dict[str, Any]) -> List[List[Segment]]:
    notes: List[List[Segment]] = []
    if rule.key == "ttest_welch":
        notes.append([T("Welch's correction for unequal variances (fractional "), S("df"), T(")")])
    if result.get("yates_correction"):
        notes.append([T("Yates' continuity correction applied")])
    if is_num(result.get("levene_pvalue")):
        notes.append([T("Levene's test "), S("p"), T(" " + format_p(result["levene_pvalue"]))])
    for w in result.get("assumption_warnings") or []:
        notes.append([T(str(w))])
    if isinstance(result.get("warnings"), str):
        notes.append([T(result["warnings"])])
    if rule.z and is_num(result.get("z")):
        notes.append([S("z"), T(" from the tie-corrected normal approximation")])
    return notes


def apa_render(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """APA 7 rendering of a unified result dict, or ``None`` without statistic/p."""
    if not isinstance(result, dict):
        return None
    p = result.get("pvalue", result.get("p_value"))
    if "statistic" not in result and p is None:
        return None
    rule = rule_for(result)
    parts = _parts(rule, result)
    segments = summary_segments(rule, result, parts)
    eff = parts["effect_symbol"]
    return {
        "rule": rule.key,
        "reference": rule.reference,
        "segments": segments,
        "plain": plain(segments),
        "html": to_html(segments),
        "latex": to_latex(segments),
        "stat_symbol": symbol_segments(parts["symbol"]),
        "effect_size_label": symbol_segments(eff) if eff else [],
        "statistic": parts["stat"],
        "df": plain(parts["df"]).strip("()") or None,
        "p_value": parts["p"],
        "effect_size": parts["effect"],
        "ci": parts["ci"],
        "table": table_rows(rule, result, parts),
        "descriptives": descriptives(rule, result),
    }


__all__ = ["apa_render", "symbol_segments", "summary_segments", "table_rows", "descriptives"]

# EOF
