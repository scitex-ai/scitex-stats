"""Skills installation must preserve caller files through the shared installer."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from scitex_stats._cli.skills_group import skills_group


@pytest.mark.parametrize("flags", [[], ["--no-link"]], ids=["link", "copy"])
def test_install_refuses_unmanaged_namespace(tmp_path: Path, flags):
    # Arrange
    dest = tmp_path / "skills"
    note = dest / "scitex-stats" / "caller-notes.md"
    note.parent.mkdir(parents=True)
    note.write_bytes(b"Keep these caller-owned notes.\n")

    # Act
    result = CliRunner().invoke(
        skills_group, ["install", "--dest", str(dest), *flags]
    )

    # Assert
    observed = {
        "exit_code": result.exit_code,
        "note": note.read_bytes() if note.is_file() else None,
    }
    assert observed == {
        "exit_code": 1,
        "note": b"Keep these caller-owned notes.\n",
    }


@pytest.mark.parametrize("flags", [[], ["--no-link"]], ids=["link", "copy"])
def test_install_refuses_foreign_file_in_managed_namespace(tmp_path: Path, flags):
    # Arrange
    dest = tmp_path / "skills"
    runner = CliRunner()
    initial = runner.invoke(
        skills_group, ["install", "--dest", str(dest), "--no-link"]
    )
    note = dest / "scitex-stats" / "caller-notes.md"
    note.write_bytes(b"Keep this addition to the managed tree.\n")

    # Act
    result = runner.invoke(
        skills_group, ["install", "--dest", str(dest), *flags]
    )

    # Assert
    observed = {
        "initial_exit_code": initial.exit_code,
        "refresh_exit_code": result.exit_code,
        "note": note.read_bytes() if note.is_file() else None,
    }
    assert observed == {
        "initial_exit_code": 0,
        "refresh_exit_code": 1,
        "note": b"Keep this addition to the managed tree.\n",
    }


def test_directory_alias_creates_managed_projection(tmp_path: Path):
    from scitex_dev.skill_registry import MANIFEST_NAME

    # Arrange
    dest = tmp_path / "skills"
    # Act
    result = CliRunner().invoke(
        skills_group, ["install", "--directory", str(dest), "--no-link"]
    )

    # Assert
    observed = {
        "exit_code": result.exit_code,
        "manifest": (dest / MANIFEST_NAME).is_file(),
        "entry": (dest / "scitex-stats" / "SKILL.md").is_file(),
    }
    assert observed == {"exit_code": 0, "manifest": True, "entry": True}
