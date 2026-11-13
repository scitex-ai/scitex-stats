"""Qualify child coverage and absence of test-time site-packages writes."""

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

import coverage
import pytest


PROJECT = Path(__file__).resolve().parents[2]


def test_root_fixture_leaves_sites_and_coverage_environment_untouched(tmp_path):
    # Arrange
    environment = tmp_path / "environment"
    # POSIX links keep relocatable Python distributions connected to their stdlib.
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("COVERAGE_")}
    env.update(
        COVERAGE_PROCESS_START="caller-owned-config",
        COVERAGE_FILE="caller-owned-data",
        PYTHONUSERBASE=str(tmp_path / "user-base"),
    )
    code = (
        "import json, os, runpy, site; from pathlib import Path; "
        "sites = [Path(p) for p in site.getsitepackages()]; "
        "sites += [Path(site.getusersitepackages())]; "
        "snapshot = lambda: {str(p): sorted(x.name for x in p.iterdir()) "
        "if p.exists() else [] for p in sites}; "
        "before = snapshot(); "
        f"runpy.run_path({str(PROJECT / 'tests/conftest.py')!r}); "
        "print(json.dumps([before == snapshot(), "
        "os.environ['COVERAGE_PROCESS_START'], os.environ['COVERAGE_FILE']]))"
    )
    # Act
    result = subprocess.run(
        [str(python), "-c", code], env=env, cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
    )
    # Assert
    observed = json.loads(result.stdout) if result.returncode == 0 else None
    assert (result.returncode, observed) == (
        0, [True, "caller-owned-config", "caller-owned-data"]
    ), result.stderr


@pytest.mark.parametrize("minimal_environment", [False, True])
def test_project_configuration_measures_real_child_lines(
    tmp_path, minimal_environment
):
    # Arrange
    child = tmp_path / "child.py"
    child.write_text("value = 40\nvalue += 2\nassert value == 42\n")
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import os, subprocess, sys\n"
        "keys = {'PATH', 'COVERAGE_PROCESS_CONFIG', 'COVERAGE_FILE', "
        "'COVERAGE_PROCESS_START', 'PYTHONNOUSERSITE'}\n"
        f"env = {{k: v for k, v in os.environ.items() if k in keys}} "
        f"if {minimal_environment!r} else os.environ.copy()\n"
        "subprocess.run([sys.executable, 'child.py'], env=env, "
        "check=True, timeout=15)\n"
    )
    data_file = tmp_path / ".coverage"
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("COVERAGE_")
    }
    env.update(COVERAGE_FILE=str(data_file), PYTHONNOUSERSITE="1")
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--rcfile",
         str(PROJECT / "pyproject.toml"), "--source", str(tmp_path), str(parent)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    measured = coverage.Coverage(data_file=str(data_file), config_file=False)
    measured.combine(keep=True)
    measured.load()
    # Assert
    assert (result.returncode, measured.get_data().lines(str(child))) == (
        0, [1, 2, 3]
    ), result.stderr
