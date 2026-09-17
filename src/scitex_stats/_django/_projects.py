#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone project provider + the project-default file contract.

The Statistics app is project-scoped (manifest ``"scope": "project"``), so it
renders the picker itself and asks a PROVIDER for the projects. In the hub the
host registers its own provider through ``SCITEX_PROJECT_PROVIDER`` /
``SCITEX_PROJECT_PROVIDER_URL``; standalone there is no host, so this module
offers the SDK's :class:`LocalProjectProvider` over a local projects root —
every non-hidden folder under it is a project.

Everything that touches the filesystem is FAIL-CLOSED on the same rule: a
project id the provider does not list is never resolved to a path, and a file
name only ever names a direct child of the authorized project directory
(``..``, absolute paths and symlinks that escape are refused). Statistics work
in progress is written under ``<project>/stats/<kind>/`` so a project's data
stays distinguishable from the app's outputs.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from scitex_ui.project_scope import (
    PROJECT_QUERY_PARAM,
    LocalProjectProvider,
    resolve_project,
)

# Where standalone looks for projects. Overridable so tests — and users whose
# data lives elsewhere — do not have to write into $HOME.
ROOT_ENV = "SCITEX_STATS_PROJECTS_ROOT"
DEFAULT_ROOT = Path.home() / ".scitex" / "stats" / "projects"

# Project-default mode accepts exactly the formats the app can analyse.
DATA_EXTENSIONS = (".csv", ".tsv")
# One import must stay a browser-sized payload; larger files are refused with a
# legible error rather than half-loaded.
MAX_IMPORT_BYTES = 5 * 1024 * 1024
# Same ceiling for what we write back — a rendered plot or a result bundle.
MAX_ARTIFACT_BYTES = 5 * 1024 * 1024
# What the app writes back into the project.
SAVE_KINDS = ("config", "results", "plots", "provenance")
UNSAFE_NAME_CHARS = ("/", "\\", "\x00")


