"""Exercise the archive adapter's local refusal gates before public-core fetches."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11) or os.name != "posix",
    reason="release-image adapter requires POSIX and Python 3.11+",
)
ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / ".github/ci/release-identity.py"


def _capture_error(action):
    try:
        action()
    except (ValueError, OSError) as error:
        return error
    return None


@pytest.fixture
def identity():
    return runpy.run_path(str(ADAPTER))


@pytest.mark.parametrize(
    "change, message",
    [
        ({"commit": "bad-commit"}, "Malformed expected source or version"),
        ({"version": "v1.0.0"}, "Malformed expected source or version"),
        ({"commit": "0" * 40}, "Checkout and expected source differ"),
        ({"version": "9.9.9"}, "Expected version and Git project metadata differ"),
    ],
)
def test_identity_refuses_wrong_source_or_version(tmp_path, change, message):
    # Arrange
    import tomllib

    values = {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"],
    }
    values.update(change)
    # Act
    result = subprocess.run(
        [sys.executable, "-I", str(ADAPTER), "write-proof",
         "--commit", values["commit"], "--version", values["version"],
         "--dist", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=15,
    )
    # Assert
    assert (result.returncode != 0, message in result.stderr) == (True, True)


@pytest.mark.parametrize("members", [
    (),
    ("scitex_stats-{version}-py3-none-any.whl",),
    ("scitex_stats-{version}-py3-none-any.whl", "scitex_stats-{version}.tar.gz", "foreign.txt"),
    ("foreign-{version}-py3-none-any.whl", "scitex_stats-{version}.tar.gz"),
])
def test_identity_refuses_ambiguous_archive_set(identity, tmp_path, members):
    # Arrange
    import tomllib

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    for member in members:
        (tmp_path / member.format(version=version)).write_bytes(b"unreviewed input")
    # Act
    error = _capture_error(
        lambda: identity["artifact_proof"](tmp_path, commit, version, ROOT)
    )
    # Assert
    assert (isinstance(error, ValueError), "Expected exactly" in str(error)) == (True, True)


def test_identity_refuses_replaced_core_bytes(identity, tmp_path):
    # Arrange: complete names do not make unverified source executable.
    (tmp_path / "release_core").mkdir()
    for name in identity["CORE_FILES"]:
        (tmp_path / name).write_bytes(b"foreign core bytes")
    # Act
    error = _capture_error(lambda: identity["verified_core"](tmp_path))
    # Assert
    assert (isinstance(error, ValueError), "fixed commit" in str(error)) == (True, True)


def test_identity_refuses_extra_core_file(identity, tmp_path):
    # Arrange
    (tmp_path / "release_core").mkdir()
    for name in identity["CORE_FILES"]:
        (tmp_path / name).write_bytes(b"foreign core bytes")
    (tmp_path / "extra.py").write_bytes(b"foreign")
    # Act
    error = _capture_error(lambda: identity["verified_core"](tmp_path))
    # Assert
    assert (isinstance(error, ValueError), "closure" in str(error)) == (True, True)


def test_identity_refuses_symlink_inputs(identity, tmp_path):
    # Arrange
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"foreign": True}))
    link = tmp_path / "proof.json"
    link.symlink_to(target)
    # Act
    error = _capture_error(lambda: identity["regular"](link))
    # Assert
    assert isinstance(error, OSError)


def _source_preflight(tmp_path, commit_override=None, version_override=None):
    import tomllib

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    sentinel = tmp_path / "keep-existing-dist"
    sentinel.write_text("unchanged")
    result = subprocess.run(
        [sys.executable, "-I", str(ADAPTER), "verify-source",
         "--commit", commit_override or commit, "--version", version_override or version,
         "--dist", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=15,
    )
    preserved = (list(tmp_path.iterdir()) == [sentinel] and sentinel.read_text() == "unchanged")
    return result, preserved, commit, version


def test_source_preflight_accepts_identity_without_archives_or_core_fetch(tmp_path):
    # Arrange: tmp_path contains no archives.
    # Act: preflight checks the independently supplied source identity.
    result, preserved, commit, version = _source_preflight(tmp_path)
    # Assert
    assert (result.returncode, preserved, json.loads(result.stdout)) == (0, True, {
        "repository": "scitex-ai/scitex-stats", "commit": commit, "version": version,
    })


@pytest.mark.parametrize("commit_override, version_override", [
    ("0" * 40, None), (None, "9.9.9"),
])
def test_source_preflight_refuses_identity_without_touching_dist(
    tmp_path, commit_override, version_override,
):
    # Arrange: supply the mismatched caller identity.
    # Act
    result, preserved, _, _ = _source_preflight(tmp_path, commit_override, version_override)
    # Assert
    assert (result.returncode != 0, preserved, result.stdout) == (True, True, "")
