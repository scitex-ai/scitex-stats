"""Check real DataFrame formatting, including axes and scalar boundary behavior."""

import numpy as np
import pandas as pd
import pytest

from scitex_stats._utils import p2stars

OPTIONS = (
    ({}, [["***", "**", "*"], ["***", "**", "ns"], ["NaN", "invalid", "invalid"]]),
    ({"ns_symbol": False}, [["***", "**", "*"], ["***", "**", ""], ["NaN", "invalid", "invalid"]]),
    ({"thresholds": (.01, .05), "symbols": ("strong", "weak", "none")},
     [["strong", "strong", "weak"], ["strong", "strong", "none"], ["NaN", "invalid", "invalid"]]),
    ({"thresholds": (.01, .05), "symbols": ("strong", "weak", "none"), "ns_symbol": False},
     [["strong", "strong", "weak"], ["strong", "strong", ""], ["NaN", "invalid", "invalid"]]),
)


def frame():
    return pd.DataFrame(
        [[.001, .01, .05], [0, .005, .15], [np.nan, -.1, 1.2]],
        index=pd.Index(["first", "second", "third"], name="sample"),
        columns=pd.Index(["A", "B", "C"], name="comparison"),
    )


@pytest.mark.parametrize("options, values", OPTIONS)
def test_dataframe_stars_preserve_values_type_and_named_axes(options, values):
    # Arrange
    data = frame()
    expected = pd.DataFrame(values, index=data.index, columns=data.columns)
    # Act
    result = p2stars(data, **options)
    # Assert
    assert type(result) is pd.DataFrame and result.equals(expected) and result.index.identical(expected.index) and result.columns.identical(expected.columns)


def test_dataframe_stars_do_not_mutate_input_values_or_axes():
    # Arrange
    data = frame()
    before = data.copy(deep=True)
    # Act
    p2stars(data)
    # Assert
    assert data.equals(before) and data.index.names == before.index.names and data.columns.names == before.columns.names


@pytest.mark.parametrize("multiindex", [False, True])
def test_dataframe_stars_preserve_duplicate_or_hierarchical_axes(multiindex):
    # Arrange
    data, expected = labelled_frames(multiindex)
    # Act
    result = p2stars(data)
    # Assert
    assert result.equals(expected) and result.index.names == expected.index.names and result.columns.names == expected.columns.names


def labelled_frames(multiindex):
    axis = pd.Index(["same", "same"], name="duplicate")
    if multiindex:
        axis = pd.MultiIndex.from_tuples([("group", "one"), ("group", "two")], names=["family", "member"])
    data = pd.DataFrame([[.05, .01], [.2, .001]], index=axis, columns=axis)
    expected = pd.DataFrame([["*", "**"], ["ns", "***"]], index=axis, columns=axis)
    return data, expected


@pytest.mark.parametrize("rows, columns", [(0, 2), (2, 0)])
def test_empty_dataframe_stars_preserve_shape_and_named_axes(rows, columns):
    # Arrange
    data = pd.DataFrame(index=pd.RangeIndex(rows, name="sample"), columns=pd.RangeIndex(columns, name="comparison"))
    # Act
    result = p2stars(data)
    # Assert
    assert type(result) is pd.DataFrame and result.shape == data.shape and result.index.identical(data.index) and result.columns.identical(data.columns)


@pytest.mark.parametrize("options, message", [
    ({"thresholds": (.05, .01, .001)}, "ascending order"),
    ({"symbols": ("*", "ns")}, "one more than thresholds"),
])
def test_dataframe_stars_preserve_threshold_configuration_errors(options, message):
    # Arrange
    data = frame()
    # Act
    # Assert
    with pytest.raises(ValueError, match=message):
        p2stars(data, **options)
