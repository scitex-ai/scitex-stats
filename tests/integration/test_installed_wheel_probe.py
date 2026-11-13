"""Own the release probe's real numerical checks and source-install refusal."""

import importlib.metadata as metadata
import os
import runpy
import subprocess
import sys
from pathlib import Path


PROBE = Path(__file__).resolve().parents[2] / ".github/ci/probe-statistics.py"


def test_probe_runs_public_numerical_and_file_interfaces(tmp_path):
    # Arrange
    probe = runpy.run_path(str(PROBE))
    # Act
    report = probe["verify_python"](tmp_path)
    # Assert
    assert (report["mean"], report["fdr_bh"], report["input_unchanged"]) == (
        2.0, [0.03, 0.04, 0.04], True
    )


def test_probe_refuses_source_import(tmp_path):
    # Arrange
    env = {"PATH": os.defpath, "HOME": str(tmp_path),
           "SCITEX_DIR": str(tmp_path / "state"),
           "PYTHONPATH": str(PROBE.parents[2] / "src") + os.pathsep
           + os.environ.get("PYTHONPATH", "")}
    # Act
    result = subprocess.run(
        [sys.executable, str(PROBE), "--expected-version",
         metadata.version("scitex-stats")],
        env=env, cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    # Assert
    assert (result.returncode != 0, "source imports are refused" in result.stderr) == (
        True, True
    )
