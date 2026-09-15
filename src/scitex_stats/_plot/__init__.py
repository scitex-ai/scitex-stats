#!/usr/bin/env python3
# File: scitex_stats/_plot/__init__.py
"""Plot a test result: neutral spec -> FigRecipe recipe or matplotlib figure.

>>> import scitex_stats as ss
>>> r = ss.run_test("ttest_ind", data=a, data2=b)
>>> spec = ss.plot_spec(r, data=a, data2=b)          # JSON-serialisable, versioned
>>> out = ss.plot(r, data=a, data2=b)                # backend="auto"
>>> out.save("ttest.png")                            # + ttest.yaml when FigRecipe drew it
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._backends import BACKENDS, PlotResult, figrecipe_available, find_figrecipe, render_spec
from ._spec import (
    JITTER_SEED,
    OKABE_ITO,
    PLOT_SPEC_JSON_SCHEMA,
    SCHEMA_ID,
    SCHEMA_VERSION,
    build_plot_spec,
    stack_brackets,
)


def is_plot_spec(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("schema") == SCHEMA_ID


def plot_spec(result: Dict[str, Any], **data: Any) -> Dict[str, Any]:
    """Neutral plot spec for ``result``; pass the raw data the test ran on.

    Keyword arguments: ``data``, ``data2``, ``groups``, ``group_names``,
    ``table``, ``posthoc``, ``stars``, ``popmean``, ``x_label``, ``y_label``,
    ``width_mm``, ``height_mm``. A result that already carries
    ``result["plot_spec"]`` (``run_test(..., plot_spec=True)``) is returned
    as is when no data is given.
    """
    if is_plot_spec(result):
        return result
    if not data and is_plot_spec(result.get("plot_spec")):
        return result["plot_spec"]
    return build_plot_spec(result, **data)


def plot(result: Dict[str, Any], backend: str = "auto", importer=None, **data: Any) -> PlotResult:
    """Render a result (or a ready spec) with FigRecipe if importable, else matplotlib."""
    return render_spec(plot_spec(result, **data), backend=backend, importer=importer)


__all__ = [
    "BACKENDS", "JITTER_SEED", "OKABE_ITO", "PLOT_SPEC_JSON_SCHEMA", "SCHEMA_ID", "SCHEMA_VERSION",
    "PlotResult", "build_plot_spec", "figrecipe_available", "find_figrecipe", "is_plot_spec",
    "plot", "plot_spec", "render_spec", "stack_brackets",
]

# EOF
