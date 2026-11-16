#!/usr/bin/env python3
# File: src/scitex_stats/_runtime_paths.py

"""Runtime path resolver for scitex-stats.

Writable state (cache, db, generated outputs, etc.) lives under
``~/.scitex/stats/runtime/<sub>/`` rather than ``~/.scitex/stats/<sub>/``.
Config files (e.g. ``~/.scitex/stats/config.yaml``) stay at the top level.

A one-shot migration moves legacy ``~/.scitex/stats/<sub>/`` subdirs to
``~/.scitex/stats/runtime/<sub>/`` on first import (called from
``scitex_stats/__init__.py``).
"""

from __future__ import annotations

from pathlib import Path

SCITEX_HOME = Path.home() / ".scitex"
STATS_HOME = SCITEX_HOME / "stats"
STATS_RUNTIME = STATS_HOME / "runtime"

# Names that should live under runtime/ when found at ~/.scitex/stats/<name>/.
RUNTIME_SUBDIRS = ("cache", "db", "workspace", "completion", "outputs", "logs")


def migrate_runtime_dirs() -> None:
    """One-shot move of legacy ``~/.scitex/stats/<sub>/`` to ``runtime/<sub>/``.

    Safe to call multiple times: only moves a subdir if the OLD path
    exists and the NEW path does not. Silently swallows every error so
    package import never breaks on a permission / filesystem hiccup.
    """
    try:
        if not STATS_HOME.exists():
            return
        for name in RUNTIME_SUBDIRS:
            old = STATS_HOME / name
            new = STATS_RUNTIME / name
            if old.exists() and not new.exists():
                STATS_RUNTIME.mkdir(parents=True, exist_ok=True)
                old.rename(new)
    except Exception:
        pass


def runtime_path(*parts: str) -> Path:
    """Resolve a runtime path under ``~/.scitex/stats/runtime/<parts...>/``.

    Public helper for downstream submodules that need to write cache/db/
    generated outputs. Always returns a path inside the ``runtime/`` tree.
    The parent directory is created on demand. Paths escaping the resolved
    runtime root raise ValueError before directories are created. Symlinks
    whose resolved targets remain within that root are supported. This
    validation does not lock paths against concurrent filesystem changes.

    Examples
    --------
    >>> runtime_path("cache", "demo.db")
    PosixPath('/home/.../.scitex/stats/runtime/cache/demo.db')
    """
    p = STATS_RUNTIME.joinpath(*parts)
    # Follow existing symlinks when validating, including a symlinked root.
    # Validate before mkdir so a rejected path cannot create outside parents.
    try:
        p.resolve().relative_to(STATS_RUNTIME.resolve())
    except ValueError as error:
        raise ValueError("Path must remain inside the stats runtime directory") from error
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
