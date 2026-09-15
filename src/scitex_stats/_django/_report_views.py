#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report endpoints: build the bundled PDF, download it, or save it to the host's Files.

Saving goes through a host service: ``settings.SCITEX_APP_SAVE_TO_FILES`` (a
dotted path to ``save(user, filename, data) -> Path``), defaulting to the
hub's Files ``save_to_downloads``. Standalone (no such service) the Save
button stays hidden and the endpoint answers 501.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

HUB_SAVE_TO_FILES = "apps.workspace.files_app.services.save_to_downloads"
HUB_USER_ROOT = "apps.workspace.files_app.services.user_root"
MAX_VALUES = 100_000


def _import(path: Optional[str]) -> Optional[Callable]:
    if not path:
        return None
    try:
        return import_string(path)
    except (ImportError, AttributeError):
        return None


def files_saver() -> Optional[Callable]:
    return _import(getattr(settings, "SCITEX_APP_SAVE_TO_FILES", None) or HUB_SAVE_TO_FILES)


def _pdf_available() -> bool:
    from scitex_stats.reporting._pdf import pdf_renderer

    return pdf_renderer() is not None


def _payload(request) -> Tuple[Optional[Dict[str, Any]], Optional[JsonResponse]]:
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"error": _("Invalid request body.")}, status=400)
    groups = body.get("groups")
    if not isinstance(groups, list) or len([g for g in groups if g]) < 2:
        return None, JsonResponse({"error": _("A report needs at least two groups of numbers.")}, status=400)
    if sum(len(g) for g in groups if isinstance(g, list)) > MAX_VALUES:
        return None, JsonResponse({"error": _("Too many values for a report.")}, status=413)
    return body, None


def _build_pdf(body: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
    from scitex_stats.reporting._pdf import report

    names = body.get("group_names")
    groups = body["groups"]
    data = dict(zip([str(n) for n in names], groups)) if isinstance(names, list) and len(names) == len(groups) else groups
    design = "within" if body.get("design") in ("within", "paired") else "between"
    posthoc = body.get("posthoc") if body.get("posthoc") in ("auto", "always", "never") else "auto"
    result = report(data, design, None, formats=("pdf",), posthoc=posthoc,
                    title=str(body.get("title") or "Statistical report")[:120])
    return result["pdf_bytes"], result["summary"]


def _filename() -> str:
    return f"stats-report_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')}.pdf"


@require_GET
def report_capabilities(request):
    authed = bool(getattr(getattr(request, "user", None), "is_authenticated", False))
    return JsonResponse({"pdf": _pdf_available(), "save_to_files": files_saver() is not None and authed})


@csrf_exempt  # stateless: builds a document from the posted numbers, stores nothing
@require_POST
def report_pdf(request):
    """The bundled report as a PDF download."""
    body, error = _payload(request)
    if error:
        return error
    try:
        data, summary = _build_pdf(body)
    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{_filename()}"'
    response["X-Report-Primary-Test"] = summary["primary_test"]
    return response


@require_POST
def report_save(request):
    """Build the report and save it to the signed-in user's Files (Downloads)."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return JsonResponse({"error": _("Sign in to save to Files.")}, status=401)
    save = files_saver()
    if save is None:
        return JsonResponse({"error": _("Saving to Files is not available here.")}, status=501)
    body, error = _payload(request)
    if error:
        return error
    try:
        data, _summary = _build_pdf(body)
    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    saved = save(user, _filename(), data)
    user_root = _import(getattr(settings, "SCITEX_APP_FILES_USER_ROOT", None) or HUB_USER_ROOT)
    try:
        rel = saved.relative_to(user_root(user)).as_posix() if user_root else saved.name
    except (ValueError, AttributeError):
        rel = getattr(saved, "name", str(saved))
    return JsonResponse({"saved": rel, "files_url": getattr(settings, "SCITEX_APP_FILES_URL", "/apps/files/")})


# EOF
