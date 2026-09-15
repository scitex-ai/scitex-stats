#!/usr/bin/env python3
# File: tests/scitex_stats/_plot/test__backends.py
"""Rendering with and without FigRecipe (mirrors src/scitex_stats/_plot/_backends.py)."""

from __future__ import annotations

import types

import pytest

import scitex_stats as ss
from scitex_stats._plot import _backends

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]


def _no_figrecipe(name):
    if name == "figrecipe":
        raise ImportError("simulated: figrecipe not installed")
    return __import__(name)


def _old_figrecipe(name):
    return types.SimpleNamespace(__name__="figrecipe")


@pytest.fixture
def spec():
    return ss.run_test("ttest_ind", data=A, data2=B, plot_spec=True)["plot_spec"]


def test_auto_falls_back_to_matplotlib_without_figrecipe(spec):
    # Arrange
    importer = _no_figrecipe
    # Act
    out = ss.plot(spec, importer=importer)
    # Assert
    assert out.backend == "matplotlib"


def test_matplotlib_fallback_renders_png(spec):
    # Arrange
    out = ss.plot(spec, importer=_no_figrecipe)
    # Act
    png = out.to_bytes("png")
    # Assert
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_matplotlib_fallback_renders_svg(spec):
    # Arrange
    out = ss.plot(spec, importer=_no_figrecipe)
    # Act
    svg = out.to_bytes("svg")
    # Assert
    assert b"<svg" in svg


def test_matplotlib_output_is_deterministic(spec):
    # Arrange
    first = ss.plot(spec, backend="matplotlib").to_bytes("png")
    # Act
    second = ss.plot(spec, backend="matplotlib").to_bytes("png")
    # Assert
    assert first == second


def test_figrecipe_without_spec_importer_counts_as_absent(spec):
    # Arrange
    importer = _old_figrecipe
    # Act
    out = ss.plot(spec, importer=importer)
    # Assert
    assert out.backend == "matplotlib"


def test_forced_figrecipe_backend_raises_when_absent(spec):
    # Arrange
    def call():
        return ss.plot(spec, backend="figrecipe", importer=_no_figrecipe)
    # Act
    expected = ImportError
    # Assert
    with pytest.raises(expected):
        call()


def test_plot_accepts_result_plus_data():
    # Arrange
    result = ss.run_test("ttest_ind", data=A, data2=B)
    # Act
    out = ss.plot(result, data=A, data2=B, importer=_no_figrecipe)
    # Assert
    assert out.spec["kind"] == "groups"


@pytest.mark.skipif(not _backends.figrecipe_available(), reason="figrecipe with from_stats_plot_spec not installed")
def test_figrecipe_path_writes_a_replayable_recipe(spec, tmp_path):
    # Arrange
    import figrecipe

    out = ss.plot(spec, backend="figrecipe")
    out.save(tmp_path / "ttest.png")
    # Act
    replayed, _ax = figrecipe.reproduce(tmp_path / "ttest.yaml")
    # Assert
    assert replayed is not None


# EOF
