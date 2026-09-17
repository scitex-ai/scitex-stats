#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/__init__.py
"""Bundled statistical report: analysis model -> PDF / HTML / Markdown."""

from ._api import FORMATS, planned_paths, report
from ._build import SECTIONS, build_report, model_text
from ._html import render_html
from ._markdown import render_markdown
from ._render import RendererUnavailable, html_to_pdf, pdf_renderer

__all__ = [
    "FORMATS",
    "SECTIONS",
    "RendererUnavailable",
    "build_report",
    "html_to_pdf",
    "model_text",
    "pdf_renderer",
    "planned_paths",
    "render_html",
    "render_markdown",
    "report",
]

# EOF
