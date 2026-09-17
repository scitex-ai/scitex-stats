#!/usr/bin/env python3
"""The SIF exec wrapper must work on a NON-Spartan runner.

Regression: `exec-in-sif.sh` hardcoded its apptainer scratch under
`/data/gpfs/projects/punim0264`, so on `actions-runner-org-04` the wrapper died
at `mkdir: cannot create directory '/data': Permission denied` — AFTER all
three test legs had passed — and the 0.2.26 build stage never ran.

These cases run the REAL script against a stub `apptainer` (the external binary
is the boundary; the script's own decisions are what is asserted): where its
scratch goes, whether it binds the Spartan tree, and whether it still fails
loud when the shim or SIF is missing.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".github" / "ci" / "exec-in-sif.sh"
SPARTAN_BIND = Path("/data/gpfs/projects/punim0264")


def _stub_apptainer(tmp_path):
    """A stand-in for the apptainer binary: records argv + scratch, exits 0."""
    recorded = tmp_path / "invocation.txt"
    stub = tmp_path / "apptainer"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$@" > "{recorded}"\n'
        f'printf "APPTAINER_TMPDIR=%s\\n" "$APPTAINER_TMPDIR" >> "{recorded}"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub, recorded


def _run_wrapper(tmp_path, shim):
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    env = dict(os.environ)
    env.update(
        SCITEX_CI_APPTAINER=str(shim),
        SCITEX_CI_SIF=str(sif),
        RUNNER_TEMP=str(runner_temp),
    )
    return subprocess.run(
        ["bash", str(SCRIPT), "run-in-sif.sh", "3.12"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def test_wrapper_puts_its_scratch_under_the_runner_temp(tmp_path):
    # Arrange
    shim, recorded = _stub_apptainer(tmp_path)
    # Act
    proc = _run_wrapper(tmp_path, shim)
    # Assert
    assert proc.returncode == 0 and f"APPTAINER_TMPDIR={tmp_path}/runner-temp" in recorded.read_text()


def test_wrapper_binds_the_spartan_tree_only_when_it_exists(tmp_path):
    # Arrange
    if SPARTAN_BIND.is_dir():
        pytest.skip("this host carries the Spartan bind tree; absence is the case under test")
    shim, recorded = _stub_apptainer(tmp_path)
    # Act
    proc = _run_wrapper(tmp_path, shim)
    # Assert
    assert proc.returncode == 0 and "--bind" not in recorded.read_text()


def test_wrapper_still_fails_loud_without_an_executable_shim(tmp_path):
    # Arrange
    missing_shim = tmp_path / "not-there" / "apptainer"
    # Act
    proc = _run_wrapper(tmp_path, missing_shim)
    # Assert
    assert proc.returncode != 0 and "apptainer shim not executable" in (proc.stdout + proc.stderr)


def test_wrapper_still_fails_loud_without_the_sif(tmp_path):
    # Arrange
    shim, _ = _stub_apptainer(tmp_path)
    env = dict(os.environ)
    env.update(
        SCITEX_CI_APPTAINER=str(shim),
        SCITEX_CI_SIF=str(tmp_path / "absent.sif"),
        RUNNER_TEMP=str(tmp_path),
    )
    # Act
    proc = subprocess.run(
        ["bash", str(SCRIPT), "run-in-sif.sh", "3.12"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )
    # Assert
    assert proc.returncode != 0 and "CI SIF missing" in (proc.stdout + proc.stderr)


# EOF
