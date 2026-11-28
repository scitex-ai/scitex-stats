"""Reject direct dispatcher use without the exact outer-bound private root."""

import os
import subprocess
from pathlib import Path

import pytest

DISPATCH = Path(__file__).resolve().parents[2] / ".github/ci/run-owned-in-sif.sh"


@pytest.mark.parametrize("extra,expected", [
    ({}, "outer owned scratch identity"),
    ({"SCITEX_STATS_JOB_ROOT_ID": "0:0:0:700"}, "root identity mismatch"),
])
def test_dispatcher_refuses_absent_or_wrong_bound_root(tmp_path, extra, expected):
    # Arrange
    environment = {"PATH": os.defpath, "HOME": str(tmp_path)}
    environment.update(extra)
    # Act
    result = subprocess.run(
        ["bash", str(DISPATCH), "run-in-sif.sh", "3.12"], env=environment,
        capture_output=True, text=True, timeout=5,
    )
    # Assert
    assert (result.returncode != 0, expected in result.stderr) == (True, True)


@pytest.mark.parametrize("inner", ["run-in-sif.sh", "build-in-sif.sh", "probe-wheel-in-sif.sh"])
def test_direct_inner_driver_refuses_unowned_host_tmp(tmp_path, inner):
    # Arrange
    script = DISPATCH.with_name(inner)
    environment = {"PATH": os.defpath, "HOME": str(tmp_path)}
    # Act
    result = subprocess.run(["bash", str(script), "3.12"], env=environment,
                            capture_output=True, text=True, timeout=5)
    # Assert
    assert (result.returncode, "outer owned scratch identity" in result.stderr) == (1, True)
