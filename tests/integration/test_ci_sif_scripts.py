#!/usr/bin/env python3
"""Retain scratch, binding and argument contracts for explicitly pinned runtimes.

The real wrapper executes inert stub runtimes at the external binary boundary.
Fixtures supply the expected hashes of their own stub/image files. Runtime
selection follows the explicit configuration: an executable on PATH cannot
replace a missing configured runtime. HOME and scratch are private to each case.
The original non-Spartan scratch and omitted-GPFS-bind regressions remain tested.
"""

from __future__ import annotations

import hashlib
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


def _fixture_digest(path):
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return "0" * 64


def _run_wrapper(tmp_path, *, shim, sif, path_prepend=None, home=None):
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(
        SCITEX_CI_APPTAINER=str(shim),
        SCITEX_CI_SIF=str(sif),
        SCITEX_CI_APPTAINER_SHA256=_fixture_digest(shim),
        SCITEX_CI_SIF_SHA256=_fixture_digest(sif),
        RUNNER_TEMP=str(runner_temp),
        SCITEX_CI_OWNED_CONTEXT=str(REPO_ROOT / "tests/scitex_stats/fixtures/dev-owned-context.bash.fixture"),
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
    assert str(SPARTAN_BIND) not in argv


def test_wrapper_refuses_a_path_substitute_for_missing_configured_runtime(tmp_path):
    # Arrange: PATH has a stub, but the explicitly configured runtime is absent.
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
    assert (proc.returncode != 0, "configured runtime is not executable" in proc.stderr,
            recorded.exists()) == (True, True, False)


def test_wrapper_hands_the_inner_script_to_the_configured_apptainer(tmp_path):
    # Arrange
    sif = tmp_path / "ci-cpu.sif"
    sif.write_text("")
    stub_dir = tmp_path / "stub-bin"
    recorded = tmp_path / "invocation.txt"
    shim = _stub(stub_dir, "apptainer", recorded)
    # Act
    proc = _run_wrapper(
        tmp_path,
        shim=shim,
        sif=sif,
        path_prepend=stub_dir,
        home=tmp_path / "empty-home",
    )
    # Assert
    assert (proc.returncode, "run-in-sif.sh" in recorded.read_text()) == (0, True)


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
    assert "configured image is missing" in (proc.stdout + proc.stderr)


# EOF
