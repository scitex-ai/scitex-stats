"""prepare(): input forms, invalid values, recorded defaults."""

from __future__ import annotations

import pandas as pd
import pytest

from scitex_stats._recommend._data import prepare


def test_dict_input_keeps_names():
    # Arrange
    data = {"ctrl": [1, 2, 3], "drug": [2, 3, 4]}
    # Act
    prep = prepare(data, design="independent", scale="continuous")
    # Assert
    assert prep.names == ["ctrl", "drug"]


def test_dataframe_columns_are_groups():
    # Arrange
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    # Act
    prep = prepare(df, design="independent", scale="continuous")
    # Assert
    assert prep.names == ["a", "b"]


def test_paired_listwise_deletion_drops_incomplete_pairs():
    # Arrange
    data = [[1, 2, None, 4], [1, 2, 3, "x"]]
    # Act
    prep = prepare(data, design="paired", scale="continuous")
    # Assert
    assert prep.pairs_dropped == 2


def test_unspecified_scale_is_recorded():
    # Arrange
    data = [[1, 2, 3], [2, 3, 4]]
    # Act
    prep = prepare(data, design="independent")
    # Assert
    assert prep.scale_specified is False and any("scale not specified" in n["text"] for n in prep.notes)


def test_categorical_rejects_negative_counts():
    # Arrange
    table = [[1, -2], [3, 4]]
    # Act
    def call():
        return prepare(table, design="independent", scale="categorical")

    # Assert
    with pytest.raises(ValueError, match="contingency table"):
        call()


def test_categorical_table_shape():
    # Arrange
    table = [[1, 2, 3], [3, 4, 5]]
    # Act
    prep = prepare(table, design="independent", scale="categorical")
    # Assert
    assert prep.table.shape == (2, 3)
