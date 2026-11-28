"""The release route resolves one promoted tag and publishes only verified central bytes."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pypi-publish-and-github-release-on-tag.yml"
CENTRAL = re.compile(
    r"^scitex-ai/\.github/\.github/workflows/leaf-release-sif\.yml@[0-9a-f]{40}$"
)


@pytest.fixture(scope="module")
def jobs():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


# Fixture repositories ignore the caller's global/system Git settings and hooks.
ISOLATED_GIT = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=dict(os.environ, **ISOLATED_GIT),
    )


@pytest.fixture
def promoted(tmp_path):
    """A real origin whose main holds a tagged commit, plus an unpromoted tag."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(work))
    _git(work, "config", "user.email", "release@example.invalid")
    _git(work, "config", "user.name", "release")
    (work / "pyproject.toml").write_text(
        '[project]\nname = "scitex-stats"\nversion = "0.0.0"\n'
    )
    _git(work, "add", "pyproject.toml")
    _git(work, "commit", "-q", "-m", "promoted")
    _git(work, "tag", "v0.0.0")
    _git(work, "checkout", "-q", "-b", "side")
    (work / "pyproject.toml").write_text(
        '[project]\nname = "scitex-stats"\nversion = "0.0.1"\n'
    )
    _git(work, "commit", "-q", "-am", "unpromoted")
    _git(work, "tag", "v0.0.1")
    _git(work, "tag", "v0.0.2")
    _git(work, "remote", "add", "origin", str(origin))
    _git(work, "push", "-q", "origin", "main", "side", "--tags")
    _git(work, "checkout", "-q", "main")
    return work


def _preflight(jobs, cwd, tag, tmp_path):
    step = next(s for s in jobs["preflight"]["steps"] if s.get("id") == "identity")
    output = tmp_path / "github-output"
    output.write_text("")
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=dict(
            {k: v for k, v in os.environ.items() if k != "BASH_ENV"},
            RELEASE_TAG=tag,
            GITHUB_OUTPUT=str(output),
            **ISOLATED_GIT,
        ),
    )
    return result, output.read_text()


def test_preflight_refuses_a_malformed_tag(jobs, promoted, tmp_path):
    # Arrange
    tag = "v1.1.0; true"
    # Act
    result, _ = _preflight(jobs, promoted, tag, tmp_path)
    # Assert
    assert "release tag must be vX.Y.Z" in result.stdout


def test_preflight_refuses_a_tag_that_is_not_on_main(jobs, promoted, tmp_path):
    # Arrange
    tag = "v0.0.1"
    # Act
    result, _ = _preflight(jobs, promoted, tag, tmp_path)
    # Assert
    assert "is not on protected main" in result.stdout


def test_preflight_writes_no_identity_for_a_refused_tag(jobs, promoted, tmp_path):
    # Arrange
    tag = "v0.0.1"
    # Act
    _, output = _preflight(jobs, promoted, tag, tmp_path)
    # Assert
    assert output == ""


def test_preflight_refuses_a_tag_whose_project_version_differs(
    jobs, promoted, tmp_path
):
    # Arrange
    _git(promoted, "push", "-q", "origin", "side:main")
    tag = "v0.0.2"
    # Act
    result, _ = _preflight(jobs, promoted, tag, tmp_path)
    # Assert
    assert "declares 'scitex-stats 0.0.1', not scitex-stats 0.0.2" in result.stdout


def test_preflight_resolves_a_promoted_tag_to_its_commit(jobs, promoted, tmp_path):
    # Arrange: real PyPI has no scitex-stats 0.0.0, so the version is unused.
    commit = subprocess.check_output(
        ["git", "rev-parse", "v0.0.0^{commit}"], cwd=promoted, text=True
    ).strip()
    # Act
    _, output = _preflight(jobs, promoted, "v0.0.0", tmp_path)
    # Assert
    assert output == f"tag=v0.0.0\ncommit={commit}\nversion=0.0.0\n"


