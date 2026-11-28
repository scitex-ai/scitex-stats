"""Release installation failures must stop before any test runs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


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
    # Arrange
    result, _ = failed_dependency_install
    # Act
    code = result.returncode
    # Assert
    assert code == 37


def test_dependency_failure_does_not_start_tests(failed_dependency_install):
    # Arrange
    result, _ = failed_dependency_install
    # Act
    output = result.stdout
    # Assert
    assert "TESTS_REACHED" not in output


def test_dependency_failure_never_retries_a_reduced_profile(failed_dependency_install):
    # Arrange
    _, calls = failed_dependency_install
    # Act
    attempts = len(calls)
    # Assert
    assert attempts == 1
