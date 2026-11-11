"""Release installation failures must stop; publisher code follows artifacts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pypi-publish-and-github-release-on-tag.yml"


@pytest.fixture
def failed_dependency_install(tmp_path):
    """Run the actual install stanza against a resolver that rejects all extras."""
    source = (ROOT / ".github/ci/run-in-sif.sh").read_text()
    start = source.index("# Install scitex-stats + its [all,dev] extras")
    end = source.index("export PYTHONPATH=", start)
    tools = tmp_path / "bin"
    tools.mkdir()
    recorded = tmp_path / "calls"
    for name in ("uv", "pip"):
        tool = tools / name
        tool.write_text(
            '#!/bin/bash\nprintf "%s\\n" "$*" >> "$INSTALL_CALLS"\n'
            'case "$*" in *".[all,dev]"*) exit 37;; esac\nexit 0\n'
        )
        tool.chmod(0o755)
    env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}")
    env.update(INSTALL_CALLS=str(recorded), VENV=str(tmp_path), TMPDIR=str(tmp_path))
    result = subprocess.run(
        [
            "bash",
            "-c",
            "set -euo pipefail\n" + source[start:end] + "echo TESTS_REACHED",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, recorded.read_text().splitlines()


def test_dependency_failure_stops_the_release_job(failed_dependency_install):
    result, _ = failed_dependency_install
    assert result.returncode == 37


def test_dependency_failure_does_not_start_tests(failed_dependency_install):
    result, _ = failed_dependency_install
    assert "TESTS_REACHED" not in result.stdout


def test_dependency_failure_never_retries_a_reduced_profile(failed_dependency_install):
    _, calls = failed_dependency_install
    assert len(calls) == 1


def test_publisher_checkout_uses_the_artifact_source_commit():
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    checkout = next(
        s
        for s in jobs["publish"]["steps"]
        if s.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["ref"] == "${{ needs.build.outputs.commit }}"


def test_build_exports_a_commit_recorded_from_its_checkout(tmp_path):
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    build = jobs["build"]
    step = next(s for s in build["steps"] if s.get("id") == "source")
    output = tmp_path / "github-output"
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=ROOT,
        env=dict(os.environ, GITHUB_OUTPUT=str(output)),
        capture_output=True,
        text=True,
        check=True,
    )
    del result
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    assert (build["outputs"]["commit"], output.read_text()) == (
        "${{ steps.source.outputs.commit }}",
        f"commit={head}\n",
    )
