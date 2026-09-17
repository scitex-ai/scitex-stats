#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone project provider + the project-default file contract.

The Statistics app is project-scoped (manifest ``"scope": "project"``), so it
renders the picker itself and asks a PROVIDER for the projects. In the hub the
host registers its own provider through ``SCITEX_PROJECT_PROVIDER`` /
``SCITEX_PROJECT_PROVIDER_URL`` and OWNS authorization — every call here is
request-aware so a host provider can answer per caller. Standalone has no host
provider, so :class:`StandaloneProjectProvider` lists local folders.

Filesystem rules, all enforced on DESCRIPTORS rather than paths:

* a project id the provider does not list for THIS request has no directory at
  all (fail-closed, and the provider is asked with the request);
* names are single components from a strict ASCII pattern — no separators, no
  dots-only, bounded length;
* children are opened ``O_NOFOLLOW`` relative to the project directory's file
  descriptor, so a symlink cannot smuggle a read or write out of the project
  (and there is no resolve-then-open window to race: the descriptor is the
  anchor, not a path string);
* writes go to a hidden temp file in the TARGET directory and are moved into
  place with ``os.replace`` — atomic, same directory — and never overwrite: an
  existing artifact gets the next free ``.vN`` suffix instead.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# Strict per-kind write policy: which extension each kind may carry, and its
# size cap. A kind is not a free-form string — it selects one of these rows, so
# "results" can never be written as an .html or an unbounded blob.
KIND_POLICY: Dict[str, Dict[str, int]] = {
    "results": {".json": 2 * 1024 * 1024},
    "provenance": {".json": 2 * 1024 * 1024},
    "config": {".json": 1 * 1024 * 1024},
    "plots": {".png": 8 * 1024 * 1024, ".svg": 8 * 1024 * 1024, ".json": 2 * 1024 * 1024},
}
SAVE_KINDS = tuple(KIND_POLICY)
ARTIFACT_DIR = "stats"

# One path component: starts alphanumeric, then alphanumerics/._-, max 64 chars.
# No separators, no leading dot, no "..", no NUL — and the same pattern is used
# for reads and writes, so a name accepted once is accepted everywhere.
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# The app's own "stateless" switch. Absence of ?project= is NOT enough to
# mean Quick analysis: the SDK precedence resumes the LAST VISITED project in
# that case, so a page the user believes stateless would still resolve a
# project server-side and accept writes. `?quick=1` says it explicitly.
QUICK_PARAM = "quick"
TRUTHY = ("1", "true", "yes", "on")


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
    """The provider this REQUEST must ask: the HOST's, else the local one.

    The hub owns project scope and authorization; asking the local folder root
    in a hub mount would read a directory the host never authorized. The
    request is threaded through every call so a host provider can decide per
    caller (its ``list_projects(request)`` is the authorization).
    """
    from scitex_ui.project_scope import host_project_provider

    host = host_project_provider()
    return host if host is not None else StandaloneProjectProvider()


def current_project_id(request: Any) -> Optional[str]:
    """The project this request resolves to, or ``None`` so the picker shows.

    ``resolve_project`` implements the precedence but does NOT read the request
    itself, so the caller hands it the explicit pick: the picker navigates with
    ``?project=<id>`` (the SDK's own ``data-navigate`` default). No project means
    STATELESS: Quick analysis is exactly this state, which is why persistence is
    refused when it is absent.
    """
    getter = getattr(request, "GET", None)
    if getter is not None and str(getter.get(QUICK_PARAM) or "").strip().lower() in TRUTHY:
        # Stateless, explicitly: no project is resolved even if one was visited.
        return None
    explicit = (getter.get(PROJECT_QUERY_PARAM) or "").strip() if getter is not None else ""
    return resolve_project(request, provider(request), explicit=explicit or None)


def authorized_project(project_id: Optional[str], request: Any = None) -> Optional[Any]:
    """The provider's entry for ``project_id``, or ``None``.

    The listing is asked WITH the request, so a host provider that filters by
    caller answers for that caller only. An id it does not list has no entry
    here, and therefore no directory: callers cannot fall back to the stored
    project.
    """
    if not project_id:
        return None
    for entry in provider(request).list_projects(request):
        if entry.id == project_id:
            return entry
    return None


def is_safe_name(name: Optional[str]) -> bool:
    """True for a single, strict path component (the only shape we ever open)."""
    return bool(name) and bool(SAFE_NAME.match(str(name)))


def _project_dir_fd(project_id: Optional[str], request: Any = None) -> Optional[int]:
    """An O_DIRECTORY descriptor for the authorized project, or ``None``.

    The descriptor — not a path string — is what every later operation is
    anchored to, which is what removes the resolve-then-open race: once this fd
    exists, a name can only ever resolve inside this directory.
    """
    entry = authorized_project(project_id, request)
    if entry is None:
        return None
    detail = str(getattr(entry, "detail", "") or "").strip()
    if not detail:
        return None
    path = Path(detail)
    if isinstance(provider(request), LocalProjectProvider):
        # The local provider promises to stay inside its own root, so that is
        # the containment we enforce. A HOST provider is the authority for its
        # entries (the hub may hand out a path outside any local root).
        root = projects_root().resolve()
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            return None
        path = resolved
    try:
        return os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return None


