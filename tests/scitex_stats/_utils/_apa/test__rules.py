#!/usr/bin/env python3
"""The APA rule table: every rule carries the line it renders, and all are covered."""

import pytest

from .conftest import CASES

from scitex_stats._utils._apa import RULES, rule_by_key


@pytest.mark.parametrize("name", list(CASES))
def test_rule_table_example_is_the_rendered_line(results, name):
    # Arrange
    rule = rule_by_key(results[name]["apa"]["rule"])
    # Act
    example = rule.example
    # Assert
    assert example == results[name]["apa"]["plain"]


def test_every_rule_is_exercised_by_a_case(results):
    # Arrange
    keys = {r.key for r in RULES}
    # Act
    covered = {res["apa"]["rule"] for res in results.values()}
    # Assert
    assert keys == covered
