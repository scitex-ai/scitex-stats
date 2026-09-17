#!/usr/bin/env python3
# File: src/scitex_stats/reporting/_pdf/_api.py
"""``scitex_stats.report(data, design=..., output="report.pdf")``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from ._build import SECTIONS, build_report
from ._html import render_html
from ._markdown import render_markdown
from ._render import html_to_pdf

FORMATS = ("pdf", "html", "md")


def _figure_svg(model: Dict[str, Any]) -> str:
    section = next(s for s in model["sections"] if s["id"] == "figures")
    return section["blocks"][0]["svg"]


def planned_paths(output: Union[str, Path], formats: Iterable[str]) -> List[Path]:
    """The files :func:`report` would write for ``output`` and ``formats``.

    Single source of truth for the writer and for anything that must not clobber an
    existing report. The CLI's overwrite guard used to check only ``--out``, so an
    existing same-stem ``.html``, ``.md`` or figure was silently replaced.
    """
    base = Path(output)
    wanted = tuple(formats)
    paths: List[Path] = []
    if "html" in wanted:
        paths.append(base.with_suffix(".html"))
    if "md" in wanted:
        paths.append(base.with_name(base.stem + "-figure-1.svg"))
        paths.append(base.with_suffix(".md"))
    if "pdf" in wanted:
        paths.append(base.with_suffix(".pdf"))
    return paths


def report(
    data: Any,
    design: Any = "between",
    output: Optional[Union[str, Path]] = "report.pdf",
    *,
    formats: Optional[Iterable[str]] = None,
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
    """Analyse ``data`` and write one bundled report (PDF, plus HTML and Markdown).

    Parameters
    ----------
    data : str | Path | DataFrame | dict | list of lists
        A CSV/TSV path or table with one column per group (wide), or long data
        with ``design={"type": ..., "group_col": ..., "value_col": ...}``.
    design : {"between", "within"} or dict
        ``"paired"`` / ``"repeated"`` are aliases of ``"within"`` (rows are subjects).
    output : path, optional
        The PDF path. HTML and Markdown are written next to it with the same stem.
        ``None`` writes nothing and returns the rendered content in memory.
    formats : iterable of {"pdf", "html", "md"}, optional
        Default: all three.
    alpha, seed : float, int
        Significance level and the seed for every stochastic step (bootstrap CIs, jitter).
    posthoc : {"auto", "always", "never"}
        ``"auto"`` runs pairwise comparisons after a significant omnibus test on
        3+ groups; ``"always"`` runs them regardless and flags a non-significant omnibus.
    timestamp : str, optional
        Fixes the "Generated" field; the only field that otherwise changes between runs.

    Returns
    -------
    dict
        ``model`` (the section model), ``summary``, ``sections`` (titles),
        ``paths`` (written files), and ``pdf_bytes`` / ``html`` / ``markdown``
        for the formats rendered.

    Examples
    --------
    >>> import scitex_stats as ss
    >>> out = ss.report({"A": [5.1, 4.9, 5.6], "B": [6.3, 6.8, 6.1], "C": [7.2, 7.0, 7.5]},
    ...                 output="report.pdf")  # doctest: +SKIP
    >>> out["paths"]["pdf"]  # doctest: +SKIP
    'report.pdf'
    """
    wanted = tuple(formats) if formats is not None else FORMATS
    unknown = set(wanted) - set(FORMATS)
    if unknown:
        raise ValueError(f"Unknown format(s) {sorted(unknown)}; choose from {FORMATS}")
    model = build_report(data, design, group_names=group_names, alpha=alpha, seed=seed, posthoc=posthoc,
                         friedman_method=friedman_method, equal_variances=equal_variances,
                         title=title, y_label=y_label, timestamp=timestamp)
    out: Dict[str, Any] = {"model": model, "summary": model["summary"],
                           "sections": [t for _, t in SECTIONS], "paths": {}}
    base = Path(output) if output is not None else None
    if base is not None:
        base.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(model) if ("html" in wanted or "pdf" in wanted) else None
    if "html" in wanted:
        out["html"] = html
        if base is not None:
            path = base.with_suffix(".html")
            path.write_text(html, encoding="utf-8")
            out["paths"]["html"] = str(path)
    if "md" in wanted:
        out["markdown"] = render_markdown(model)
        if base is not None:
            svg_path = base.with_name(base.stem + "-figure-1.svg")
            svg_path.write_text(_figure_svg(model), encoding="utf-8")
            out["markdown"] = out["markdown"].replace("](figure-1.svg)", f"]({svg_path.name})")
            path = base.with_suffix(".md")
            path.write_text(out["markdown"], encoding="utf-8")
            out["paths"]["md"] = str(path)
            out["paths"]["figure"] = str(svg_path)
    if "pdf" in wanted:
        target = base.with_suffix(".pdf") if base is not None else None
        out["pdf_bytes"] = html_to_pdf(html, target)
        if target is not None:
            out["paths"]["pdf"] = str(target)
    return out


__all__ = ["FORMATS", "planned_paths", "report"]

# EOF
