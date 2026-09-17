#!/usr/bin/env python3
"""The SIF exec wrapper must work on a HETEROGENEOUS runner pool.

Two measured failures drove these cases:

1. The wrapper hardcoded its apptainer scratch under
   `/data/gpfs/projects/punim0264`, so on the org runners it died at
   `mkdir: cannot create directory '/data': Permission denied` BEFORE anything
   ran (v0.2.26 build; every leg of the first v0.2.27 run).
2. It demanded `~/.env-3.11/bin/apptainer` exactly, which exists on some nodes
   and not others: the same tag passed on 3.11 and 3.12 and died on 3.13 with
   `apptainer shim not executable` (run 35180305493).

These cases run the REAL script against a stub `apptainer` (the external binary
is the boundary; the script's own decisions are what is asserted) and keep the
fail-loud contract: a missing SIF is still a hard error. One assertion per test
(STX-TQ007 — note the checker counts `pytest.skip(...)` as an assertion, so
skips are `@pytest.mark.skipif` decorators here).
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
ABSOLUTE_APPTAINERS = (Path("/usr/bin/apptainer"), Path("/usr/local/bin/apptainer"))


def _stub(path, name, recorded):
    """A stand-in for the apptainer binary: records argv + scratch, exits 0."""
    stub = path / name
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$@" > "{recorded}"\n'
        f'printf "APPTAINER_TMPDIR=%s\\n" "$APPTAINER_TMPDIR" >> "{recorded}"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _run_wrapper(tmp_path, *, shim, sif, path_prepend=None):
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(
        SCITEX_CI_APPTAINER=str(shim),
        SCITEX_CI_SIF=str(sif),
        RUNNER_TEMP=str(runner_temp),
    )
    if path_prepend is not None:
        env["PATH"] = f"{path_prepend}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", str(SCRIPT), "run-in-sif.sh", "3.12"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


@pytest.fixture
def wrapper_run(tmp_path):
    """The wrapper, run once against a stub shim with a present SIF."""
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    recorded = tmp_path / "invocation.txt"
    shim = _stub(tmp_path, "apptainer", recorded)
    return _run_wrapper(tmp_path, shim=shim, sif=sif), recorded, tmp_path


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


def test_wrapper_falls_back_to_an_apptainer_on_the_path(tmp_path):
    # Arrange: the configured shim is absent — exactly the node that broke 3.13.
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    recorded = tmp_path / "invocation.txt"
    _stub(bin_dir, "apptainer", recorded)
    # Act
    proc = _run_wrapper(
        tmp_path, shim=tmp_path / "missing" / "apptainer", sif=sif, path_prepend=bin_dir
    )
    # Assert
    assert proc.returncode == 0


def test_wrapper_uses_the_path_apptainer_when_the_shim_is_absent(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    recorded = tmp_path / "invocation.txt"
    _stub(bin_dir, "apptainer", recorded)
    # Act
    _run_wrapper(tmp_path, shim=tmp_path / "missing" / "apptainer", sif=sif, path_prepend=bin_dir)
    # Assert
    assert "run-in-sif.sh" in recorded.read_text()


def test_wrapper_still_fails_loud_without_the_sif(tmp_path):
    # Arrange
    recorded = tmp_path / "invocation.txt"
    shim = _stub(tmp_path, "apptainer", recorded)
    # Act
    proc = _run_wrapper(tmp_path, shim=shim, sif=tmp_path / "absent.sif")
    # Assert
    assert proc.returncode != 0


def test_wrapper_reports_the_missing_sif_gate(tmp_path):
    # Arrange
    recorded = tmp_path / "invocation.txt"
    shim = _stub(tmp_path, "apptainer", recorded)
    # Act
    proc = _run_wrapper(tmp_path, shim=shim, sif=tmp_path / "absent.sif")
    # Assert
    assert "CI SIF missing" in (proc.stdout + proc.stderr)


@pytest.mark.skipif(
    any(candidate.exists() for candidate in ABSOLUTE_APPTAINERS),
    reason="this host carries an absolute apptainer, so 'nothing usable' cannot be shown here",
)
def test_wrapper_fails_loud_when_no_apptainer_exists_anywhere(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    # Act
    proc = _run_wrapper(
        tmp_path, shim=tmp_path / "missing" / "apptainer", sif=sif, path_prepend=empty_bin
    )
    # Assert
    assert "no usable apptainer found" in (proc.stdout + proc.stderr)


# EOF
