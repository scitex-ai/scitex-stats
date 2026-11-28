"""Reject wrong release inputs before the fresh-wheel runner installs anything."""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


RUNNER = Path(__file__).resolve().parents[2] / ".github/ci/probe-wheel.py"


@pytest.mark.parametrize(
    "wheels, expected",
    [
        ([], "exactly one wheel"),
        ([("scitex-stats", "1.0.0"), ("scitex-stats", "1.0.0")],
         "exactly one wheel"),
        ([("other-project", "1.0.0")], "distribution must be scitex-stats"),
        ([("scitex-stats", "9.9.9")], "version differs"),
    ],
)
def test_runner_refuses_wrong_inputs_before_install(tmp_path, wheels, expected):
    # Arrange
    dist = tmp_path / "dist"
    dist.mkdir()
    for index, (name, version) in enumerate(wheels):
        with zipfile.ZipFile(dist / f"candidate{index}.whl", "w") as archive:
            archive.writestr("candidate.dist-info/METADATA",
                             f"Name: {name}\nVersion: {version}\n")
    # A real executable records any attempted dependency installation.
    marker = tmp_path / "installer-called"
    uv = tmp_path / "uv"
    uv.write_text(f"#!{sys.executable}\nfrom pathlib import Path\n"
                  f"Path({str(marker)!r}).touch()\nraise SystemExit(23)\n")
    uv.chmod(0o700)
    env = {"PATH": str(tmp_path), "HOME": str(tmp_path)}
    # Act
    result = subprocess.run(
        [sys.executable, "-I", str(RUNNER), "--dist", str(dist),
         "--expected-version", "1.0.0"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    # Assert
    assert (result.returncode != 0, expected in result.stderr,
            marker.exists(), result.stdout) == (True, True, False, "")


@pytest.mark.skipif(os.name != "posix", reason="retained runner uses POSIX executables")
def test_runner_propagates_installer_failure_without_fallback(tmp_path):
    # Arrange
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "scitex_stats-1.0.0-py3-none-any.whl", "w") as archive:
        archive.writestr("scitex_stats-1.0.0.dist-info/METADATA",
                         "Name: scitex-stats\nVersion: 1.0.0\n")
    marker = tmp_path / "installer-calls"
    uv = tmp_path / "uv"
    uv.write_text(f"#!{sys.executable}\nfrom pathlib import Path\n"
                  f"with Path({str(marker)!r}).open('a') as out: out.write('called\\n')\n"
                  "raise SystemExit(23)\n")
    uv.chmod(0o700)
    # Act
    result = subprocess.run(
        [sys.executable, "-I", str(RUNNER), "--dist", str(dist),
         "--expected-version", "1.0.0"],
        cwd=tmp_path, env={"PATH": str(tmp_path), "HOME": str(tmp_path)},
        capture_output=True, text=True, timeout=10,
    )
    # Assert
    assert (result.returncode != 0, "exit status 23" in result.stderr,
            marker.read_text(), result.stdout) == (True, True, "called\n", "")


def test_nested_runner_supplies_owned_database_refusal(tmp_path):
    # Arrange
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "scitex_stats-1.0.0-py3-none-any.whl", "w") as archive:
        archive.writestr("scitex_stats-1.0.0.dist-info/METADATA", "Name: scitex-stats\nVersion: 1.0.0\n")
    marker = tmp_path / "refusal.json"
    uv = tmp_path / "uv"
    uv.write_text(f"#!{sys.executable}\nimport json,os\nfrom pathlib import Path\n"
                  "from urllib.parse import urlparse,parse_qs\n"
                  "host=os.environ['PGHOST']\n"
                  "query=parse_qs(urlparse(os.environ['SCITEX_STORE_DSN']).query)\n"
                  f"Path({str(marker)!r}).write_text(json.dumps({{'owned':Path(host).parent==Path(os.environ['TMPDIR']),'dsn':query['host']==[host],'port':os.environ['PGPORT'],'exists':Path(host).exists()}}))\n"
                  "raise SystemExit(23)\n")
    uv.chmod(0o700)
    # Act
    result = subprocess.run([sys.executable, "-I", str(RUNNER), "--dist", str(dist),
                             "--expected-version", "1.0.0"], cwd=tmp_path,
                            env={"PATH":str(tmp_path),"HOME":str(tmp_path)},
                            capture_output=True, text=True, timeout=10)
    # Assert
    assert (result.returncode != 0, json.loads(marker.read_text())) == (True, {"owned":True,"dsn":True,"port":"1","exists":False})
