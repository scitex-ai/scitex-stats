"""`scitex-stats tests` group registration."""

from __future__ import annotations

from scitex_stats._cli import main
from scitex_stats._cli.tests_group import tests_group as group_under_check


def test_tests_group_is_mounted_on_main():
    # Arrange
    # Act
    group = main.commands.get("tests")
    # Assert
    assert group is group_under_check


def test_tests_group_has_recommend_commands():
    # Arrange
    # Act
    names = set(group_under_check.commands)
    # Assert
    assert {"list", "execute", "describe", "recommend", "applicability", "recommend-test", "run-all"} <= names
