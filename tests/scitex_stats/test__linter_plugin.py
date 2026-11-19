"""Tests for scitex_stats._linter_plugin — STX-I002 (scipy.stats import).

STX-I002 moved here from the scitex-dev engine with no behaviour change, so
these tests pin the engine's exact behaviour: ``from scipy import stats``
and ``from scipy.stats import ...`` are flagged once per statement; a bare
``import scipy.stats`` is not (it never was); the engine's gates apply; and
the metadata is identical to the engine's compatibility copy.
"""

import ast

from scitex_dev.linter import spi
from scitex_dev.linter.config import LinterConfig

from scitex_stats._linter_plugin import _I002, _bind_import_checker, get_plugin

_RULE = spi.Rule(**_I002)


class _Checker(_bind_import_checker(_RULE, spi)):
    # The umbrella `scitex` (the rule's `requires`) may be absent in this
    # env; pin availability so the checker's own logic is what is tested.
    available = {"scitex": True}


def _findings(source, config=None):
    checker = _Checker(source.splitlines(), config or LinterConfig())
    checker.visit(ast.parse(source))
    return [(i.rule.id, i.line, i.rule.severity) for i in checker.issues]


def test_plugin_declares_i002_with_engine_metadata():
    # Arrange
    from scitex_dev.linter.rules import ALL_RULES

    # Act
    declared = {r.id: r for r in get_plugin()["rules"]}["STX-I002"]
    # Assert — identical to the engine's compatibility copy (delete this
    # test together with that copy once the handover completes).
    assert declared == ALL_RULES["STX-I002"]


def test_scipy_stats_from_imports_are_flagged():
    # Arrange
    source = (
        "from scipy import stats\n"
        "from scipy.stats import ttest_ind, pearsonr\n"
        "from scipy import linalg\n"
        "import scipy.stats\n"
    )
    # Act
    found = _findings(source)
    # Assert
    assert found == [("STX-I002", 1, "warning"), ("STX-I002", 2, "warning")]


def test_stx_allow_comment_suppresses_i002():
    # Arrange
    source = "from scipy import stats  # stx-allow: STX-I002\n"
    # Act
    found = _findings(source)
    # Assert
    assert found == []


def test_per_rule_severity_pin_applies_to_i002():
    # Arrange
    config = LinterConfig(per_rule_severity={"STX-I002": "error"})
    # Act
    found = _findings("from scipy import stats\n", config)
    # Assert
    assert found == [("STX-I002", 1, "error")]
