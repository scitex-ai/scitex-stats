#!/usr/bin/env python3
# File: scitex_stats/_utils/_apa/__init__.py
"""APA 7 reporting: one rule table drives the formatter and the validator.

``apa_render(result)`` -> summary line (segments + plain/HTML/LaTeX), table
rows and descriptives. ``validate_apa(text, html=None, result=None)`` ->
violations of the same rules in manuscript text. The per-test output
format and its APA 7 section references are in the skill page
``_skills/scitex-stats/16_apa7-reporting.md``.
"""

from ._numbers import format_ci, format_df, format_number, format_p, format_p_exact
from ._render import apa_render
from ._rules import RULES, TestRule, rule_by_key, rule_for
from ._segments import MINUS, parse_symbol, plain, to_html, to_latex
from ._validate import validate_apa

__all__ = [
    "MINUS", "RULES", "TestRule", "apa_render", "format_ci", "format_df", "format_number",
    "format_p", "format_p_exact", "parse_symbol", "plain", "rule_by_key", "rule_for",
    "to_html", "to_latex", "validate_apa",
]

# EOF
