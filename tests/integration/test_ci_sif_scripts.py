#!/usr/bin/env python3
"""The SIF exec wrapper must work on a NON-Spartan runner.

Regression: `exec-in-sif.sh` hardcoded its apptainer scratch under
`/data/gpfs/projects/punim0264`, so on the org runners the wrapper died at

    mkdir: cannot create directory '/data': Permission denied

BEFORE anything ran — which is how the v0.2.26 build stage and every leg of the
first v0.2.27 run went red with all tests otherwise healthy.

These cases run the REAL script against a stub `apptainer` (the external binary
is the boundary; the script's own decisions are what is asserted): where its
scratch goes, whether it binds the Spartan tree, and that it still fails loud
when the shim or the SIF is missing. One assertion per test (STX-TQ007).
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


def _run_wrapper(tmp_path, shim, sif):
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
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


@pytest.fixture
def wrapper_run(tmp_path):
    """The wrapper, run once against a stub apptainer with a present SIF."""
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    shim, recorded = _stub_apptainer(tmp_path)
    return _run_wrapper(tmp_path, shim, sif), recorded, tmp_path


def test_wrapper_exits_zero_on_a_non_spartan_runner(wrapper_run):
    # Arrange
    proc, _, _ = wrapper_run
    # Act
    code = proc.returncode
    # Assert
    assert code == 0


def test_wrapper_scratch_lives_under_the_runner_temp(wrapper_run):
    # Arrange
    _, recorded, tmp_path = wrapper_run
    # Act
    written = recorded.read_text()
    # Assert
    assert f"APPTAINER_TMPDIR={tmp_path}/runner-temp" in written


@pytest.mark.skipif(
    SPARTAN_BIND.is_dir(), reason="this host carries the Spartan bind tree; absence is the case under test"
)
def test_wrapper_omits_the_bind_where_the_spartan_tree_is_absent(wrapper_run):
    # Arrange
    _, recorded, _ = wrapper_run
    # Act
    argv = recorded.read_text()
    # Assert
    assert "--bind" not in argv


def test_missing_shim_exits_non_zero(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    # Act
    proc = _run_wrapper(tmp_path, tmp_path / "not-there" / "apptainer", sif)
    # Assert
    assert proc.returncode != 0


def test_missing_shim_reports_the_gate(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    # Act
    proc = _run_wrapper(tmp_path, tmp_path / "not-there" / "apptainer", sif)
    # Assert
    assert "apptainer shim not executable" in (proc.stdout + proc.stderr)


def test_missing_sif_exits_non_zero(tmp_path):
    # Arrange
    shim, _ = _stub_apptainer(tmp_path)
    # Act
    proc = _run_wrapper(tmp_path, shim, tmp_path / "absent.sif")
    # Assert
    assert proc.returncode != 0


def test_missing_sif_reports_the_gate(tmp_path):
    # Arrange
    shim, _ = _stub_apptainer(tmp_path)
    # Act
    proc = _run_wrapper(tmp_path, shim, tmp_path / "absent.sif")
    # Assert
    assert "CI SIF missing" in (proc.stdout + proc.stderr)


# EOF
