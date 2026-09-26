#!/usr/bin/env python3
# File: scitex_stats/_plot/_backends.py
"""Render a plot spec with FigRecipe when importable, else plain matplotlib.

FigRecipe is looked up at CALL time through an injectable importer, never at
module import: installing or removing figrecipe changes behaviour without a
restart of anything that imported scitex_stats, and tests can simulate its
absence by passing ``importer=``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from ._mpl import figure_bytes, render_matplotlib

Importer = Callable[[str], Any]
FIGRECIPE_ENTRY = "from_stats_plot_spec"
BACKENDS = ("auto", "figrecipe", "matplotlib")


def default_importer(name: str) -> Any:
    return importlib.import_module(name)


def find_figrecipe(importer: Optional[Importer] = None) -> Optional[Callable[..., Any]]:
    """FigRecipe's public spec importer, or ``None`` when figrecipe (or that API) is absent."""
    try:
        module = (importer or default_importer)("figrecipe")
    except ImportError:
        return None
    return getattr(module, FIGRECIPE_ENTRY, None)


def figrecipe_available(importer: Optional[Importer] = None) -> bool:
    return find_figrecipe(importer) is not None


@dataclass
class PlotResult:
    """A rendered figure plus the backend that drew it."""

    figure: Any
    backend: str
    spec: Dict[str, Any]

    def to_bytes(self, fmt: str = "png", dpi: Optional[int] = None) -> bytes:
        dpi = int(dpi or self.spec["style"].get("dpi", 300))
        if self.backend == "figrecipe":
            import io

            buf = io.BytesIO()
            self.figure.savefig(buf, format=fmt, dpi=dpi, facecolor="white", save_recipe=False, validate=False)
            return buf.getvalue()
        return figure_bytes(self.figure, fmt=fmt, dpi=dpi)

    def close(self) -> None:
        """Release a pyplot-managed FigRecipe figure (matplotlib ones are unmanaged)."""
        if self.backend == "figrecipe":
            import matplotlib.pyplot as plt

            plt.close(getattr(self.figure, "fig", self.figure))

    def save(self, path: Union[str, Path], dpi: Optional[int] = None) -> Path:
        """Save the image; the FigRecipe backend also writes the editable ``.yaml`` recipe."""
        path = Path(path)
        if self.backend == "figrecipe":
            import figrecipe

            figrecipe.save(self.figure, path, validate=False, verbose=False)
            return path
        path.write_bytes(self.to_bytes(path.suffix.lstrip(".") or "png", dpi=dpi))
        return path


def render_spec(spec: Dict[str, Any], backend: str = "auto", importer: Optional[Importer] = None) -> PlotResult:
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}, got {backend!r}")
    if backend in ("auto", "figrecipe"):
        build = find_figrecipe(importer)
        if build is not None:
            fig, _ax = build(spec)
            return PlotResult(fig, "figrecipe", spec)
        if backend == "figrecipe":
            raise ImportError(
                "figrecipe with `from_stats_plot_spec` is required for backend='figrecipe': "
                "pip install 'scitex-stats[figrecipe]'"
            )
    return PlotResult(render_matplotlib(spec), "matplotlib", spec)


__all__ = ["BACKENDS", "PlotResult", "default_importer", "find_figrecipe", "figrecipe_available", "render_spec"]

# EOF
