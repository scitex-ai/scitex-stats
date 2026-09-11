#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the generic percentile-bootstrap confidence interval.

Tests cover:
- Point estimate and interval coverage for a known distribution
- Reproducibility under a fixed seed
- Paired (row-wise) resampling across several arrays
- Stratified resampling and degenerate-resample handling
- Input validation
"""

import numpy as np
import pytest

from scitex_stats.resampling import bootstrap_ci


def _paired_difference(x, y):
    """Mean paired difference — a two-array metric."""
    return float(np.mean(x - y))


class TestPointEstimate:
    """The estimate comes from the observed data, not the resamples."""

    def test_estimate_matches_the_metric_on_observed_data(self):
        # Arrange
        x = np.arange(100, dtype=float)
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=200, seed=0)
        # Assert
        assert res["estimate"] == pytest.approx(np.mean(x))

    def test_interval_brackets_the_estimate(self):
        # Arrange
        x = np.arange(100, dtype=float)
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=500, seed=0)
        # Assert
        assert res["ci_lower"] <= res["estimate"] <= res["ci_upper"]

    def test_interval_covers_the_true_mean(self):
        # Arrange: known population mean of 5.0
        rng = np.random.default_rng(3)
        x = rng.normal(5.0, 1.0, 400)
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=800, seed=0)
        # Assert
        assert res["ci_lower"] < 5.0 < res["ci_upper"]

    def test_standard_error_approximates_the_analytic_one(self):
        # Arrange: SE of the mean = s / sqrt(n)
        rng = np.random.default_rng(4)
        x = rng.normal(0.0, 2.0, 500)
        analytic_se = np.std(x, ddof=1) / np.sqrt(len(x))
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=1000, seed=0)
        # Assert
        assert res["se"] == pytest.approx(analytic_se, rel=0.2)

    def test_works_with_a_median_metric(self):
        # Arrange
        rng = np.random.default_rng(5)
        x = rng.normal(0.0, 1.0, 300)
        # Act
        res = bootstrap_ci(np.median, x, n_boot=400, seed=0)
        # Assert
        assert res["ci_lower"] <= res["estimate"] <= res["ci_upper"]


class TestReproducibility:
    """A fixed seed pins the interval."""

    def test_same_seed_gives_identical_bounds(self):
        # Arrange
        x = np.arange(50, dtype=float)
        # Act
        first = bootstrap_ci(np.mean, x, n_boot=300, seed=42)
        second = bootstrap_ci(np.mean, x, n_boot=300, seed=42)
        # Assert
        assert first["ci_lower"] == second["ci_lower"]
        assert first["ci_upper"] == second["ci_upper"]

    def test_different_seeds_give_different_bounds(self):
        # Arrange
        x = np.arange(50, dtype=float)
        # Act
        first = bootstrap_ci(np.mean, x, n_boot=300, seed=1)
        second = bootstrap_ci(np.mean, x, n_boot=300, seed=2)
        # Assert
        assert first["ci_lower"] != second["ci_lower"]


class TestPairedResampling:
    """Several arrays are resampled jointly, preserving row alignment."""

    def test_paired_metric_recovers_a_constant_offset(self):
        # Arrange: y is x shifted by exactly 2.0, so every resample agrees
        x = np.arange(100, dtype=float)
        y = x - 2.0
        # Act
        res = bootstrap_ci(_paired_difference, x, y, n_boot=200, seed=0)
        # Assert
        assert res["estimate"] == pytest.approx(2.0)

    def test_constant_offset_gives_a_degenerate_interval(self):
        # Arrange
        x = np.arange(100, dtype=float)
        y = x - 2.0
        # Act
        res = bootstrap_ci(_paired_difference, x, y, n_boot=200, seed=0)
        # Assert
        assert res["ci_lower"] == pytest.approx(2.0)
        assert res["ci_upper"] == pytest.approx(2.0)

    def test_rows_stay_aligned_across_arrays(self):
        # Arrange: pairing carries all the signal; shuffling would destroy it
        rng = np.random.default_rng(6)
        x = rng.normal(size=200)
        y = x + rng.normal(0.0, 0.01, 200)
        # Act
        res = bootstrap_ci(_paired_difference, x, y, n_boot=300, seed=0)
        # Assert
        assert abs(res["ci_upper"] - res["ci_lower"]) < 0.01

    def test_length_mismatch_across_arrays_raises(self):
        # Arrange
        x = np.arange(10, dtype=float)
        y = np.arange(9, dtype=float)
        # Act / Assert
        with pytest.raises(ValueError, match="same length|share length"):
            bootstrap_ci(_paired_difference, x, y, n_boot=10)


class TestStratification:
    """Stratified resampling keeps every group present."""

    def test_group_sizes_are_preserved_in_every_resample(self):
        # Arrange: metric returns the positive count, which must stay fixed
        y = np.repeat([0, 1], [80, 20])
        observed_positives = int(y.sum())
        # Act
        res = bootstrap_ci(
            lambda labels: float(labels.sum()),
            y,
            n_boot=100,
            seed=0,
            stratify=y,
        )
        # Assert
        assert res["ci_lower"] == pytest.approx(observed_positives)
        assert res["ci_upper"] == pytest.approx(observed_positives)

    def test_stratified_run_uses_every_resample(self):
        # Arrange
        y = np.repeat([0, 1], [30, 6])
        rng = np.random.default_rng(7)
        score = rng.normal(size=len(y)) + y
        # Act
        res = bootstrap_ci(
            lambda labels, scores: float(np.mean(scores[labels == 1])),
            y,
            score,
            n_boot=200,
            seed=0,
            stratify=y,
        )
        # Assert
        assert res["n_valid"] == 200

    def test_stratify_length_mismatch_raises(self):
        # Arrange
        x = np.arange(10, dtype=float)
        # Act / Assert
        with pytest.raises(ValueError, match="stratify has"):
            bootstrap_ci(np.mean, x, n_boot=10, stratify=np.arange(9))


class TestDegenerateResamples:
    """Failures are discarded and counted, never silently coerced."""

    def test_failing_resamples_are_excluded_from_n_valid(self):
        # Arrange: metric rejects resamples that miss the rare class
        y = np.repeat([0, 1], [40, 2])

        def positives_only(labels):
            if labels.sum() == 0:
                raise ValueError("no positives in this resample")
            return float(labels.sum())

        # Act
        res = bootstrap_ci(positives_only, y, n_boot=200, seed=0)
        # Assert
        assert res["n_valid"] < res["n_boot"]

    def test_valid_resamples_still_produce_an_interval(self):
        # Arrange
        y = np.repeat([0, 1], [40, 2])

        def positives_only(labels):
            if labels.sum() == 0:
                raise ValueError("no positives in this resample")
            return float(labels.sum())

        # Act
        res = bootstrap_ci(positives_only, y, n_boot=200, seed=0)
        # Assert
        assert res["ci_lower"] <= res["ci_upper"]

    def test_metric_failing_on_observed_data_propagates_its_own_error(self):
        # Arrange: a metric broken on the real data must fail fast with its
        # own message, not be reinterpreted as a resampling problem
        x = np.arange(20, dtype=float)

        def always_fails(_):
            raise ValueError("never works")

        # Act / Assert
        with pytest.raises(ValueError, match="never works"):
            bootstrap_ci(always_fails, x, n_boot=25)

    def test_all_resamples_failing_raises_with_a_hint(self):
        # Arrange: succeeds on the observed (all-distinct) data, but every
        # resample draws with replacement and so contains a duplicate
        x = np.arange(20, dtype=float)

        def requires_all_distinct(values):
            if len(np.unique(values)) != len(values):
                raise ValueError("duplicate rows in this resample")
            return float(np.mean(values))

        # Act / Assert
        with pytest.raises(ValueError, match="stratify"):
            bootstrap_ci(requires_all_distinct, x, n_boot=25)

    def test_non_finite_metric_values_are_discarded(self):
        # Arrange
        x = np.arange(20, dtype=float)
        # Act / Assert
        with pytest.raises(ValueError, match="finite"):
            bootstrap_ci(lambda _: float("nan"), x, n_boot=25)


class TestResultShape:
    """The returned contract."""

    def test_all_documented_keys_are_present(self):
        # Arrange
        x = np.arange(30, dtype=float)
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=100, seed=0)
        # Assert
        assert set(res) == {
            "estimate",
            "ci_lower",
            "ci_upper",
            "ci_level",
            "se",
            "n_boot",
            "n_valid",
            "n",
            "method",
            "formatted",
        }

    def test_formatted_string_reports_the_estimate_and_level(self):
        # Arrange
        x = np.arange(30, dtype=float)
        # Act
        res = bootstrap_ci(np.mean, x, n_boot=100, ci=90.0, seed=0)
        # Assert
        assert res["formatted"].startswith("14.500")
        assert "90% CI" in res["formatted"]

    def test_higher_confidence_widens_the_interval(self):
        # Arrange
        rng = np.random.default_rng(8)
        x = rng.normal(size=200)
        # Act
        narrow = bootstrap_ci(np.mean, x, n_boot=800, ci=90.0, seed=0)
        wide = bootstrap_ci(np.mean, x, n_boot=800, ci=99.0, seed=0)
        # Assert
        assert (wide["ci_upper"] - wide["ci_lower"]) > (
            narrow["ci_upper"] - narrow["ci_lower"]
        )


class TestValidation:
    """Invalid input fails loudly."""

    def test_no_arrays_raises(self):
        # Act / Assert
        with pytest.raises(ValueError, match="at least one array"):
            bootstrap_ci(np.mean)

    @pytest.mark.parametrize("bad_ci", [0.0, 100.0, -1.0])
    def test_out_of_range_confidence_level_raises(self, bad_ci):
        # Arrange
        x = np.arange(10, dtype=float)
        # Act / Assert
        with pytest.raises(ValueError, match="ci must be"):
            bootstrap_ci(np.mean, x, ci=bad_ci)

    @pytest.mark.parametrize("bad_n_boot", [0, -10])
    def test_non_positive_n_boot_raises(self, bad_n_boot):
        # Arrange
        x = np.arange(10, dtype=float)
        # Act / Assert
        with pytest.raises(ValueError, match="n_boot must be positive"):
            bootstrap_ci(np.mean, x, n_boot=bad_n_boot)


# EOF
