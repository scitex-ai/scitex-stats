#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/_validate.py
"""Check statistics text against the APA 7 rules the formatter uses (``_rules``)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from ._rules import EFFECT_SYMBOLS, RULES, is_bounded
from ._segments import GREEK

_SUBSCRIPT = dict(zip("₀₁₂₃₄₅₆₇₈₉₊ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ", "0123456789+aehijklmnoprstuvx"))

TOKEN = re.compile(
    r"(?<![\w.'’])(?P<base>SD|SE|Mdn|IQR|OR|[χτηεωρδ]|[tFUHDTWrzpdgVnNPM])"
    r"(?P<sup>²)?(?P<sub>_[A-Za-z0-9+]+|[₀-₉₊ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ]+)?"
    r"\s*(?P<df>\([^()]*\))?\s*(?P<rel><=|>=|=|<|>|≤|≥)\s*(?P<val>[−-]?(?:\d+(?:\.\d+)?|\.\d+))"
)

_TEST_RULES: Dict[str, list] = {}
for _r in RULES:
    for _s in ([_r.symbol] if _r.symbol else {"wilcoxon": ["T", "W_+"], "kendall": ["τ_b", "τ_c", "τ"]}[_r.key]):
        _TEST_RULES.setdefault(_s, []).append(_r)
_EFFECTS = {s for _, s in EFFECT_SYMBOLS} | {"r"}
_PURE_TEST = set(_TEST_RULES) - _EFFECTS - {"OR"}
_SAMPLE = {"n", "n_1", "n_2", "N"}
_UNBOUNDED_DESCRIPTIVE = {"M", "SD", "SE", "Mdn", "IQR"}

_REF = {
    "p": "APA 7 §6.36", "zero": "APA 7 §6.36", "dec": "APA 7 §6.36", "minus": "APA 7 §6.45",
    "df": "APA 7 §6.43", "sym": "APA 7 §6.44", "star": "APA 7 §6.43 / §7.14", "space": "APA 7 §6.45",
    "effect": "APA 7 §3.7 (JARS) / §6.43", "n": "APA 7 §3.6 / §6.44",
}


def _key(m: re.Match) -> str:
    base = m.group("base")
    if base == "P" and m.group("df"):
        return "P(X>Y)"
    sub = m.group("sub") or ""
    sub = sub[1:] if sub.startswith("_") else "".join(_SUBSCRIPT.get(c, c) for c in sub)
    return base + ("²" if m.group("sup") else "") + (f"_{sub}" if sub else "")


def _v(out: list, code: str, ref: str, message: str, fix: str, excerpt: str) -> None:
    out.append({"code": code, "message": message, "fix": fix, "excerpt": excerpt.strip(), "reference": _REF[ref]})


def _check_value(out: list, key: str, m: re.Match) -> None:
    val, text = m.group("val"), m.group(0)
    decimals = len(val.split(".")[1]) if "." in val else 0
    if val.startswith("-"):
        _v(out, "APA-MINUS", "minus", "Hyphen used as a minus sign.", "Use the minus sign − (U+2212).", text)
    digits = val.lstrip("−-")
    if key == "p":
        if float(digits) == 0:
            _v(out, "APA-P-ZERO", "p", "p reported as zero.", "Write p < .001.", text)
        elif m.group("rel") == "=" and float(digits) < 0.001:
            _v(out, "APA-P-SMALL", "p", "Exact p below .001.", "Write p < .001.", text)
        if digits.startswith("0."):
            _v(out, "APA-LEADING-ZERO", "zero", "Leading zero on p (cannot exceed 1).", "Drop the zero: p = .032.", text)
        if decimals > 3:
            _v(out, "APA-P-DECIMALS", "p", "p given to more than three decimals.", "Round p to two or three decimals.", text)
        return
    if key in _SAMPLE:
        return
    bounded = is_bounded(key) or key in ("r_s", "W")
    if bounded and digits.startswith("0."):
        _v(out, "APA-LEADING-ZERO", "zero", f"Leading zero on {key} (cannot exceed 1).", f"Drop the zero: {key} = .{digits[2:]}.", text)
    if not bounded and digits.startswith("."):
        _v(out, "APA-MISSING-ZERO", "zero", f"{key} can exceed 1 but has no leading zero.", f"Write {key} = 0{digits}.", text)
    if decimals > 2:
        _v(out, "APA-DECIMALS", "dec", f"{key} given to {decimals} decimals.", "Round statistics to two decimals.", text)


def _check_chunk(out: list, chunk: str) -> None:
    tokens = [(m, _key(m)) for m in TOKEN.finditer(chunk)]
    for m, key in tokens:
        _check_value(out, key, m)
    tests = [(m, k) for m, k in tokens if k in _TEST_RULES]
    pure = [(m, k) for m, k in tests if k in _PURE_TEST]
    if not (pure or tests):
        return
    m, key = (pure or tests)[0]
    rules = _TEST_RULES[key]
    rule = rules[0]
    df = m.group("df")
    keys = {k for _, k in tokens}
    if rule.df != "none" and not df:
        _v(out, "APA-MISSING-DF", "df", f"{key} reported without degrees of freedom.", f"Write {key}(df) = …, e.g. {rule.example.split(',')[0]}.", m.group(0))
    if rule.df == "two" and df and "," not in df:
        _v(out, "APA-DF-PAIR", "df", "F needs numerator and denominator df.", "Write F(df1, df2) = ….", m.group(0))
    if rule.df == "one_N" and df and "N" not in df:
        _v(out, "APA-CHI2-N", "df", f"{key} without N in the parentheses.", f"Write {key}(df, N = total) = ….", m.group(0))
    if "p" not in keys:
        _v(out, "APA-MISSING-P", "p", f"{key} reported without a p value.", "Add p = .xxx or p < .001.", m.group(0))
    has_effect = bool(keys & (_EFFECTS - {key})) or "P(X>Y)" in keys
    if all(r.effect_required and r.show_statistic for r in rules) and not rule.bounded_stat and not has_effect:
        _v(out, "APA-MISSING-EFFECT", "effect", f"No effect size reported with {key}.", "Add an effect size, e.g. d, η², r or V, with its CI when available.", m.group(0))
    if all(r.sample != "none" for r in rules) and not keys & _SAMPLE:
        _v(out, "APA-MISSING-N", "n", "No sample size reported.", "Add n (per group: n₁, n₂) or N.", m.group(0))


class _Italics(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chars: List[Tuple[str, bool]] = []
        self.depth = 0
        self.sup = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("i", "em"):
            self.depth += 1
        elif tag == "sup":
            self.sup += 1

    def handle_endtag(self, tag):
        if tag in ("i", "em") and self.depth:
            self.depth -= 1
        elif tag == "sup" and self.sup:
            self.sup -= 1

    def handle_data(self, data):
        if self.sup:
            data = data.replace("2", "²")
        self.chars += [(c, self.depth > 0) for c in data]


def _check_html(out: list, html: str) -> str:
    parser = _Italics()
    parser.feed(html)
    text = "".join(c for c, _ in parser.chars)
    for m in TOKEN.finditer(text):
        base = m.group("base")
        italic = all(parser.chars[m.start("base") + i][1] for i in range(len(base)))
        if base in GREEK and any(parser.chars[m.start("base") + i][1] for i in range(len(base))):
            _v(out, "APA-GREEK-ITALIC", "sym", f"Greek {base} is italic.", "Set Greek letters upright.", m.group(0))
        elif base not in GREEK and not italic:
            _v(out, "APA-NOT-ITALIC", "sym", f"Symbol {base} is not italic.", f"Italicize {base} (<i>{base}</i>).", m.group(0))
    return text


def validate_apa(text: str = "", html: Optional[str] = None, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Report APA 7 violations in statistics text (and its HTML, when given).

    Returns ``{"ok", "violations": [{code, message, fix, excerpt, reference}],
    "expected"}``; ``expected`` is the formatter's line when ``result`` is given.
    """
    out: List[Dict[str, str]] = []
    if html:
        stripped = _check_html(out, html)
        text = text or stripped
    text = str(text or "")
    if re.search(r"\*|(?<![\w])ns(?![\w])", text):
        _v(out, "APA-ASTERISK", "star", "Significance asterisks or 'ns' in running text.", "Report exact p; keep asterisks for tables and figures.", text)
    if re.search(r"(?<![\w.'’])[tFpUHrzdn][=<>]|[=<>](?=[\d.−-])", text):
        _v(out, "APA-SPACING", "space", "No spaces around = / < / >.", "Write p = .03, not p=.03.", text)
    for bracket in re.findall(r"\[[^\]]*\]", text):
        if re.search(r"(^\[|,\s*)-\d|-\.\d", bracket):
            _v(out, "APA-MINUS", "minus", "Hyphen used as a minus sign in a CI.", "Use the minus sign − (U+2212).", bracket)
    for chunk in re.split(r";\s+|\n+|(?<=[a-z\d)])\.\s+(?=[A-Z])", text):
        _check_chunk(out, chunk)
    expected = None
    if result is not None:
        from ._render import apa_render

        rendered = apa_render(result)
        expected = rendered["plain"] if rendered else None
        if expected and expected not in text:
            _v(out, "APA-MISMATCH", "p", "Text differs from the result's APA line.", f"Use: {expected}", text)
    return {"ok": not out, "violations": out, "expected": expected}


__all__ = ["validate_apa"]

# EOF
