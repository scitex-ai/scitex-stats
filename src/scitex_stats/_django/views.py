#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Views for the scitex-stats Django app (the Statistics calculator UI).

Every view is a thin adapter over the ``scitex_stats`` package — no
statistical logic lives here. The dispatcher, effect sizes, power,
post-hoc, and corrections are all imported from the common package (the
whole point of compass §12 L451/#210: logic in the package, thin app UI).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from django.apps import apps as _django_apps
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from scitex_app._django import mount_prefix

# The dotted INSTALLED_APPS entry a host must carry for these views to work
# (one string, so the refusal and the docs name the same thing — see apps.py
# for why the label is "stats_calculator").
APP_NAME = "scitex_stats._django"
APP_CONFIG_PATH = "scitex_stats._django.apps.StatsCalculatorConfig"
APP_LABEL = "stats_calculator"


def _refuse_unless_app_installed() -> None:
    """Fail at import when a host serves these views without our app.

    The hub mounts this module's views under its own urlconf. If the host
    forgets to add ``StatsCalculatorConfig`` to INSTALLED_APPS, Django's
    app_directories template loader never sees ``stats/stats.html`` and
    every request to the app answers 500 TemplateDoesNotExist. Serving an
    app's views without installing the app is a declaration the host cannot
    honour, so it must fail where the cause is legible — at import time,
    which is where ``manage.py check`` and the host's urlconf both reach.

    Three-valued on purpose: the app registry may not be READY when a script
    or doc build imports this module early. That is UNKNOWN, not
    "installed", and an import-time guard must not raise on unknown.
    """
    if not _django_apps.ready:
        return
    if _django_apps.is_installed(APP_NAME):
        return
    raise ImproperlyConfigured(
        f"{__name__} was imported, but '{APP_NAME}' is not in INSTALLED_APPS. "
        "Django's template loader only searches installed apps, so every page "
        "view here would answer 500 TemplateDoesNotExist (stats/stats.html). "
        f"Add '{APP_CONFIG_PATH}' (label '{APP_LABEL}') to the host project's "
        "INSTALLED_APPS next to the other mounted leaf apps."
    )


_refuse_unless_app_installed()

# Stats fills only the module pane; the shell's AI/files/viewer panes stay closed.
SHELL_PANES = {"ai": "unused", "files": "unused", "viewer": "unused"}


def _finite(value: Any) -> Any:
    # JSON has no NaN/Infinity; the browser's JSON.parse rejects them.
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    return value


def _safe(payload: Any) -> Any:
    """JSON-safe conversion (numpy -> native, NaN/Inf -> null)."""
    try:
        from scitex_stats import to_json_safe

        payload = to_json_safe(payload)
    except Exception:
        pass
    return _finite(payload)


def index(request):
    """Serve the Statistics page (Data | Test | Results panes)."""
    from scitex_stats import __version__
    from scitex_ui.branding import shell_context

    from . import _projects

    context = shell_context("Statistics", panes=SHELL_PANES)
    context["stx_mount"] = mount_prefix(request)
    # App-header identity: OUR package version (never the host's) and the
    # project this request resolves to, so the shared picker renders the
    # current one instead of guessing.
    context["stats_version"] = __version__
    context["current_project"] = _projects.current_project_id(request)
    # Project-default mode renders the active project's AUTHORIZED files. An
    # unauthorized/absent project yields [] here and the panel stays hidden,
    # so the page never hints at data the caller cannot read.
    context["project_files"] = _projects.list_data_files(context["current_project"]) or []
    html = render_to_string("stats/stats.html", context, request=request)
    return HttpResponse(html)


@require_GET
def health(request):
    """Liveness probe; also proves the package is importable end-to-end."""
    from scitex_stats import __version__

    return JsonResponse(
        _safe(
            {
                "status": "ok",
                "app": "scitex-stats",
                "package_version": __version__,
                "tests": len(_available_tests()),
            }
        )
    )


def _available_tests() -> List[str]:
    from scitex_stats import available_tests

    return list(available_tests())


@require_GET
def tests(request):
    """Catalogue of runnable test names."""
    return JsonResponse(_safe({"tests": _available_tests()}))


@csrf_exempt  # stateless calculations: no side effects to forge
@require_POST
def recommend(request):
    """Rank appropriate tests from a StatContext payload."""
    import json

    from scitex_stats import StatContext, recommend_tests

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))

    n_groups = int(body.get("n_groups", 2))
    sample_sizes = body.get("sample_sizes") or [30] * n_groups
    ctx = StatContext(
        n_groups=n_groups,
        sample_sizes=[int(s) for s in sample_sizes],
        outcome_type=body.get("outcome_type", "continuous"),
        design=body.get("design", "between"),
        paired=bool(body.get("paired", False)),
        has_control_group=bool(body.get("has_control_group", False)),
        n_factors=int(body.get("n_factors", 1)),
    )
    recs = recommend_tests(ctx, top_k=int(body.get("top_k", 3)))
    return JsonResponse(_safe({"recommendations": list(recs)}))


