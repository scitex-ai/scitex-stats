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
    assert {"list", "execute", "describe", "recommend", "check-applicability", "recommend-test", "execute-all"} <= names


def test_renamed_noun_leaves_stay_hidden_aliases():
    # Arrange
    renamed = {"applicability": "check-applicability", "run-all": "execute-all"}
    # Act
    aliases = {
        name: (group_under_check.commands[name].hidden, group_under_check.commands[name]._deprecated_alias["target"])
        for name in renamed
    }
    # Assert
    assert aliases == {name: (True, target) for name, target in renamed.items()}
