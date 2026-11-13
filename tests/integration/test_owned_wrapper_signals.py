"""Cancel an actual wrapper-owned process group before releasing its root."""

import os
import signal
import subprocess
import time
from pathlib import Path

from ._owned_wrapper_control import ROOT, WRAPPER, make_case, report


def birth(pid):
    try:
        path = Path(f"/proc/{pid}")
        if path.stat().st_uid != os.getuid():
            return None
        return (path / "stat").read_text().rsplit(") ", 1)[1].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def retire_fixture(process, group, token):
    if group is not None and group > 1 and group != os.getpgrp() and token is not None:
        try:
            if birth(group) == token and os.getpgid(group) == group:
                os.killpg(group, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
        process.communicate(timeout=5)


def test_term_cancels_runtime_then_cleans_owned_root(tmp_path):
    # Arrange
    late = tmp_path / "late-write"
    case = make_case(tmp_path, f"time.sleep(30)\nPath({str(late)!r}).write_text('late')\n")
    process = subprocess.Popen(["bash", str(WRAPPER), "run-in-sif.sh", "3.12"],
                               cwd=ROOT, env=case["env"], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    group = token = None
    try:
        until = time.monotonic() + 5
        while not case["marker"].exists() and process.poll() is None and time.monotonic() < until:
            time.sleep(0.02)
        group = report(case)["group"]
        token = birth(group)
        # Act
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=15)
        # Assert
        assert (process.returncode, list(case["runner"].iterdir()), late.exists()) == (143, [], False), (stdout, stderr)
    finally:
        retire_fixture(process, group, token)
