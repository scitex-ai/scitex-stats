#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_stats/reporting/__init__.py

"""Six-stat reporting bundle.

Encodes the operator's six-stat reporting doctrine (2026-07-05) as a
checked invariant rather than a documentation convention: any reported
statistic must carry all of (1) n, (2) 95% CI, (3) method/test name,
(4) p-value, (5) effect size, (6) test statistic. See :func:`full_report`.
"""

from ._full_report import SIX_STAT_FIELDS, IncompleteReportError, full_report

__all__ = ["full_report", "SIX_STAT_FIELDS", "IncompleteReportError"]

# EOF
