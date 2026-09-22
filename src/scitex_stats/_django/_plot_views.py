#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot and FigRecipe-integration views for the Statistics app.

``api/plot`` renders a test result server-side from its neutral plot spec.
``api/integrations`` reports whether the host also runs the FigRecipe app,
discovered from the ``scitex.apps`` entry points plus the host's URL
configuration — figrecipe itself is never imported here.
"""

from __future__ import annotations

import base64
import json
import threading
from typing import Any, Dict, List, Optional

# PS-233: `django` is a `[server]`-only distribution. This module is a Django
# view set — it has no meaning without the framework — so the guard FAILS
# LOUDLY with the extra to install instead of silently degrading.
try:
    from django.http import JsonResponse
    from django.urls import NoReverseMatch, reverse
    from django.views.decorators.csrf import csrf_exempt
    from django.views.decorators.http import require_GET, require_POST
except ImportError as exc:
    raise ImportError(
        "scitex_stats._django._plot_views needs Django, which is not installed. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from exc

# pyplot (FigRecipe backend) is process-global state; one render at a time.
_RENDER_LOCK = threading.Lock()

FIGRECIPE_APP = "figrecipe"
# Hub URL names first; a host without them has no FigRecipe mount to open.
_FIGRECIPE_API_URLS = ("figrecipe_app:figrecipe_editor",)
_FIGRECIPE_PAGE_URLS = ("figrecipe_app:figure_editor", "figrecipe_app:figrecipe_editor")
IMPORT_ENDPOINT = "api/import/stats-plot-spec"
_POSTHOC = {"tukey", "games_howell"}


def discover_app_names() -> List[str]:
    """Names of installed ``scitex.apps`` plugins, read from metadata only."""
    try:
        from scitex_app.plugins import discover_plugin_apps

        return [p.name for p in discover_plugin_apps()]
    except ImportError:
        from importlib.metadata import entry_points

        return [ep.name for ep in entry_points(group="scitex.apps")]


def _reverse_first(names) -> Optional[str]:
    for name in names:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return None


def figrecipe_integration(discover=discover_app_names, resolve=_reverse_first) -> Dict[str, Any]:
    """FigRecipe availability: installed as a plugin AND mounted by this host."""
    if FIGRECIPE_APP not in discover():
        return {"available": False}
    api_base = resolve(_FIGRECIPE_API_URLS)
    page = resolve(_FIGRECIPE_PAGE_URLS)
    if not api_base or not page:
        return {"available": False}
    return {
        "available": True,
        "import_url": api_base.rstrip("/") + "/" + IMPORT_ENDPOINT,
        "open_url": page,
    }


@require_GET
def integrations(request):
    return JsonResponse({"figrecipe": figrecipe_integration()})


def _run_kwargs(body: Dict[str, Any]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"alternative": body.get("alternative", "two-sided")}
    for key in ("data", "data2", "groups"):
        if key in body:
            kwargs[key] = body[key]
    if body.get("popmean") is not None:
        kwargs["popmean"] = float(body["popmean"])
    if isinstance(body.get("group_names"), list):
        kwargs["group_names"] = [str(n) for n in body["group_names"]]
    return kwargs


def _posthoc(body: Dict[str, Any], kwargs: Dict[str, Any]) -> Optional[list]:
    method = body.get("posthoc")
    groups = kwargs.get("groups")
    if method not in _POSTHOC or not groups or len(groups) < 3:
        return None
    from scitex_stats import posthoc as posthoc_mod

    fn = {"tukey": posthoc_mod.posthoc_tukey, "games_howell": posthoc_mod.posthoc_games_howell}[method]
    return fn(groups, group_names=kwargs.get("group_names"), return_as="list")


def _data_uri(mime: str, payload: bytes) -> str:
    return f"data:{mime};base64," + base64.b64encode(payload).decode("ascii")


@csrf_exempt  # stateless rendering: no side effects to forge
@require_POST
def plot(request):
    """Run the test, build its plot spec, return the spec plus SVG and 300 dpi PNG."""
    from scitex_stats import plot as render, plot_spec, run_test
    from scitex_stats._utils._serialize import to_json_safe

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON body"}, status=400)
    test_name = body.get("test_name") or body.get("name")
    if not test_name:
        return JsonResponse({"error": "test_name required"}, status=400)
    kwargs = _run_kwargs(body)
    try:
        result = run_test(test_name, **kwargs)
        spec_kwargs = {k: kwargs[k] for k in ("data", "data2", "groups", "group_names") if k in kwargs}
        if test_name == "ttest_1samp":
            spec_kwargs["popmean"] = kwargs.get("popmean", 0.0)
        spec = plot_spec(result, posthoc=_posthoc(body, kwargs), stars=bool(body.get("stars")), **spec_kwargs)
        with _RENDER_LOCK:
            out = render(spec, backend=body.get("backend", "auto"))
            try:
                svg = out.to_bytes("svg")
                png = out.to_bytes("png")
            finally:
                out.close()
    except (ValueError, TypeError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001 - a clean 400 beats a 500 page in the pane
        return JsonResponse({"error": f"{type(e).__name__}: {e}"}, status=400)
    return JsonResponse({
        "plot_spec": to_json_safe(spec),
        "backend": out.backend,
        "svg": _data_uri("image/svg+xml", svg),
        "png": _data_uri("image/png", png),
        "figrecipe": figrecipe_integration(),
    })


__all__ = ["discover_app_names", "figrecipe_integration", "integrations", "plot"]

# EOF
