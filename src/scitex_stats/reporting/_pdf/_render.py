#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_render.py
"""HTML -> PDF with WeasyPrint, network disabled (only data: URIs resolve)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


class RendererUnavailable(RuntimeError):
    """No PDF renderer is installed; HTML and Markdown can still be written."""


def pdf_renderer() -> Optional[str]:
    try:
        import weasyprint

        return f"WeasyPrint {weasyprint.__version__}"
    except Exception:  # noqa: BLE001 - missing system libraries raise OSError, not ImportError
        return None


def _offline_fetcher():
    """Only ``data:`` URIs resolve, so rendering never touches the network."""
    try:
        from weasyprint.urls import URLFetcher  # WeasyPrint >= 66
    except ImportError:
        from weasyprint.urls import default_url_fetcher

        def fetch(url, *args, **kwargs):
            if not url.startswith("data:"):
                raise ValueError(f"report rendering is offline; refused to fetch {url!r}")
            return default_url_fetcher(url, *args, **kwargs)

        return fetch
    return URLFetcher(allowed_protocols=("data",))


def html_to_pdf(html: str, target: Optional[Union[str, Path]] = None) -> bytes:
    """Render ``html`` to PDF bytes (and write them to ``target`` when given)."""
    if pdf_renderer() is None:
        raise RendererUnavailable(
            "PDF output needs WeasyPrint: pip install 'scitex-stats[report]' "
            "(plus Pango, see https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)."
        )
    import logging

    from weasyprint import HTML

    wp_logger = logging.getLogger("weasyprint")
    level = wp_logger.level
    wp_logger.setLevel(logging.ERROR)  # its per-step INFO lines drown the caller's logs
    try:
        data = HTML(string=html, base_url=None, url_fetcher=_offline_fetcher()).write_pdf()
    finally:
        wp_logger.setLevel(level)
    if target is not None:
        Path(target).write_bytes(data)
    return data


__all__ = ["RendererUnavailable", "html_to_pdf", "pdf_renderer"]

# EOF
