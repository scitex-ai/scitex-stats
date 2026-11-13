"""Exercise Stats release-state isolation with real child interpreters."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import scitex_dev

PROVIDER_SITE = Path(scitex_dev.__file__).resolve().parent.parent
CONTEXT = Path(__file__).resolve().parents[2] / ".github/ci/release-context.sh"


@pytest.fixture
def state_case(tmp_path):
    root = tmp_path / "scratch +%&?#= space"
    root.mkdir(mode=0o700)
    probe = tmp_path / "probe.py"
    probe.write_text("import json,os; print(json.dumps(dict(os.environ)))")
    ambient = tmp_path / "ambient-home"
    ambient.mkdir()
    environment = {"PATH": os.defpath, "HOME": str(ambient)}
    for name in ("GH_TOKEN", "AWS_ACCESS_KEY_ID", "DATABASE_URL", "PYTHONPATH",
                 "COVERAGE_PROCESS_START", "COVERAGE_FILE", "VIRTUAL_ENV",
                 "SCITEX_STORE_DSN", "PGHOST", "MPLCONFIGDIR", "UV_CACHE_DIR"):
        environment[name] = "owned-refusal-fixture"
    return root, probe, environment


def execute(case, body=None):
    root, probe, environment = case
    code = 'set -euo pipefail; source "$1"; stats_release_context "$2" "$3"; '
    code += body or 'stats_release_run "$3/bin/python" -I "$4" "$5"'
    return subprocess.run(
        ["bash", "-c", code, "state-control", str(CONTEXT), str(root), sys.prefix, str(probe), str(PROVIDER_SITE)],
        env=environment, capture_output=True, text=True, timeout=15,
    )


def test_child_receives_only_declared_environment(state_case):
    # Arrange
    forbidden = set(state_case[2]) - {"PATH", "HOME", "SCITEX_STORE_DSN", "PGHOST", "MPLCONFIGDIR", "UV_CACHE_DIR"}
    # Act
    result = execute(state_case)
    child = json.loads(result.stdout)
    # Assert
    assert (result.returncode, forbidden.intersection(child)) == (0, set())


def test_all_private_paths_stay_inside_owned_root(state_case):
    # Arrange
    root = state_case[0]
    names = ("HOME", "TMPDIR", "SCITEX_DIR", "XDG_CACHE_HOME", "XDG_DATA_HOME",
             "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR", "UV_CACHE_DIR", "PIP_CACHE_DIR", "MPLCONFIGDIR")
    # Act
    result = execute(state_case)
    child = json.loads(result.stdout)
    # Assert
    assert (result.returncode, all(Path(child[n]).is_relative_to(root) for n in names)) == (0, True)


def test_postgres_refusal_preserves_special_path_characters(state_case):
    # Arrange
    expected = str(state_case[0] / "stats-state/refused-postgres")
    # Act
    child = json.loads(execute(state_case).stdout)
    parsed = parse_qs(urlparse(child["SCITEX_STORE_DSN"]).query)
    # Assert
    assert (child["PGHOST"], parsed["host"], parsed["port"], Path(expected).exists()) == (expected, [expected], ["1"], False)


def test_parent_home_is_unchanged(state_case):
    # Arrange
    body = 'stats_release_run "$3/bin/python" -I "$4" "$5" > /dev/null; printf "%s" "$HOME"'
    # Act
    result = execute(state_case, body)
    # Assert
    assert (result.returncode, result.stdout) == (0, state_case[2]["HOME"])


def test_symlinked_root_refused(state_case, tmp_path):
    # Arrange
    link = tmp_path / "linked-root"
    link.symlink_to(state_case[0], target_is_directory=True)
    # Act
    result = execute((link, state_case[1], state_case[2]))
    # Assert
    assert (result.returncode, list(state_case[0].iterdir())) == (1, [])


def test_nonprivate_root_refused(state_case):
    # Arrange
    state_case[0].chmod(0o755)
    # Act
    result = execute(state_case)
    # Assert
    assert (result.returncode, list(state_case[0].iterdir())) == (1, [])


def test_occupied_state_refused_without_clobbering(state_case):
    # Arrange
    occupied = state_case[0] / "stats-state"
    occupied.mkdir()
    marker = occupied / "sentinel"
    marker.write_text("preserve")
    # Act
    result = execute(state_case)
    # Assert
    assert (result.returncode, marker.read_text()) == (1, "preserve")


def test_uninitialized_run_refused(state_case):
    # Arrange
    code = 'set -euo pipefail; source "$1"; stats_release_run touch "$2/executed"'
    # Act
    result = subprocess.run(["bash", "-c", code, "state-control", str(CONTEXT), str(state_case[0])], env=state_case[2], capture_output=True, timeout=5)
    # Assert
    assert (result.returncode, list(state_case[0].iterdir())) == (1, [])


def test_real_store_resolution_and_connection_refusal(state_case):
    # Arrange
    state_case[1].write_text('''import json,os,sys
sys.path.insert(0,sys.argv[1])
import scitex_dev
from pathlib import Path
assert Path(scitex_dev.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
import psycopg
from scitex_dev.store import host_store
from psycopg.conninfo import conninfo_to_dict
dsn=host_store(pkg="qualification",name="release").dsn
info=conninfo_to_dict(dsn)
assert info["host"] == os.environ["PGHOST"] and info["port"] == "1"
assert not os.path.exists(info["host"])
assert len(os.fsencode(info["host"]+"/.s.PGSQL.1")) < 104
try:
    psycopg.connect(dsn, connect_timeout=1)
except psycopg.OperationalError as error:
    assert "No such file or directory" in str(error)
    print(json.dumps({"refused":True}))
else:
    raise RuntimeError("owned refusal socket unexpectedly accepted a connection")
''')
    # Act
    with tempfile.TemporaryDirectory(prefix="ss-", dir="/tmp") as short_root:
        result = execute((Path(short_root), state_case[1], state_case[2]))
    # Assert
    assert (result.returncode, result.stdout.strip()) == (0, '{"refused": true}'), result.stderr
