#!/usr/bin/env python3
# File: src/scitex_stats/_recommend/__init__.py
"""Data-driven test applicability, one primary recommendation, and
sensitivity runs that never select by p-value.

- :func:`check_applicability` — ✓/✗ with reasons for every test.
- :func:`recommend_test` — one primary test with reason + decision path.
- :func:`run_all_applicable` — primary + sensitivity analyses, with a
  p-hacking warning and an agreement report.
"""

from ._applicability import CATALOG, check_applicability
from ._assumptions import DEFAULT_THRESHOLDS
from ._decide import DECISION_RULES, recommend_test
from ._run_all import run_all_applicable

__all__ = [
    "CATALOG",
    "DECISION_RULES",
    "DEFAULT_THRESHOLDS",
    "check_applicability",
    "recommend_test",
    "run_all_applicable",
]

# EOF
