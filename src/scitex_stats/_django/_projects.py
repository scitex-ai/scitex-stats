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
* project roots are opened from their TRUSTED PARENT with ``O_NOFOLLOW``, so an
  authorized root that is itself a symlink is refused instead of crossing into
  another project;
* children are opened ``O_NOFOLLOW`` relative to the project directory's file
  descriptor, so a symlink cannot smuggle a read or write out of the project
  (and there is no resolve-then-open window to race: the descriptor is the
  anchor, not a path string);
* writes reserve the artifact name with ``os.link`` — which fails rather than
  overwrites — after the bytes are complete, so two writers racing for the same
  name cannot both report it, neither loses its payload, and no reader ever sees
  a partial artifact. An existing artifact takes the next free ``.vN`` suffix;
* the bytes have to BE what the extension promises (JSON parses, PNG has the PNG
  magic, SVG starts as XML), because a name is a promise later readers trust.

Where a project's files live is asked of an explicit, request-aware STORAGE
capability — never ``ProjectEntry.detail``, which the SDK defines as display
metadata (the hub puts the owner's username there, not a path).
"""

from __future__ import annotations

import base64
import binascii
import itertools
import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

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
# The bound is on the FINAL name, and every save reserves room for a version
# suffix: a 64-character name is fine for the first save and then has nowhere to
# go, which would silently lose the second save's payload. So the base name must
# leave room for ".vNNN".
MAX_NAME = 64
VERSION_ROOM = len(".v999")

# The host registers where its projects' files live — and who may write them —
# through this setting (a dotted path to a request-aware storage capability).
STORAGE_SETTING = "SCITEX_PROJECT_STORAGE"

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


@runtime_checkable
class ProjectStorage(Protocol):
    """Where an authorized project's files live, and whether THIS request may write.

    A separate capability from :class:`ProjectProvider`, because the provider's
    entries are a *listing*: the hub lists read-only collaborators too, and its
    ``ProjectEntry.detail`` is display metadata (the owner's username), not a
    path. Reading either as a filesystem path fails or resolves an unrelated
    directory that merely shares the project's name.
    """

    def project_path(self, project_id: str, request: Any) -> Optional[Path]:
        """The project's storage root, or ``None`` when this request has none."""
        ...

    def can_write(self, project_id: str, request: Any) -> bool:
        """True when this request may WRITE into the project — read is not write."""
        ...


class StandaloneProjectStorage:
    """Local folders: the project is ``<root>/<id>`` and the local user owns it.

    The path is returned UNRESOLVED on purpose: the root open is what refuses a
    symlinked project directory (``O_NOFOLLOW``), and containment comes from the
    id being a single safe component. Resolving here would follow exactly the
    link the root open exists to refuse.
    """

    def project_path(self, project_id: str, request: Any = None) -> Optional[Path]:
        if not is_safe_name(project_id):
            return None
        return projects_root() / str(project_id)

    def can_write(self, project_id: str, request: Any = None) -> bool:
        return True


class NoHostStorage:
    """A host is installed but supplied no usable storage: refuse everything.

    Falling back to the standalone local root here is exactly what a hostile
    setup wants: a host that lists one read-only project would otherwise resolve
    to a same-named, WRITABLE folder under ``SCITEX_STATS_PROJECTS_ROOT``.
    """

    def project_path(self, project_id: str, request: Any = None) -> Optional[str]:
        return None

    def can_write(self, project_id: str, request: Any = None) -> bool:
        return False


def _method_of(candidate: Any, name: str) -> Any:
    """The named callable on ``candidate``, or ``None``.

    ``getattr(obj, name, None)`` only swallows ``AttributeError``: a property or
    other descriptor that RAISES while being read propagates straight out of the
    inspection and becomes a 500. Inspection is not the place to discover that
    host code is broken — a raising descriptor means "not a capability".
    """
    try:
        attribute = getattr(candidate, name, None)
    except Exception:  # noqa: BLE001 - a hostile descriptor is a refusal, not a crash
        return None
    return attribute if callable(attribute) else None


def _is_capability(candidate: Any) -> bool:
    """True when ``candidate`` is a USABLE capability INSTANCE.

    Two traps this closes. ``isinstance`` against a runtime-checkable Protocol only
    proves the NAMES exist — an object whose ``can_write`` is the string
    ``"false"`` passes it and then explodes when called, so the methods must be
    callable. And a CLASS is not an instance: its methods are callable
    (unbound), so a class would pass too, and every call would then raise
    missing-``self``. Classes are instantiated by :func:`_capability`, never
    returned from here.
    """
    if isinstance(candidate, type):
        return False
    return all(_method_of(candidate, name) is not None for name in ("project_path", "can_write"))


def _capability(candidate: Any) -> Any:
    """Turn a registration into a storage capability, or ``None``.

    A dotted path may name a CLASS (the documented form) or an instance. A class
    must be instantiated FIRST — ``_is_capability`` would also match a class
    object, whose every call is then a missing-``self`` ``TypeError``. Exactly ONE
    factory hop is taken: a factory that returns another class is REJECTED rather
    than recursively instantiated, because each extra hop is another chance to end
    up holding something that is not the capability anyone registered.
    """
    if _is_capability(candidate):
        return candidate
    if isinstance(candidate, type) or callable(candidate):
        try:
            built = candidate()
        except Exception:  # noqa: BLE001 - a broken registration refuses, it never crashes a request
            return None
        return built if _is_capability(built) else None
    return None


def _capability_path(store: Any, project_id: Optional[str], request: Any) -> Optional[str]:
    """The path this capability gives for ``project_id``, or ``None``.

    A capability is host code: if it raises — or hands back something that only
    LOOKS like a path — the app refuses. ``os.fspath`` is guarded too, because a
    custom ``__fspath__`` is host code that can raise, and its result must be a
    ``str`` (a ``bytes`` path is not something this app will open).
    """
    method = _method_of(store, "project_path")
    if method is None:
        return None
    try:
        answer = method(str(project_id), request)
        if isinstance(answer, str):
            return answer
        if isinstance(answer, os.PathLike):
            resolved = os.fspath(answer)
            return resolved if isinstance(resolved, str) else None
    except Exception:  # noqa: BLE001 - a broken capability refuses; it does not 500 the app
        return None
    return None


def _capability_allows_write(store: Any, project_id: Optional[str], request: Any) -> bool:
    """True only for an explicit, literal ``True`` from the capability.

    ``bool(answer)`` is not enough: the string ``"false"`` is truthy, and it
    authorized a write to a read-only project before this check existed.
    """
    method = _method_of(store, "can_write")
    if method is None:
        return False
    try:
        answer = method(str(project_id), request)
    except Exception:  # noqa: BLE001 - same rule: a broken capability refuses
        return False
    return answer is True


def storage(request: Any = None) -> Any:
    """The request-aware storage capability: the host's, else the local one.

    With a HOST provider installed only the host may say where files are, and a
    missing or unusable host capability fails CLOSED (``NoHostStorage``) rather
    than falling through to local folders; a broken registration is treated the
    same way instead of crashing the request.
    """
    from django.conf import settings
    from django.utils.module_loading import import_string

    host = provider(request)
    fallback = NoHostStorage() if not isinstance(host, LocalProjectProvider) else StandaloneProjectStorage()

    dotted = str(getattr(settings, STORAGE_SETTING, "") or "").strip()
    if dotted:
        try:
            registered = import_string(dotted)
        except Exception:  # noqa: BLE001 - a broken registration refuses, never crashes a request
            return fallback
        return _capability(registered) or fallback

    if isinstance(host, LocalProjectProvider):
        return StandaloneProjectStorage()
    return _capability(host) or fallback


def can_write(project_id: Optional[str], request: Any = None) -> bool:
    """True only when the request resolves a project AND may write into it."""
    if not project_id or authorized_project(project_id, request) is None:
        return False
    return _capability_allows_write(storage(request), project_id, request)


def is_safe_name(name: Optional[str]) -> bool:
    """True for a single, strict path component (the only shape we ever open)."""
    return bool(name) and bool(SAFE_NAME.match(str(name)))


def _open_path_no_follow(path: str) -> Optional[int]:
    """Walk ``path`` from the filesystem root, opening EVERY component no-follow.

    Refusing only the final component left the ancestors: a replaced parent
    directory (a symlink) redirected the whole traversal into another project
    while every child check still passed. So the walk starts at ``/`` and no
    component is ever followed — a symlink at any level is a refusal.
    """
    components = [part for part in os.path.normpath(os.path.abspath(path)).split(os.sep) if part]
    try:
        current = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return None
    for component in components:
        try:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
        except OSError:
            os.close(current)
            return None
        os.close(current)
        current = nxt
    return current


def _project_dir_fd(project_id: Optional[str], request: Any = None) -> Optional[int]:
    """An O_DIRECTORY descriptor for the authorized project, or ``None``.

    The descriptor — not a path string — is what every later operation is
    anchored to, which is what removes the resolve-then-open race: once this fd
    exists, a name can only ever resolve inside this directory. The path comes
    from the storage CAPABILITY, never from the provider entry, and the walk to
    it refuses a symlink at any level.
    """
    entry = authorized_project(project_id, request)
    if entry is None:
        return None
    path = _capability_path(storage(request), project_id, request)
    if not path:
        return None
    return _open_path_no_follow(str(path))


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


def _candidates(name: str):
    """``name``, then ``<stem>.v2<ext>``, ``<stem>.v3<ext>``, … in order.

    Every candidate stays within the name bound because the base name already
    left ``VERSION_ROOM`` for the suffix (checked at the API boundary).
    """
    stem, ext = os.path.splitext(name)
    yield name
    for version in range(2, 1000):
        yield f"{stem}.v{version}{ext}"


def _unlink(name: str, dir_fd: int) -> None:
    try:
        os.unlink(name, dir_fd=dir_fd)
    except OSError:
        pass


def _svg_is_valid(body: bytes) -> bool:
    """An SVG must parse, be in the SVG namespace, and carry no DTD.

    A name is not a format: ``<svg-not-svg>bad</svg-not-svg>`` and
    ``<x:svg xmlns:x="urn:not-svg"/>`` both look like SVG and were accepted
    before. The root must be bare ``svg`` (HTML-style, no namespace) or
    ``{http://www.w3.org/2000/svg}svg`` — any OTHER namespace is a different
    document type wearing the same local name. A DOCTYPE/ENTITY declaration is the
    shape that makes an XML parser do more than read.
    """
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        return False
    from xml.etree import ElementTree

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return False
    return root.tag in ("svg", "{http://www.w3.org/2000/svg}svg")


def _content_is_wrong(extension: str, body: bytes) -> bool:
    """True when ``body`` is not the content its extension promises.

    A name is a promise every later reader trusts: a ``.json`` result that is not
    JSON, or a ``.png`` plot that is not a PNG, is a corrupt artifact wearing a
    valid name.
    """
    if extension == ".json":
        try:
            json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return True
        return False
    if extension == ".png":
        return not body.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".svg":
        return not _svg_is_valid(body)
    return False


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


# Temp names must be unique per WRITER, not per process: two threads saving the
# same artifact in one process would otherwise collide on the temp file itself
# (O_EXCL) and one of them would lose its payload.
_TEMP_COUNTER = itertools.count()


def _write_bytes(dir_fd: int, name: str, payload: bytes) -> Optional[str]:
    """Write ``payload`` under a never-used name, reserving that name atomically.

    The name is claimed with ``os.link``, which fails with ``EEXIST`` instead of
    overwriting, so two writers racing for the same artifact cannot both report
    it and neither loses its payload — the loser simply takes the next free
    version. The bytes are complete (and fsynced) before the name exists, so no
    reader ever sees a half-written artifact, and the temporary file never
    outlives the call.
    """
    temp = f".{name}.tmp.{os.getpid()}.{next(_TEMP_COUNTER)}"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    except OSError:
        return None
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    except OSError:
        os.close(fd)
        _unlink(temp, dir_fd)
        return None
    os.close(fd)

    for candidate in _candidates(name):
        try:
            os.link(temp, candidate, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        except FileExistsError:
            continue
        except OSError:
            break
        _unlink(temp, dir_fd)
        return candidate
    _unlink(temp, dir_fd)
    return None


def save_artifact(
    project_id: Optional[str],
    kind: str,
    name: str,
    payload: Any,
    payload_base64: Optional[str] = None,
    request: Any = None,
) -> Optional[Dict[str, Any]]:
    """Write one artifact into ``<project>/stats/<kind>/`` and describe it.

    Returns ``None`` for every refusal: no active project or a read-only one
    (the write capability is asked separately — the hub lists read-only
    collaborators too, so a listing is not write authority), unknown kind, a name
    or extension outside that kind's policy, a name with no room for the version
    suffix, invalid base64, a payload over the kind's cap, or bytes that are not
    what the extension promises. A successful write keeps the bytes it validated
    and reserves its name atomically.
    """
    policy = KIND_POLICY.get(str(kind))
    if policy is None or not is_safe_name(name):
        return None
    safe_name = str(name)
    if len(safe_name) + VERSION_ROOM > MAX_NAME:
        # Room for the version suffix is part of the policy: a name that cannot
        # be versioned would silently lose the SECOND save's payload.
        return None
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
    if len(body) > cap or _content_is_wrong(extension, body):
        return None

    if not can_write(project_id, request):
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