def _recommend_args(body: Dict[str, Any]) -> Dict[str, Any]:
    groups = body.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("groups required")
    names = body.get("group_names")
    return {
        "data": groups,
        "design": body.get("design") or None,
        "scale": body.get("scale") or None,
        "group_names": [str(n) for n in names] if isinstance(names, list) else None,
    }


@csrf_exempt
@require_POST
def recommend_test(request):
    """One primary test + decision path + ✓/✗ applicability for the posted groups."""
    import json

    from scitex_stats import recommend_test as _recommend_test

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    try:
        out = _recommend_test(**_recommend_args(body), assume_equal_variance=bool(body.get("assume_equal_variance")))
    except (TypeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse(_safe(out))


@csrf_exempt
@require_POST
def run_all(request):
    """Every applicable test in sequence: primary + labelled sensitivity analyses."""
    import json

    from scitex_stats import run_all_applicable

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    try:
        out = run_all_applicable(
            **_recommend_args(body),
            primary=body.get("primary") or None,
            alternative=body.get("alternative", "two-sided"),
            assume_equal_variance=bool(body.get("assume_equal_variance")),
        )
    except (TypeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    out.pop("recommendation", None)  # the page already holds it
    return JsonResponse(_safe(out))


@csrf_exempt
@require_http_methods(["POST"])
def run(request):
    """Run a single test by name; returns the unified result dict."""
    import json

    from scitex_stats import run_test

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))

    test_name = body.get("test_name") or body.get("name")
    if not test_name:
        return JsonResponse({"error": "test_name required"}, status=400)

    kwargs = {
        "alternative": body.get("alternative", "two-sided"),
    }
    if "data" in body:
        kwargs["data"] = body["data"]
    if "data2" in body:
        kwargs["data2"] = body["data2"]
    if "groups" in body:
        kwargs["groups"] = body["groups"]
    if body.get("popmean") is not None:
        kwargs["popmean"] = float(body["popmean"])
    if isinstance(body.get("group_names"), list):
        kwargs["group_names"] = [str(n) for n in body["group_names"]]

    try:
        result = run_test(test_name, **kwargs)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001 - surface a clean 400, not a 500 stack
        return JsonResponse({"error": f"{type(e).__name__}: {e}"}, status=400)
    return JsonResponse(_safe(result))


@csrf_exempt
@require_http_methods(["POST"])
def describe(request):
    """Descriptive statistics for one sample."""
    import json

    from scitex_stats import descriptive

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    data = body.get("data")
    if not data:
        return JsonResponse({"error": "data required"}, status=400)
    values, names = descriptive.describe(data)
    return JsonResponse(
        _safe({"statistics": dict(zip(names, [float(v) for v in values]))})
    )


@csrf_exempt
@require_http_methods(["POST"])
def effect_size(request):
    """Standalone effect size between two groups."""
    import json

    from scitex_stats import effect_sizes

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    g1, g2 = body.get("group1"), body.get("group2")
    if g1 is None or g2 is None:
        return JsonResponse({"error": "group1 and group2 required"}, status=400)
    measure = body.get("measure", "cohens_d")
    fn = {
        "cohens_d": effect_sizes.cohens_d,
        "cliffs_delta": effect_sizes.cliffs_delta,
    }.get(measure)
    if fn is None:
        return JsonResponse(
            {"error": f"unsupported measure '{measure}'"}, status=400
        )
    value = fn(g1, g2)
    return JsonResponse(_safe({"measure": measure, "value": value}))


@csrf_exempt
@require_http_methods(["POST"])
def power(request):
    """Power / required sample size for a t-test design."""
    import json

    from scitex_stats import power as power_mod

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    which = body.get("which", "power")
    if which == "power":
        n1, n2 = body.get("n1"), body.get("n2")
        value = power_mod.power_ttest(
            float(body["effect_size"]),
            n1=int(n1) if n1 is not None else None,
            n2=int(n2) if n2 is not None else None,
            alpha=float(body.get("alpha", 0.05)),
            alternative=body.get("alternative", "two-sided"),
        )
    else:  # sample size
        value = power_mod.sample_size_ttest(
            float(body["effect_size"]),
            power=float(body.get("target_power", 0.8)),
            alpha=float(body.get("alpha", 0.05)),
            alternative=body.get("alternative", "two-sided"),
        )
    return JsonResponse(_safe({"which": which, "value": value}))


