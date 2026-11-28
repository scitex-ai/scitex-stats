"""Own the release probe's real numerical checks and source-install refusal."""

import importlib.metadata as metadata
import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import scitex_dev


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
    env = {
        **{key: value for key, value in os.environ.items()
           if key in {"COVERAGE_PROCESS_START", "COVERAGE_PROCESS_CONFIG", "COVERAGE_FILE"}},
        "PATH": os.defpath, "HOME": str(tmp_path),
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


@pytest.mark.parametrize("home_kind", ["default", "installer"])
def test_probe_children_use_private_store_and_state(home_kind):
    # Arrange
    site = str(Path(scitex_dev.__file__).resolve().parent.parent)
    script = '''import os,sys,json
sys.path.insert(0,sys.argv[1])
import psycopg
from pathlib import Path
from scitex_dev.store import host_store
from psycopg.conninfo import conninfo_to_dict
expected=sys.argv[2]
info=conninfo_to_dict(host_store(pkg="qualification",name="probe").dsn)
assert info["host"]==expected and os.environ["PGHOST"]==expected and info["port"]=="1"
assert not info.get("hostaddr") and not info.get("service")
assert "PGHOSTADDR" not in os.environ and "PGSERVICE" not in os.environ
assert expected.startswith("/tmp/") and not Path(expected).exists()
assert len(os.fsencode(expected+"/.s.PGSQL.1"))<104
assert os.environ["HOME"]==sys.argv[3]
assert "SCITEX_RELEASE_SENTINEL" not in os.environ
try:
    psycopg.connect(host_store(pkg="qualification",name="probe").dsn,connect_timeout=1)
except psycopg.OperationalError as error:
    assert "No such file or directory" in str(error)
    print(json.dumps({"private_socket_refused":True,"ambient_absent":True}))
else:
    raise RuntimeError("owned missing socket unexpectedly accepted connection")
'''
    # Act
    with tempfile.TemporaryDirectory(prefix="sp-", dir="/tmp") as directory:
        root = Path(directory)
        (root / "home").mkdir()
        expected_home = {"default": root, "installer": root / "home"}[home_kind]
        wrapper = """import runpy,subprocess,sys
from pathlib import Path
factory=runpy.run_path(sys.argv[1])["isolated_environment"]
root=Path(sys.argv[2])
options={} if sys.argv[3]=="default" else {"home":root/"home"}
result=subprocess.run([sys.executable,"-I","-c",sys.argv[4],*sys.argv[5:]],
                      env=factory(root,**options),capture_output=True,text=True,timeout=15)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
"""
        result = subprocess.run(
            [sys.executable, "-I", "-c", wrapper, str(PROBE), str(root),
             home_kind, script, site, str(root / "refused-postgres"),
             str(expected_home)],
            env={**os.environ, "SCITEX_RELEASE_SENTINEL": "owned-fixture"},
            capture_output=True, text=True, timeout=20,
        )
    # Assert
    assert (result.returncode, result.stdout.strip()) == (0, '{"private_socket_refused": true, "ambient_absent": true}'), result.stderr
