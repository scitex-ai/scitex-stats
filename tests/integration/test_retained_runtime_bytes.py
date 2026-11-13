"""Exercise retained-wrapper byte and execution refusal using inert runtimes."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None
    or shutil.which("sha256sum") is None,
    reason="retained Linux SIF wrapper requires bash and sha256sum",
)
ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / ".github/ci/exec-in-sif.sh"


@pytest.fixture
def configured_runtime(tmp_path):
    marker = tmp_path / "executed.json"
    runtime = tmp_path / "configured runtime"
    body = (
        f"#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n"
    )
    runtime.write_text(body)
    runtime.chmod(0o700)
    fallback = tmp_path / "apptainer"
    fallback.write_text(body)
    fallback.chmod(0o700)
    image = tmp_path / "reviewed image.sif"
    image.write_bytes(b"inert reviewed image bytes")
    env = {
        "PATH": str(tmp_path) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "RUNNER_TEMP": str(tmp_path),
        "SCITEX_CI_APPTAINER": str(runtime),
        "SCITEX_CI_APPTAINER_SHA256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
        "SCITEX_CI_SIF": str(image),
        "SCITEX_CI_SIF_SHA256": hashlib.sha256(image.read_bytes()).hexdigest(),
    }
    return {
        "marker": marker, "runtime": runtime, "image": image, "env": env,
        "runtime_paths": {"absolute": str(runtime), "home": f"~/{runtime.name}"},
        "image_paths": {"absolute": str(image), "home": f"~/{image.name}"},
    }


def _invoke(config, inner="build-in-sif.sh"):
    return subprocess.run(
        ["bash", str(WRAPPER), inner, "3.12", "argument with spaces"],
        cwd=ROOT, env=config["env"], capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("path_kind", ["absolute", "home"])
def test_wrapper_executes_only_matching_configured_bytes(configured_runtime, path_kind):
    # Arrange
    config = configured_runtime
    config["env"]["SCITEX_CI_APPTAINER"] = config["runtime_paths"][path_kind]
    config["env"]["SCITEX_CI_SIF"] = config["image_paths"][path_kind]
    # Act
    result = _invoke(config)
    argv = json.loads(config["marker"].read_text())
    # Assert
    assert (result.returncode, argv[-5:]) == (
        0, [str(config["image"]), "bash", ".github/ci/build-in-sif.sh",
            "3.12", "argument with spaces"],
    )


@pytest.mark.parametrize("field, value, message", [
    ("SCITEX_CI_SIF_SHA256", "", "SCITEX_CI_SIF_SHA256"),
    ("SCITEX_CI_APPTAINER_SHA256", "", "SCITEX_CI_APPTAINER_SHA256"),
    ("SCITEX_CI_SIF_SHA256", "bad", "lowercase SHA-256"),
    ("SCITEX_CI_APPTAINER_SHA256", "bad", "lowercase SHA-256"),
    ("SCITEX_CI_SIF_SHA256", "0" * 64, "image digest mismatch"),
    ("SCITEX_CI_APPTAINER_SHA256", "0" * 64, "runtime digest mismatch"),
])
def test_wrapper_refuses_missing_or_wrong_pins(
    configured_runtime, field, value, message,
):
    # Arrange
    config = configured_runtime
    config["env"][field] = value
    # Act
    result = _invoke(config)
    # Assert
    assert (result.returncode != 0, message in result.stderr,
            config["marker"].exists()) == (True, True, False)


def test_wrapper_does_not_replace_missing_configured_runtime(configured_runtime):
    # Arrange: another inert executable exists on PATH.
    config = configured_runtime
    config["runtime"].unlink()
    # Act
    result = _invoke(config)
    # Assert
    assert (result.returncode != 0, "not executable" in result.stderr,
            config["marker"].exists()) == (True, True, False)


def test_wrapper_refuses_changed_image_bytes(configured_runtime):
    # Arrange
    config = configured_runtime
    config["image"].write_bytes(b"foreign image bytes")
    # Act
    result = _invoke(config)
    # Assert
    assert (result.returncode != 0, "image digest mismatch" in result.stderr,
            config["marker"].exists()) == (True, True, False)


def test_wrapper_refuses_inner_path_traversal(configured_runtime):
    # Arrange
    config = configured_runtime
    # Act
    result = _invoke(config, "../build-in-sif.sh")
    # Assert
    assert (result.returncode != 0, "shell basename" in result.stderr,
            config["marker"].exists()) == (True, True, False)
