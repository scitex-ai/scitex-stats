#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for `scitex_stats._utils._formatters.fmt_sym_md` (plain-text italics)."""

from __future__ import annotations

from scitex_stats._utils._formatters import fmt_sym_md


def test_fmt_sym_md_italicizes_plain_symbol():
    # Arrange
    symbol = "t"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*t*"


def test_fmt_sym_md_keeps_lowercase_n_subscript_verbatim():
    # Arrange
    symbol = "n_x"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*n*_x"


def test_fmt_sym_md_keeps_uppercase_n_subscript_verbatim():
    # Arrange
    symbol = "N_subjects"
    # Act
    out = fmt_sym_md(symbol)
    # Assert
    assert out == "*N*_subjects"


def test_fmt_sym_md_does_not_conflate_upper_and_lower_n():
    # Arrange
    lower = fmt_sym_md("n_windows")
    # Act
    upper = fmt_sym_md("N_subjects")
    # Assert
    assert lower != upper
