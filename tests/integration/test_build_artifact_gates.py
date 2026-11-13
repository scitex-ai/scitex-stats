"""The actual post-build shell stanza must stop before any later release gate.

External proof/install processes are inert executable fixtures here. Real archive
and installed-wheel behavior has separate owning tests and release qualification.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".github/ci/build-in-sif.sh"


@pytest.mark.parametrize("failure, expected_calls, code", [
    ("none", ["write-proof", "probe", "verify-proof"], 0),
    ("write-proof", ["write-proof"], 23),
    ("probe", ["write-proof", "probe"], 23),
    ("verify-proof", ["write-proof", "probe", "verify-proof"], 23),
])
def test_build_stops_at_the_first_failed_artifact_gate(tmp_path, failure, expected_calls, code):
    # Arrange: execute the literal production stanza against subprocess fixtures.
    calls = tmp_path / "calls.jsonl"
    python = tmp_path / "python-boundary"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "name='probe' if sys.argv[2].endswith('probe-wheel.py') else sys.argv[3]\n"
        "with open(os.environ['GATE_CALLS'],'a') as out: out.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "raise SystemExit(23 if name==os.environ['FAIL_GATE'] else 0)\n"
    )
    python.chmod(0o700)
    source = BUILD.read_text()
    stanza = source[source.index('# Keep transfer outside this application.'):]
    env = dict(os.environ, PY=str(python), HELPERS=str(ROOT / ".github/ci"),
               EXPECTED_COMMIT="a" * 40, EXPECTED_VERSION="1.0.1",
               GATE_CALLS=str(calls), FAIL_GATE=failure)
    # Act
    result = subprocess.run(["bash", "-euo", "pipefail", "-c", stanza],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    # Assert: source/version are caller supplied; failure never reaches later checks.
    actual = [json.loads(line) for line in calls.read_text().splitlines()]
    stages = ["probe" if argv[1].endswith("probe-wheel.py") else argv[2] for argv in actual]
    assert (result.returncode, stages) == (code, expected_calls), result.stderr
    for argv in actual:
        if argv[1].endswith("release-identity.py"):
            assert argv[argv.index("--commit") + 1] == "a" * 40
            assert argv[argv.index("--version") + 1] == "1.0.1"
        else:
            assert argv[argv.index("--expected-version") + 1] == "1.0.1"
