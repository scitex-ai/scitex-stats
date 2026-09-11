#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the single-AUC confidence interval.

Tests cover:
- Known-value AUC on a hand-computable example
- Perfect and inverted separation
- Tie handling via midranks
- DeLong vs bootstrap agreement
- Confidence-level effects and input validation
"""

import numpy as np
import pytest

from scitex_stats.resampling import auc_ci


def _make_separable_data(n=200, effect=1.0, seed=0):
    """Return labels and scores with a controllable amount of signal."""
    rng = np.random.default_rng(seed)
    y = np.repeat([0, 1], n // 2)
    scores = rng.normal(0.0, 1.0, n) + effect * y
    return y, scores


class TestKnownValues:
    """AUC point estimates against hand-computable ground truth."""

    def test_hand_computed_auc_is_exact(self):
        # Arrange: pairs (neg, pos) concordant in 3 of 4 comparisons
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.4, 0.35, 0.8])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["auc"] == pytest.approx(0.75)

    def test_perfect_separation_auc_is_one(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.2, 0.9, 1.0])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["auc"] == pytest.approx(1.0)

    def test_perfect_separation_upper_bound_is_one(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.2, 0.9, 1.0])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["ci_upper"] == pytest.approx(1.0)

    def test_inverted_scores_give_zero_auc(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.9, 1.0, 0.1, 0.2])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["auc"] == pytest.approx(0.0)

    def test_all_tied_scores_give_chance_auc(self):
        # Arrange: midranks make every comparison a tie -> AUC 0.5
        y = np.array([0, 0, 1, 1])
        score = np.array([0.5, 0.5, 0.5, 0.5])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["auc"] == pytest.approx(0.5)

    def test_partial_ties_are_counted_as_half(self):
        # Arrange: one tied pair among four comparisons -> 0.5 credit
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.4, 0.4, 0.8])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["auc"] == pytest.approx(0.875)


class TestDelongInterval:
    """Properties of the analytic DeLong interval."""

    def test_ci_brackets_the_estimate(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["ci_lower"] <= res["auc"] <= res["ci_upper"]

    def test_standard_error_is_positive(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["se"] > 0

    def test_bounds_stay_within_unit_interval(self):
        # Arrange
        y, score = _make_separable_data(effect=3.0)
        # Act
        res = auc_ci(y, score)
        # Assert
        assert 0.0 <= res["ci_lower"] and res["ci_upper"] <= 1.0

    def test_higher_confidence_widens_the_interval(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        narrow = auc_ci(y, score, ci=90.0)
        wide = auc_ci(y, score, ci=99.0)
        # Assert
        assert (wide["ci_upper"] - wide["ci_lower"]) > (
            narrow["ci_upper"] - narrow["ci_lower"]
        )

    def test_larger_sample_shrinks_the_interval(self):
        # Arrange
        y_small, score_small = _make_separable_data(n=60, seed=1)
        y_large, score_large = _make_separable_data(n=600, seed=1)
        # Act
        small = auc_ci(y_small, score_small)
        large = auc_ci(y_large, score_large)
        # Assert
        assert large["se"] < small["se"]

    def test_reported_counts_match_the_input(self):
        # Arrange
        y, score = _make_separable_data(n=100)
        # Act
        res = auc_ci(y, score)
        # Assert
        assert (res["n"], res["n_positive"], res["n_negative"]) == (100, 50, 50)


class TestBootstrapMethod:
    """The distribution-free alternative and its agreement with DeLong."""

    def test_bootstrap_estimate_matches_delong_point_estimate(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        delong = auc_ci(y, score, method="delong")
        boot = auc_ci(y, score, method="bootstrap", n_boot=400)
        # Assert
        assert boot["auc"] == pytest.approx(delong["auc"])

    def test_bootstrap_and_delong_intervals_overlap(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        delong = auc_ci(y, score, method="delong")
        boot = auc_ci(y, score, method="bootstrap", n_boot=600)
        # Assert
        assert boot["ci_lower"] < delong["ci_upper"]
        assert delong["ci_lower"] < boot["ci_upper"]

    def test_bootstrap_widths_are_comparable_to_delong(self):
        # Arrange
        y, score = _make_separable_data(n=400)
        # Act
        delong = auc_ci(y, score, method="delong")
        boot = auc_ci(y, score, method="bootstrap", n_boot=800)
        # Assert
        delong_width = delong["ci_upper"] - delong["ci_lower"]
        boot_width = boot["ci_upper"] - boot["ci_lower"]
        assert boot_width == pytest.approx(delong_width, rel=0.35)

    def test_bootstrap_is_reproducible_for_a_fixed_seed(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        first = auc_ci(y, score, method="bootstrap", n_boot=200, seed=7)
        second = auc_ci(y, score, method="bootstrap", n_boot=200, seed=7)
        # Assert
        assert first["ci_lower"] == second["ci_lower"]
        assert first["ci_upper"] == second["ci_upper"]

    def test_different_seeds_give_different_intervals(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        first = auc_ci(y, score, method="bootstrap", n_boot=200, seed=1)
        second = auc_ci(y, score, method="bootstrap", n_boot=200, seed=2)
        # Assert
        assert first["ci_lower"] != second["ci_lower"]


class TestResultShape:
    """The returned contract."""

    def test_all_documented_keys_are_present(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        res = auc_ci(y, score)
        # Assert
        assert set(res) == {
            "auc",
            "ci_lower",
            "ci_upper",
            "ci_level",
            "se",
            "method",
            "n",
            "n_positive",
            "n_negative",
            "formatted",
        }

    def test_formatted_string_reports_auc_and_level(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.4, 0.35, 0.8])
        # Act
        res = auc_ci(y, score)
        # Assert
        assert res["formatted"].startswith("AUC = 0.750")
        assert "95% CI" in res["formatted"]

    def test_method_is_echoed_back(self):
        # Arrange
        y, score = _make_separable_data()
        # Act
        res = auc_ci(y, score, method="bootstrap", n_boot=100)
        # Assert
        assert res["method"] == "bootstrap"


class TestValidation:
    """Invalid input fails loudly."""

    def test_single_class_raises(self):
        # Arrange
        y = np.array([1, 1, 1, 1])
        score = np.array([0.1, 0.2, 0.3, 0.4])
        # Act / Assert
        with pytest.raises(ValueError, match="both classes"):
            auc_ci(y, score)

    def test_length_mismatch_raises(self):
        # Arrange
        y = np.array([0, 1, 1])
        score = np.array([0.1, 0.2])
        # Act / Assert
        with pytest.raises(ValueError, match="samples"):
            auc_ci(y, score)

    def test_non_binary_labels_raise(self):
        # Arrange
        y = np.array([0, 1, 2, 1])
        score = np.array([0.1, 0.2, 0.3, 0.4])
        # Act / Assert
        with pytest.raises(ValueError, match="binary"):
            auc_ci(y, score)

    def test_unknown_method_raises(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.2, 0.3, 0.4])
        # Act / Assert
        with pytest.raises(ValueError, match="delong"):
            auc_ci(y, score, method="jackknife")

    @pytest.mark.parametrize("bad_ci", [0.0, 100.0, -5.0, 120.0])
    def test_out_of_range_confidence_level_raises(self, bad_ci):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score = np.array([0.1, 0.2, 0.3, 0.4])
        # Act / Assert
        with pytest.raises(ValueError, match="ci must be"):
            auc_ci(y, score, ci=bad_ci)


# EOF