@csrf_exempt
@require_http_methods(["POST"])
def posthoc(request):
    """Post-hoc pairwise comparisons after ANOVA/Kruskal."""
    import json

    from scitex_stats import posthoc as posthoc_mod

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    groups = body.get("groups")
    if not groups:
        return JsonResponse({"error": "groups required"}, status=400)
    method = body.get("method", "tukey")
    group_names = body.get("group_names")
    fn = {
        "tukey": posthoc_mod.posthoc_tukey,
        "games_howell": posthoc_mod.posthoc_games_howell,
        "dunnett": posthoc_mod.posthoc_dunnett,
    }.get(method)
    if fn is None:
        return JsonResponse({"error": f"unsupported method '{method}'"}, status=400)
    from scitex_stats._utils._apa import format_p

    out = fn(groups, group_names=group_names, return_as="list")
    for c in out:
        c["p_apa"] = format_p(c.get("pvalue"))
    return JsonResponse(_safe({"method": method, "comparisons": out}))


@csrf_exempt
@require_http_methods(["POST"])
def correct(request):
    """Multiple-comparison correction over a list of p-values."""
    import json

    from scitex_stats import correct as correct_mod

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    pvalues = body.get("pvalues")
    if not pvalues:
        return JsonResponse({"error": "pvalues required"}, status=400)
    method = body.get("method", "fdr_bh")
    fn, kwargs = {
        "bonferroni": (correct_mod.correct_bonferroni, {}),
        "holm": (correct_mod.correct_holm, {}),
        "sidak": (correct_mod.correct_sidak, {}),
        "fdr_bh": (correct_mod.correct_fdr, {"method": "bh"}),
        "fdr_by": (correct_mod.correct_fdr, {"method": "by"}),
    }.get(method, (None, None))
    if fn is None:
        return JsonResponse({"error": f"unsupported method '{method}'"}, status=400)
    results = [
        {"name": f"p{i}", "pvalue": float(p)} for i, p in enumerate(pvalues)
    ]
    from scitex_stats._utils._apa import format_p

    out = fn(results, alpha=float(body.get("alpha", 0.05)), **kwargs)
    for r in out:
        r["p_apa"] = format_p(r.get("pvalue"))
        r["p_adjusted_apa"] = format_p(r.get("pvalue_adjusted"))
    return JsonResponse(_safe({"method": method, "results": out}))


def _parse_body(request, json):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return {"error": "invalid JSON body", "status": 400}


# ---------------------------------------------------------------------------
# Project-default mode: the active project's data, and the artifacts written
# back to it. Every route is fail-closed through _projects (an unauthorized
# project id has no path at all), so a host that mounts this app behind its
# own auth still cannot read a project the provider does not list for the
# caller.
# ---------------------------------------------------------------------------


@require_GET
def project_files(request):
    """List the active project's authorized CSV/TSV files."""
    from . import _projects

    project = request.GET.get("project", "")
    files = _projects.list_data_files(project)
    if files is None:
        return JsonResponse({"error": "project not accessible"}, status=403)
    return JsonResponse({"project": project, "files": files})


@require_GET
def project_import(request):
    """Read one authorized project data file so the client can load it."""
    from . import _projects

    project = request.GET.get("project", "")
    name = request.GET.get("name", "")
    text = _projects.read_data_file(project, name)
    if text is None:
        # One refusal for every reason: unknown project, traversal, wrong
        # format, missing, oversized. A caller learns only "not available".
        return JsonResponse({"error": "file not available"}, status=403)
    return JsonResponse({"project": project, "name": name, "text": text})


@csrf_exempt
@require_POST
def project_save(request):
    """Write a config / results / plot / provenance artifact into the project."""
    import json

    from . import _projects

    body = _parse_body(request, json)
    if isinstance(body, dict) and "error" in body:
        return JsonResponse(body, status=body.pop("status", 400))
    saved = _projects.save_artifact(
        body.get("project"), body.get("kind"), body.get("name"), body.get("payload")
    )
    if saved is None:
        return JsonResponse({"error": "not saved"}, status=403)
    return JsonResponse(saved, status=201)


# EOF
