#!/usr/bin/env python3
# File: tests/scitex_stats/test__runtime_paths.py

"""Sanity tests for the runtime-separation path resolver.

Mirrors ``src/scitex_stats/_runtime_paths.py``. Each test covers exactly
one observable contract of the path-resolver convention.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_runtime_path_is_exposed_at_package_level():
    # Arrange
    import scitex_stats

    # Act
    fn = getattr(scitex_stats, "_runtime_path", None)

    # Assert
    assert callable(fn)


def test_runtime_path_returns_pathlib_path():
    # Arrange
    from scitex_stats._runtime_paths import runtime_path

    # Act
    p = runtime_path("cache", "demo.db")

    # Assert
    assert isinstance(p, Path)


def test_runtime_path_lives_under_scitex_stats_runtime_dir():
    # Arrange
    from scitex_stats._runtime_paths import runtime_path

    expected_prefix = Path.home() / ".scitex" / "stats" / "runtime"

    # Act
    p = runtime_path("cache", "demo.db")

    # Assert
    assert str(p).startswith(str(expected_prefix))


def test_runtime_path_preserves_trailing_filename():
    # Arrange
    from scitex_stats._runtime_paths import runtime_path

    # Act
    p = runtime_path("cache", "demo.db")

    # Assert
    assert p.name == "demo.db"


def test_runtime_path_preserves_intermediate_subdir():
    # Arrange
    from scitex_stats._runtime_paths import runtime_path

    # Act
    p = runtime_path("cache", "demo.db")

    # Assert
    assert p.parent.name == "cache"


def test_migrate_runtime_dirs_moves_legacy_subdir_to_runtime(tmp_path):
    # Arrange: run the migration in a subprocess with HOME=tmp_path so the
    # real ``~/.scitex/stats/`` is never touched. Real env var, real
    # filesystem state — no monkeypatching of production internals.
    legacy = tmp_path / ".scitex" / "stats" / "cache"
    legacy.mkdir(parents=True)
    (legacy / "marker.txt").write_text("legacy")
    env = {**os.environ, "HOME": str(tmp_path)}

    # Act
    subprocess.run(
        [sys.executable, "-c", "import scitex_stats"],
        env=env,
        check=True,
    )

    # Assert
    moved = tmp_path / ".scitex" / "stats" / "runtime" / "cache" / "marker.txt"
    assert moved.read_text() == "legacy"


def test_migrate_runtime_dirs_is_idempotent(tmp_path):
    # Arrange: HOME with the post-migration layout already in place;
    # a second import must leave the runtime/ tree untouched.
    runtime_cache = tmp_path / ".scitex" / "stats" / "runtime" / "cache"
    runtime_cache.mkdir(parents=True)
    (runtime_cache / "marker.txt").write_text("already-migrated")
    env = {**os.environ, "HOME": str(tmp_path)}

    # Act
    subprocess.run(
        [sys.executable, "-c", "import scitex_stats; import scitex_stats"],
        env=env,
        check=True,
    )

    # Assert
    assert (runtime_cache / "marker.txt").read_text() == "already-migrated"


def _runtime_child(home, parts):
    """Use the real environment reader in an isolated child, without patching it."""
    code = """import json,sys
from scitex_stats import _runtime_path
try:
 p=_runtime_path(*json.loads(sys.argv[1]))
 print(json.dumps({'path':str(p),'resolved':str(p.resolve()),'parent_exists':p.parent.is_dir(),'path_exists':p.exists()}))
except Exception as error:
 print(json.dumps({'exception_type':type(error).__name__,'error':str(error)}))
"""
    env = {**os.environ, "HOME": str(home), "SCITEX_DIR": str(home / ".scitex")}
    result = subprocess.run(
        [sys.executable, "-c", code, json.dumps(parts)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@pytest.fixture(params=["absolute", "traversal", "parent_symlink", "file_symlink"])
def escaping_runtime_case(tmp_path, request):
    home = tmp_path / "home"
    home.mkdir()
    root = home / ".scitex/stats/runtime"
    root.mkdir(parents=True)
    outside = root.parent / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_bytes(b"preserve outside marker\n")
    mode = request.param
    if mode == "absolute":
        parts = [str(outside / "new/result.txt")]
    elif mode == "traversal":
        parts = ["..", "outside", "new", "result.txt"]
    elif mode == "parent_symlink":
        (root / "linked").symlink_to(outside, target_is_directory=True)
        parts = ["linked", "new", "result.txt"]
    else:
        (root / "linked").symlink_to(marker)
        parts = ["linked"]
    return home, parts, outside, marker


def test_escaping_paths_fail_before_outside_mutation(escaping_runtime_case):
    # Arrange
    home, parts, outside, marker = escaping_runtime_case
    # Act
    result = _runtime_child(home, parts)
    # Assert
    assert (
        result.get("exception_type"),
        sorted(p.name for p in outside.iterdir()),
        marker.read_bytes(),
    ) == ("ValueError", ["keep.txt"], b"preserve outside marker\n")


def test_nested_paths_keep_shape_and_create_parent(tmp_path):
    # Arrange
    expected = tmp_path / ".scitex/stats/runtime/cache/nested/result.txt"
    # Act
    result = _runtime_child(tmp_path, ["cache", "nested", "result.txt"])
    # Assert
    assert result == {
        "path": str(expected),
        "resolved": str(expected.resolve()),
        "parent_exists": True,
        "path_exists": False,
    }


def test_symlinked_runtime_root_remains_supported(tmp_path):
    # Arrange
    root = tmp_path / ".scitex/stats/runtime"
    root.parent.mkdir(parents=True)
    target = tmp_path / "configured-storage"
    target.mkdir()
    root.symlink_to(target, target_is_directory=True)
    # Act
    result = _runtime_child(tmp_path, ["cache", "result.txt"])
    # Assert
    assert result == {
        "path": str(root / "cache/result.txt"),
        "resolved": str(target / "cache/result.txt"),
        "parent_exists": True,
        "path_exists": False,
    }


def test_internal_directory_alias_remains_supported(tmp_path):
    # Arrange
    root = tmp_path / ".scitex/stats/runtime"
    (root / "actual").mkdir(parents=True)
    (root / "alias").symlink_to(root / "actual", target_is_directory=True)
    # Act
    result = _runtime_child(tmp_path, ["alias", "nested", "result.txt"])
    # Assert
    assert result == {
        "path": str(root / "alias/nested/result.txt"),
        "resolved": str(root / "actual/nested/result.txt"),
        "parent_exists": True,
        "path_exists": False,
    }