def projects_root() -> Path:
    """The standalone projects root (``SCITEX_STATS_PROJECTS_ROOT``, else the default)."""
    configured = os.environ.get(ROOT_ENV, "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_ROOT


class StandaloneProjectProvider(LocalProjectProvider):
    """The local-folder provider, reading the projects root when CONSTRUCTED.

    A CLASS, not a factory function, because ``host_project_provider()``
    resolves ``SCITEX_PROJECT_PROVIDER`` by importing the dotted path and
    treats anything that is not a class as an already-built instance — handing
    it a function silently produced an object that is not a provider at all
    (caught by the standalone-shell test, which renders through the real
    settings module).
    """

    def __init__(self) -> None:
        super().__init__(projects_root())


def provider(request: Any = None) -> Any:
    """The provider this request must ask: the HOST's, else the local one.

    The hub OWNS project scope: it mounts this app and registers its provider
    through ``SCITEX_PROJECT_PROVIDER`` (optionally with an HTTP endpoint behind
    ``SCITEX_PROJECT_PROVIDER_URL``). Asking the local folder root in a hub mount
    would bypass the host's authority entirely — the file listing, import and
    save routes would read a directory the host never authorized. So every route
    asks the SAME provider the picker gets its options from, and standalone (no
    host provider registered) falls back to the local root.
    """
    from scitex_ui.project_scope import host_project_provider

    host = host_project_provider()
    return host if host is not None else StandaloneProjectProvider()


def current_project_id(request: Any) -> Optional[str]:
    """The project this request resolves to, or ``None`` so the picker shows.

    ``resolve_project`` implements the precedence but does NOT read the request
    itself, so the caller must hand it the explicit pick: the picker navigates
    with ``?project=<id>`` (the SDK's own ``data-navigate`` default).
    """
    getter = getattr(request, "GET", None)
    explicit = (getter.get(PROJECT_QUERY_PARAM) or "").strip() if getter is not None else ""
    return resolve_project(request, provider(), explicit=explicit or None)


def authorized_project(project_id: Optional[str]) -> Optional[Any]:
    """The provider's entry for ``project_id``, or ``None``.

    Fail-closed by construction: an id that is not in the provider's listing
    (unknown, revoked, someone else's) has no path here at all, so callers
    cannot accidentally fall back to the stored project.
    """
    if not project_id:
        return None
    for entry in provider().list_projects():
        if entry.id == project_id:
            return entry
    return None


def project_dir(project_id: Optional[str]) -> Optional[Path]:
    """The authorized directory of ``project_id``, or ``None``.

    The containment check is applied to the LOCAL provider's own root, because
    that is the root it promises to stay inside. A host provider is the
    authority for its own entries (the hub may hand out a path on a NAS, not
    under any local root), so its detail is taken as given — while an entry with
    NO filesystem detail is refused rather than guessed at.
    """
    entry = authorized_project(project_id)
    if entry is None:
        return None
    detail = str(getattr(entry, "detail", "") or "").strip()
    if not detail:
        return None
    candidate = Path(detail).resolve()
    if isinstance(provider(), LocalProjectProvider):
        root = projects_root().resolve()
        if candidate != root and root not in candidate.parents:
            return None
    return candidate if candidate.is_dir() else None


def _safe_child(base: Path, name: str) -> Optional[Path]:
    """``base/name`` when ``name`` is a plain child of ``base``, else ``None``.

    Refuses traversal, absolute paths and NUL, then re-checks the RESOLVED path
    so a symlink pointing outside the project cannot smuggle a read or write.
    """
    if not name or any(char in name for char in UNSAFE_NAME_CHARS):
        return None
    if name in (".", ".."):
        return None
    resolved_base = base.resolve()
    candidate = (resolved_base / name).resolve()
    if resolved_base not in candidate.parents:
        return None
    return candidate


def list_data_files(project_id: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """The project's authorized CSV/TSV files, or ``None`` when not authorized."""
    base = project_dir(project_id)
    if base is None:
        return None
    files = []
    for path in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if path.is_file() and path.suffix.lower() in DATA_EXTENSIONS:
            stat = path.stat()
            files.append(
                {"name": path.name, "size": stat.st_size, "modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime))}
            )
    return files


def read_data_file(project_id: Optional[str], name: str) -> Optional[str]:
    """The text of one authorized project data file, or ``None``.

    ``None`` covers every refusal (unknown project, traversal, wrong format,
    missing, oversized) so a caller cannot tell "not authorized" from "not
    there" — the same information a hostile caller would want.
    """
    base = project_dir(project_id)
    if base is None:
        return None
    path = _safe_child(base, name)
    if path is None or not path.is_file() or path.suffix.lower() not in DATA_EXTENSIONS:
        return None
    if path.stat().st_size > MAX_IMPORT_BYTES:
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def save_artifact(
    project_id: Optional[str],
    kind: str,
    name: str,
    payload: Any,
    payload_base64: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Write one artifact into ``<project>/stats/<kind>/`` and describe it.

    Returns ``None`` for every refusal (unknown project, unknown kind, unsafe
    name, invalid base64, oversized binary). ``payload_base64`` writes the
    decoded BYTES — that is how a rendered plot (PNG/SVG) is stored; otherwise
    the payload is written as JSON when it is not already a string.
    """
    base = project_dir(project_id)
    if base is None or kind not in SAVE_KINDS:
        return None
    safe_name = _safe_child(base, name)
    if safe_name is None or safe_name.name != name:
        return None
    target_dir = base / "stats" / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _safe_child(target_dir, name)
    if target is None:
        return None
    if payload_base64 is not None:
        try:
            binary = base64.b64decode(payload_base64, validate=True)
        except (binascii.Error, ValueError):
            return None
        if len(binary) > MAX_ARTIFACT_BYTES:
            return None
        target.write_bytes(binary)
    else:
        text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True, default=str)
        if len(text.encode("utf-8")) > MAX_ARTIFACT_BYTES:
            return None
        target.write_text(text, encoding="utf-8")
    return {
        "project": project_id,
        "kind": kind,
        "name": name,
        "path": str(target.relative_to(base)),
        "bytes": target.stat().st_size,
    }


# EOF
