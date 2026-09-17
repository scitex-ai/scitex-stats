#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone project provider for the shared header picker.

The Statistics app is project-scoped (manifest ``"scope": "project"``), so it
renders the picker itself and asks a PROVIDER for the projects. In the hub the
host registers its own provider through ``SCITEX_PROJECT_PROVIDER`` /
``SCITEX_PROJECT_PROVIDER_URL``; standalone there is no host, so this module
offers the SDK's :class:`LocalProjectProvider` over a local projects root —
every non-hidden folder under it is a project.

Nothing here decides permissions: the picker's HTTP contract
(:func:`scitex_ui.project_scope.project_listing_view`) fails closed — a project
the provider does not list is refused, it never silently falls back to a stored
one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from scitex_ui.project_scope import LocalProjectProvider, resolve_project

# Where standalone looks for projects. Overridable so tests — and users whose
# data lives elsewhere — do not have to write into $HOME.
ROOT_ENV = "SCITEX_STATS_PROJECTS_ROOT"
DEFAULT_ROOT = Path.home() / ".scitex" / "stats" / "projects"


def projects_root() -> Path:
    """The standalone projects root (``SCITEX_STATS_PROJECTS_ROOT``, else the default)."""
    configured = os.environ.get(ROOT_ENV, "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_ROOT


def provider(request: Any = None) -> LocalProjectProvider:
    """Build the standalone provider (a factory: the SDK setting takes a callable)."""
    return LocalProjectProvider(projects_root())


def current_project_id(request: Any) -> Optional[str]:
    """The project this request resolves to, or ``None`` so the picker shows."""
    return resolve_project(request, provider())


# EOF
