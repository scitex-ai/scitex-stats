#!/usr/bin/env python3
"""Tests for seaborn-style data= parameter support in scitex.stats."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from scitex_stats._utils._csv_support import resolve_columns, resolve_groups


@pytest.fixture
def paired_column_source(tmp_path):
    """Keep DataFrame/CSV source arrangement outside the shared test intent."""
    def select_source(frame, source_kind):
        if source_kind == "csv":
            source = tmp_path / "paired.csv"
            frame.to_csv(source, index=False)
            return source
        return frame

    return select_source


@pytest.mark.parametrize("source_kind", ["dataframe", "csv"])
@pytest.mark.parametrize(
    "engine_name",
    ["test_ttest_rel", "test_wilcoxon", "test_pearson", "test_spearman", "test_kendall"],
)
def test_paired_columns_keep_original_observation_positions(
    engine_name, source_kind, tmp_path, paired_column_source
):
    # Arrange
    import scitex_stats

    x = np.array([9, np.nan, 8, 4, 7, 3, 6, 2, 5], dtype=float)
    y = np.array([1, 20, np.nan, 2, 3, 8, 4, 9, 7], dtype=float)
    frame = pd.DataFrame({"before": x, "after": y}, index=[7, 2, 2, 9, 4, 6, 1, 3, 0])
    source = paired_column_source(frame, source_kind)
    engine = getattr(scitex_stats, engine_name)
    expected = engine(x, y)
    # Act
    actual = engine("before", "after", data=source)
    # Assert
    assert actual == expected


@pytest.mark.parametrize("engine_name", ["test_ttest_ind", "test_mannwhitneyu"])
def test_unpaired_columns_keep_independent_missing_value_removal(engine_name):
    # Arrange
    import scitex_stats

    frame = pd.DataFrame(
        {"x": [1, np.nan, 3, 4, 7, 9], "y": [8, 2, np.nan, 5, 6, 10]}
    )
    engine = getattr(scitex_stats, engine_name)
    expected = engine(frame["x"].dropna().to_numpy(), frame["y"].dropna().to_numpy())
    # Act
    actual = engine("x", "y", data=frame)
    # Assert
    assert actual == expected


def test_preserve_rows_keeps_missing_positions_for_joint_mask():
    # Arrange
    frame = pd.DataFrame({"x": [1, np.nan, 3], "y": [4, 5, np.nan]})
    expected = frame.to_numpy()
    # Act
    actual = resolve_columns(frame, preserve_rows=True, x="x", y="y")
    observed = np.column_stack([actual["x"], actual["y"]])
    # Assert
    assert observed.shape == expected.shape and np.array_equal(
        observed, expected, equal_nan=True
    )


def test_preserve_rows_retains_non_column_array_identity():
    # Arrange
    frame = pd.DataFrame({"y": [4, 5, np.nan]})
    x = np.array([1, np.nan, 3])
    # Act
    actual = resolve_columns(frame, preserve_rows=True, x=x, y="y")
    # Assert
    assert actual["x"] is x


def test_preserve_rows_keeps_existing_staggered_missingness_fixture(df_with_nan):
    # Arrange
    expected = df_with_nan[["x", "y"]].to_numpy()
    # Act
    actual = resolve_columns(df_with_nan, preserve_rows=True, x="x", y="y")
    observed = np.column_stack([actual["x"], actual["y"]])
    # Assert
    assert observed.shape == expected.shape and np.array_equal(
        observed, expected, equal_nan=True
    )


def test_preserve_rows_keeps_true_zeros_and_original_order():
    # Arrange
    frame = pd.DataFrame({"x": [0.0, 3.0, np.nan, 1.0], "y": [2.0, 0.0, 5.0, 4.0]})
    expected = frame.to_numpy()
    # Act
    actual = resolve_columns(frame, preserve_rows=True, x="x", y="y")
    observed = np.column_stack([actual["x"], actual["y"]])
    # Assert
    assert observed.shape == expected.shape and np.array_equal(
        observed, expected, equal_nan=True
    )


def _skip_without_scitex_io():
    """Skip test if scitex_io is not available."""
    try:
        import scitex_io  # noqa: F401
    except ImportError:
        pytest.skip("scitex_io not available")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df():
    """DataFrame with two numeric columns and a group column."""
    np.random.seed(42)
    return pd.DataFrame(
        {
            "before": np.random.normal(100, 10, 30),
            "after": np.random.normal(105, 10, 30),
            "score": np.concatenate(
                [
                    np.random.normal(100, 10, 10),
                    np.random.normal(110, 10, 10),
                    np.random.normal(120, 10, 10),
                ]
            ),
            "group": ["A"] * 10 + ["B"] * 10 + ["C"] * 10,
        }
    )


@pytest.fixture
def csv_path(sample_df):
    """Write sample_df to a temporary CSV and return its path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_df.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def df_with_nan():
    """DataFrame containing NaN values."""
    return pd.DataFrame(
        {
            "x": [1.0, 2.0, np.nan, 4.0, 5.0],
            "y": [10.0, np.nan, 30.0, 40.0, 50.0],
        }
    )


