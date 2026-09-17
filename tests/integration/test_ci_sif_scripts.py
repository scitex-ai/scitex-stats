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
is the boundary; the script's own decisions are what is asserted). They are
hermetic about the two things the host also has: `HOME` is redirected, so the
`~/.env-3.11/bin/apptainer` shim the script prepends to PATH cannot answer
instead of the stub, and the SIF path is one we create. A "nothing usable
anywhere" case is deliberately absent — it cannot be asserted hermetically
because the resolver's last candidates are absolute host paths; the fail-loud
contract is covered through the SIF gate instead.

One assertion per test (STX-TQ007 — the checker counts `pytest.skip(...)` as an
assertion, so skips are `@pytest.mark.skipif` decorators).
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


def _stub(directory, name, recorded):
    """A stand-in for the apptainer binary: records argv + scratch, exits 0."""
    directory.mkdir(parents=True, exist_ok=True)
    stub = directory / name
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$@" > "{recorded}"\n'
        f'printf "APPTAINER_TMPDIR=%s\\n" "$APPTAINER_TMPDIR" >> "{recorded}"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _run_wrapper(tmp_path, *, shim, sif, path_prepend=None, home=None):
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
    if home is not None:
        env["HOME"] = str(home)
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
    # Arrange: the configured shim is absent — the node state that broke 3.13.
    # HOME is redirected so the shim the script prepends to PATH cannot answer.
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    stub_dir = tmp_path / "stub-bin"
    recorded = tmp_path / "invocation.txt"
    _stub(stub_dir, "apptainer", recorded)
    # Act
    proc = _run_wrapper(
        tmp_path,
        shim=tmp_path / "missing" / "apptainer",
        sif=sif,
        path_prepend=stub_dir,
        home=tmp_path / "empty-home",
    )
    # Assert
    assert proc.returncode == 0


def test_wrapper_hands_the_inner_script_to_the_path_apptainer(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    stub_dir = tmp_path / "stub-bin"
    recorded = tmp_path / "invocation.txt"
    _stub(stub_dir, "apptainer", recorded)
    # Act
    _run_wrapper(
        tmp_path,
        shim=tmp_path / "missing" / "apptainer",
        sif=sif,
        path_prepend=stub_dir,
        home=tmp_path / "empty-home",
    )
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


# EOF