def _open_child_dir(parent_fd: int, name: str, create: bool = False) -> Optional[int]:
    """O_DIRECTORY|O_NOFOLLOW descriptor for a single child directory."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if create:
        try:
            os.mkdir(name, dir_fd=parent_fd)
        except FileExistsError:
            pass
        except OSError:
            return None
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError:
        return None


def _next_free_name(dir_fd: int, name: str) -> str:
    """``name`` if free, else ``<stem>.v2<ext>``, ``<stem>.v3<ext>``, …

    Artifacts are never overwritten silently: the caller is told which path was
    written, so a second save cannot destroy the first one's evidence.
    """
    stem, ext = os.path.splitext(name)
    candidate = name
    version = 1
    while True:
        try:
            os.stat(candidate, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            return candidate
        except OSError:
            return candidate
        version += 1
        candidate = f"{stem}.v{version}{ext}"


def list_data_files(project_id: Optional[str], request: Any = None) -> Optional[List[Dict[str, Any]]]:
    """The project's authorized CSV/TSV files, or ``None`` when not authorized."""
    dir_fd = _project_dir_fd(project_id, request)
    if dir_fd is None:
        return None
    try:
        names = os.listdir(dir_fd)
    except OSError:
        return None
    finally:
        os.close(dir_fd)

    files = []
    for name in sorted(names, key=str.lower):
        if not is_safe_name(name) or os.path.splitext(name)[1].lower() not in DATA_EXTENSIONS:
            continue
        dir_fd = _project_dir_fd(project_id, request)
        if dir_fd is None:
            return None
        try:
            # follow_symlinks=False + S_ISREG: a symlink is not a data file.
            info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except OSError:
            continue
        finally:
            os.close(dir_fd)
        if not stat.S_ISREG(info.st_mode):
            continue
        files.append(
            {
                "name": name,
                "size": info.st_size,
                "modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(info.st_mtime)),
            }
        )
    return files


def read_data_file(project_id: Optional[str], name: str, request: Any = None) -> Optional[str]:
    """The text of one authorized project data file, or ``None``.

    ``None`` covers every refusal (unknown/unauthorized project, unsafe name,
    wrong format, symlink, missing, oversized) so a caller cannot tell "not
    authorized" from "not there" — the same information a hostile caller wants.
    """
    if not is_safe_name(name) or os.path.splitext(str(name))[1].lower() not in DATA_EXTENSIONS:
        return None
    dir_fd = _project_dir_fd(project_id, request)
    if dir_fd is None:
        return None
    try:
        # O_NOFOLLOW: a symlinked name is refused outright rather than followed.
        file_fd = os.open(str(name), os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    except OSError:
        return None
    finally:
        os.close(dir_fd)
    try:
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_IMPORT_BYTES:
            return None
        chunks = []
        while True:
            chunk = os.read(file_fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
    except OSError:
        return None
    finally:
        os.close(file_fd)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _write_bytes(dir_fd: int, name: str, payload: bytes) -> Optional[str]:
    """Atomically write ``payload`` into ``dir_fd`` under a never-used name."""
    target = _next_free_name(dir_fd, name)
    temp = f".{target}.tmp.{os.getpid()}"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    except OSError:
        return None
    try:
        os.write(fd, payload)
        os.fsync(fd)
    except OSError:
        os.close(fd)
        try:
            os.unlink(temp, dir_fd=dir_fd)
        except OSError:
            pass
        return None
    os.close(fd)
    try:
        # Same directory, so the move is atomic: readers see the old name or the
        # complete new file, never a half-written artifact.
        os.replace(temp, target, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    except OSError:
        try:
            os.unlink(temp, dir_fd=dir_fd)
        except OSError:
            pass
        return None
    return target


def save_artifact(
    project_id: Optional[str],
    kind: str,
    name: str,
    payload: Any,
    payload_base64: Optional[str] = None,
    request: Any = None,
) -> Optional[Dict[str, Any]]:
    """Write one artifact into ``<project>/stats/<kind>/`` and describe it.

    Returns ``None`` for every refusal: unauthorized project (including "no
    active project", which is the stateless Quick analysis state), unknown kind,
    a name or extension outside that kind's policy, invalid base64, or a payload
    over the kind's cap. A successful write keeps the bytes it validated — the
    same ``payload`` is encoded once and written atomically.
    """
    policy = KIND_POLICY.get(str(kind))
    if policy is None or not is_safe_name(name):
        return None
    safe_name = str(name)
    extension = os.path.splitext(safe_name)[1].lower()
    cap = policy.get(extension)
    if cap is None:
        return None

    if payload_base64 is not None:
        try:
            body = base64.b64decode(payload_base64, validate=True)
        except (binascii.Error, ValueError):
            return None
    else:
        text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True, default=str)
        body = text.encode("utf-8")
    if len(body) > cap:
        return None

    dir_fd = _project_dir_fd(project_id, request)
    if dir_fd is None:
        return None
    try:
        artifact_fd = _open_child_dir(dir_fd, ARTIFACT_DIR, create=True)
        if artifact_fd is None:
            return None
        try:
            kind_fd = _open_child_dir(artifact_fd, str(kind), create=True)
        finally:
            os.close(artifact_fd)
        if kind_fd is None:
            return None
        try:
            written = _write_bytes(kind_fd, safe_name, body)
        finally:
            os.close(kind_fd)
    finally:
        os.close(dir_fd)
    if written is None:
        return None
    return {
        "project": project_id,
        "kind": kind,
        "name": written,
        "path": f"{ARTIFACT_DIR}/{kind}/{written}",
        "bytes": len(body),
    }


# EOF