# ---------------------------------------------------------------------------
# resolve_columns tests
# ---------------------------------------------------------------------------


class TestResolveColumns:
    def test_two_columns_resolved(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before", y="after")
        # Assert
        assert "x" in resolved

    def test_two_columns_resolved_2(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before", y="after")
        # Assert
        assert "y" in resolved

    def test_two_columns_ndarray_resolved(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before", y="after")
        # Assert
        assert isinstance(resolved["x"], np.ndarray)

    def test_two_columns_resolved_3(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before", y="after")
        # Assert
        assert len(resolved["x"]) == 30

    def test_single_column_resolved(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before")
        # Assert
        assert "x" in resolved

    def test_single_column_resolved_2(self, sample_df):
        # Arrange
        # Act
        resolved = resolve_columns(sample_df, x="before")
        # Assert
        assert len(resolved["x"]) == 30

    def test_csv_path_ndarray_resolved(self, csv_path):
        # Arrange
        _skip_without_scitex_io()
        # Act
        resolved = resolve_columns(csv_path, x="before", y="after")
        # Assert
        assert isinstance(resolved["x"], np.ndarray)

    def test_csv_path_resolved(self, csv_path):
        # Arrange
        _skip_without_scitex_io()
        # Act
        resolved = resolve_columns(csv_path, x="before", y="after")
        # Assert
        assert len(resolved["x"]) == 30

    def test_missing_column_raises(self, sample_df):
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            resolve_columns(sample_df, x="nonexistent")

    def test_nan_dropped_resolved(self, df_with_nan):
        # Arrange
        # Act
        resolved = resolve_columns(df_with_nan, x="x")
        # Assert
        assert len(resolved["x"]) == 4

    def test_nan_dropped_any_isnan_resolved(self, df_with_nan):
        # Arrange
        # Act
        resolved = resolve_columns(df_with_nan, x="x")
        # Assert
        assert not np.isnan(resolved["x"]).any()

    def test_passthrough_non_string_array_equal_resolved(self, sample_df):
        # Arrange
        arr = np.array([1, 2, 3])
        # Act
        resolved = resolve_columns(sample_df, x=arr, y="after")
        # Assert
        assert np.array_equal(resolved["x"], arr)

    def test_passthrough_non_string_ndarray_resolved(self, sample_df):
        # Arrange
        arr = np.array([1, 2, 3])
        # Act
        resolved = resolve_columns(sample_df, x=arr, y="after")
        # Assert
        assert isinstance(resolved["y"], np.ndarray)


# ---------------------------------------------------------------------------
# resolve_groups tests
# ---------------------------------------------------------------------------


class TestResolveGroups:
    def test_basic_split_groups(self, sample_df):
        # Arrange
        # Act
        groups, names = resolve_groups(sample_df, "score", "group")
        # Assert
        assert len(groups) == 3

    def test_basic_split_names(self, sample_df):
        # Arrange
        # Act
        groups, names = resolve_groups(sample_df, "score", "group")
        # Assert
        assert names == ["A", "B", "C"]

    def test_basic_split_all_ndarray_groups(self, sample_df):
        # Arrange
        # Act
        groups, names = resolve_groups(sample_df, "score", "group")
        # Assert
        assert all(isinstance(g, np.ndarray) for g in groups)

    def test_two_groups_case_1(self, sample_df):
        # Arrange
        df2 = sample_df[sample_df["group"].isin(["A", "B"])]
        # Act
        groups, names = resolve_groups(df2, "score", "group")
        # Assert
        assert len(groups) == 2

    def test_two_groups_names(self, sample_df):
        # Arrange
        df2 = sample_df[sample_df["group"].isin(["A", "B"])]
        # Act
        groups, names = resolve_groups(df2, "score", "group")
        # Assert
        assert names == ["A", "B"]

    def test_csv_path_groups(self, csv_path):
        # Arrange
        _skip_without_scitex_io()
        # Act
        groups, names = resolve_groups(csv_path, "score", "group")
        # Assert
        assert len(groups) == 3

    def test_missing_value_col_raises(self, sample_df):
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="value_col 'bad'"):
            resolve_groups(sample_df, "bad", "group")

    def test_missing_group_col_raises(self, sample_df):
        # Arrange
        # Act
        # Assert
        with pytest.raises(ValueError, match="group_col 'bad'"):
            resolve_groups(sample_df, "score", "bad")


# ---------------------------------------------------------------------------
# Integration tests: test functions with data= parameter
# ---------------------------------------------------------------------------


class TestTwoSampleDataParam:
    """Test data= parameter on two-sample (x, y) test functions."""

    def test_ttest_ind_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_ttest_ind
        # Act
        result = test_ttest_ind(x="before", y="after", data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_ttest_rel_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_ttest_rel
        # Act
        result = test_ttest_rel(x="before", y="after", data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_pearson_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_pearson
        # Act
        result = test_pearson(x="before", y="after", data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_mannwhitneyu_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_mannwhitneyu
        # Act
        result = test_mannwhitneyu(x="before", y="after", data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_csv_path_as_data(self, csv_path):
        # Arrange
        _skip_without_scitex_io()
        from scitex_stats import test_ttest_ind
        # Act
        result = test_ttest_ind(x="before", y="after", data=csv_path)
        # Assert
        assert "pvalue" in result

    def test_backward_compat_arrays(self, sample_df):
        # Arrange
        from scitex_stats import test_ttest_ind
        # Act
        result = test_ttest_ind(sample_df["before"].values, sample_df["after"].values)
        # Assert
        assert "pvalue" in result


class TestOneSampleDataParam:
    """Test data= parameter on one-sample (x) test functions."""

    def test_shapiro_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_shapiro
        # Act
        result = test_shapiro(x="before", data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_ttest_1samp_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_ttest_1samp
        # Act
        result = test_ttest_1samp(x="before", popmean=100, data=sample_df)
        # Assert
        assert "pvalue" in result

    def test_backward_compat_array(self, sample_df):
        # Arrange
        from scitex_stats import test_shapiro
        # Act
        result = test_shapiro(sample_df["before"].values)
        # Assert
        assert "pvalue" in result


class TestMultiGroupDataParam:
    """Test data= parameter on multi-group (groups) test functions."""

    def test_anova_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_anova
        # Act
        result = test_anova(data=sample_df, value_col="score", group_col="group")
        # Assert
        assert "pvalue" in result

    def test_kruskal_with_data(self, sample_df):
        # Arrange
        from scitex_stats import test_kruskal
        # Act
        result = test_kruskal(data=sample_df, value_col="score", group_col="group")
        # Assert
        assert "pvalue" in result

    def test_anova_backward_compat(self, sample_df):
        # Arrange
        from scitex_stats import test_anova
        groups = [
            sample_df[sample_df["group"] == g]["score"].values for g in ["A", "B", "C"]
        ]
        # Act
        result = test_anova(groups)
        # Assert
        assert "pvalue" in result


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
