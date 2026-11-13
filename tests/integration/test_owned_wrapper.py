"""Check owned scratch and environment before invoking any actual container."""

import subprocess
from pathlib import Path

import pytest

from ._owned_wrapper_control import RESOURCE, ROOT, WRAPPER, bindings, invoke, make_case, report


@pytest.fixture
def outer_case(tmp_path):
    return make_case(tmp_path)


def test_runtime_does_not_inherit_ambient_credentials(outer_case):
    # Arrange
    case = outer_case
    # Act
    result = invoke(case)
    values = report(case)["forbidden"].values()
    # Assert
    assert (result.returncode, set(values)) == (0, {None})


def test_private_home_and_work_are_removed(outer_case):
    # Arrange
    case = outer_case
    # Act
    result = invoke(case)
    snapshot = report(case)
    # Assert
    assert (result.returncode, snapshot["home_mode"], Path(snapshot["home"]).exists(),
            Path(snapshot["scratch"]).exists(), list(case["runner"].iterdir())) == (0, "0o700", False, False, [])


def test_runtime_receives_cleanenv_home_and_private_tmp_bind(outer_case):
    # Arrange
    case = outer_case
    # Act
    result = invoke(case)
    snapshot = report(case)
    argv = snapshot["argv"]
    # Assert
    assert (result.returncode, "--cleanenv" in argv, argv[argv.index("--home") + 1],
            argv[argv.index("--bind") + 1]) == (
        0, True, snapshot["home"] + ":/home/scitex-release",
        str(Path(snapshot["home"]).parent / "container") + ":/tmp",
    )


def test_runtime_failure_status_survives_cleanup(tmp_path):
    # Arrange
    case = make_case(tmp_path, "raise SystemExit(23)\n")
    # Act
    result = invoke(case)
    # Assert
    assert (result.returncode, list(case["runner"].iterdir())) == (23, [])


def test_changed_shared_resource_refused_before_execution(outer_case, tmp_path):
    # Arrange
    changed = tmp_path / "changed-resource.sh"
    changed.write_bytes(RESOURCE.read_bytes() + b"\n")
    outer_case["env"]["SCITEX_CI_OWNED_CONTEXT"] = str(changed)
    # Act
    result = invoke(outer_case)
    # Assert
    assert (result.returncode, "context digest mismatch" in result.stderr,
            outer_case["marker"].exists(), list(outer_case["runner"].iterdir())) == (1, True, False, [])


def test_symlinked_shared_resource_refused(outer_case, tmp_path):
    # Arrange
    link = tmp_path / "resource-link"
    link.symlink_to(RESOURCE)
    outer_case["env"]["SCITEX_CI_OWNED_CONTEXT"] = str(link)
    # Act
    result = invoke(outer_case)
    # Assert
    assert (result.returncode, "non-symlink" in result.stderr, outer_case["marker"].exists()) == (1, True, False)


def test_missing_shared_resource_refused(outer_case):
    # Arrange
    del outer_case["env"]["SCITEX_CI_OWNED_CONTEXT"]
    # Act
    result = invoke(outer_case)
    # Assert
    assert (result.returncode, "SCITEX_CI_OWNED_CONTEXT" in result.stderr,
            outer_case["marker"].exists()) == (1, True, False)


@pytest.mark.parametrize("separator", [":", ",", "\n"])
def test_ambiguous_bind_parent_refused_and_cleaned(outer_case, tmp_path, separator):
    # Arrange
    runner = tmp_path / ("bind" + separator + "parent")
    runner.mkdir()
    outer_case["env"]["RUNNER_TEMP"] = str(runner)
    # Act
    result = invoke(outer_case)
    # Assert
    assert (result.returncode, "bind separators" in result.stderr,
            outer_case["marker"].exists(), list(runner.iterdir())) == (1, True, False, [])


def test_qualified_resource_path_with_spaces(outer_case, tmp_path):
    # Arrange
    resource = tmp_path / "qualified shared lifecycle.sh"
    resource.write_bytes(RESOURCE.read_bytes())
    outer_case["env"]["SCITEX_CI_OWNED_CONTEXT"] = str(resource)
    # Act
    result = invoke(outer_case)
    # Assert
    assert (result.returncode, list(outer_case["runner"].iterdir())) == (0, [])


def test_legacy_publisher_is_not_executed(outer_case):
    # Arrange
    # Act
    result = subprocess.run(["bash", str(WRAPPER), "publish-in-sif.sh", "3.12"],
                            cwd=ROOT, env=outer_case["env"], capture_output=True, text=True, timeout=5)
    # Assert
    assert (result.returncode, "non-publishing" in result.stderr,
            outer_case["marker"].exists()) == (1, True, False)


def test_checkout_and_both_temporary_roots_are_explicitly_bound(outer_case):
    # Arrange
    case = outer_case
    # Act
    result = invoke(case)
    temporary = str(Path(report(case)["home"]).parent / "container")
    # Assert
    assert (result.returncode, {temporary + ":/tmp", temporary + ":/var/tmp",
                               str(ROOT) + ":" + str(ROOT)} <= bindings(case)) == (0, True)