def test_preflight_refuses_a_version_already_on_pypi(jobs, promoted, tmp_path):
    # Arrange: scitex-stats 1.0.0 is public on PyPI.
    (promoted / "pyproject.toml").write_text(
        '[project]\nname = "scitex-stats"\nversion = "1.0.0"\n'
    )
    _git(promoted, "commit", "-q", "-am", "published")
    _git(promoted, "tag", "v1.0.0")
    _git(promoted, "push", "-q", "origin", "main", "v1.0.0")
    # Act
    result, _ = _preflight(jobs, promoted, "v1.0.0", tmp_path)
    # Assert
    assert "is not an unused PyPI version (HTTP 200)" in result.stdout


@pytest.mark.parametrize("name", ["test", "build"])
def test_native_jobs_use_the_pinned_central_executor(jobs, name):
    # Arrange
    job = jobs[name]
    # Act
    uses = job["uses"]
    # Assert
    assert CENTRAL.match(uses)


@pytest.mark.parametrize(("name", "operation"), [("test", "test"), ("build", "build")])
def test_native_jobs_receive_only_the_preflight_identity(jobs, name, operation):
    # Arrange
    job = jobs[name]
    # Act
    inputs = job["with"]
    # Assert
    assert inputs == {
        "operation": operation,
        "source_commit": "${{ needs.preflight.outputs.commit }}",
        "release_tag": "${{ needs.preflight.outputs.tag }}",
    }


def test_test_and_build_executors_are_the_same_central_revision(jobs):
    # Arrange
    names = ("test", "build")
    # Act
    revisions = {jobs[name]["uses"] for name in names}
    # Assert
    assert len(revisions) == 1


def test_publisher_checkout_uses_the_preflight_commit(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    checkout = next(
        s for s in steps if s.get("uses", "").startswith("actions/checkout@")
    )
    # Assert
    assert checkout["with"]["ref"] == "${{ needs.preflight.outputs.commit }}"


def test_publisher_downloads_the_central_build_artifact(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    download = next(
        s for s in steps if s.get("uses", "").startswith("actions/download-artifact@")
    )
    # Assert
    assert download["with"] == {
        "name": "stats-dist-${{ needs.preflight.outputs.commit }}",
        "path": "dist",
    }


def test_publisher_verifies_tag_and_bytes_before_upload(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    verify = next(i for i, s in enumerate(steps) if "verify-proof" in s.get("run", ""))
    upload = next(
        i
        for i, s in enumerate(steps)
        if s.get("uses", "").startswith("pypa/gh-action-pypi-publish@")
    )
    # Assert
    assert verify == upload - 1


def test_publisher_refuses_a_moved_tag(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    body = next(s["run"] for s in steps if "verify-proof" in s.get("run", ""))
    # Assert
    assert 'refs/tags/$RELEASE_TAG^{commit}")" = "$RELEASE_COMMIT" ]' in body


def test_publisher_uploads_exactly_the_wheel_and_sdist(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    body = next(s["run"] for s in steps if "verify-proof" in s.get("run", ""))
    # Assert
    assert 'mv dist/release-proof.json "$RUNNER_TEMP/proof/"' in body and (
        '[ "$(find dist -mindepth 1 | wc -l)" -eq 2 ]' in body
    )


def test_publisher_uses_the_pinned_pypi_trusted_publishing_action(jobs):
    # Arrange
    steps = jobs["publish"]["steps"]
    # Act
    upload = next(
        s for s in steps if s.get("uses", "").startswith("pypa/gh-action-pypi-publish@")
    )
    # Assert
    assert re.fullmatch(r"pypa/gh-action-pypi-publish@[0-9a-f]{40}", upload["uses"])


def test_publisher_keeps_the_trusted_environment_and_oidc_scope(jobs):
    # Arrange
    job = jobs["publish"]
    # Act
    scope = (job["runs-on"], job["environment"]["name"], job["permissions"])
    # Assert
    assert scope == ("ubuntu-latest", "pypi", {"contents": "read", "id-token": "write"})


def test_workflow_default_token_is_read_only():
    # Arrange
    workflow = yaml.safe_load(WORKFLOW.read_text())
    # Act
    permissions = workflow["permissions"]
    # Assert
    assert permissions == {"contents": "read"}


def test_release_runs_only_after_publication(jobs):
    # Arrange
    job = jobs["release"]
    # Act
    needs = job["needs"]
    # Assert
    assert needs == ["preflight", "build", "publish"]
