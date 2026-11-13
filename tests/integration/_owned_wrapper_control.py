"""Inert runtime boundary; the wrapper still sources the exact shared lifecycle."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / ".github/ci/exec-in-sif.sh"
RESOURCE = ROOT / "tests/scitex_stats/fixtures/dev-owned-context.bash.fixture"
FORBIDDEN = ("GH_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "APPTAINERENV_GH_TOKEN",
             "SCITEX_STORE_DSN", "VIRTUAL_ENV", "PYTHONPATH", "COVERAGE_FILE")


def make_case(directory, tail=""):
    marker = directory / "runtime.json"
    runtime = directory / "inert runtime"
    runtime.write_text(
        f"#!{sys.executable}\nimport json,os,sys,time\nfrom pathlib import Path\n"
        f"marker=Path({str(marker)!r})\n"
        f"names={FORBIDDEN!r}\n"
        "report={'argv':sys.argv[1:],'home':os.environ['HOME'],"
        "'scratch':os.environ['APPTAINER_TMPDIR'],'pid':os.getpid(),'group':os.getpgrp(),"
        "'home_mode':oct(os.stat(os.environ['HOME']).st_mode & 0o777),"
        "'forbidden':{name:os.environ.get(name) for name in names}}\n"
        "pending=marker.with_suffix('.pending')\n"
        "pending.write_text(json.dumps(report))\npending.replace(marker)\n" + tail
    )
    runtime.chmod(0o700)
    image = directory / "inert image.sif"
    image.write_bytes(b"owned fixture image")
    runner = directory / "runner"
    runner.mkdir()
    environment = {"PATH": os.defpath, "HOME": str(directory / "ambient-home"),
                   "RUNNER_TEMP": str(runner), "SCITEX_CI_APPTAINER": str(runtime),
                   "SCITEX_CI_SIF": str(image), "SCITEX_CI_OWNED_CONTEXT": str(RESOURCE)}
    environment.update({name: "owned-fake-ambient-value" for name in FORBIDDEN})
    environment["SCITEX_CI_APPTAINER_SHA256"] = hashlib.sha256(runtime.read_bytes()).hexdigest()
    environment["SCITEX_CI_SIF_SHA256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    return {"env": environment, "marker": marker, "runtime": runtime, "runner": runner}


def invoke(case):
    return subprocess.run(["bash", str(WRAPPER), "run-in-sif.sh", "3.12"], cwd=ROOT,
                          env=case["env"], capture_output=True, text=True, timeout=15)


def report(case):
    return json.loads(case["marker"].read_text())


def bindings(case):
    argv = report(case)["argv"]
    return {argv[index + 1] for index, value in enumerate(argv) if value == "--bind"}
