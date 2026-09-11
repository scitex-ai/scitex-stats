#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the correlated two-AUC difference (DeLong).

Tests cover:
- Identical scorers (null case)
- Antisymmetry under swapping the two scorers
- Consistency with the single-AUC estimates
- Detection of a genuinely better scorer
- Input validation
"""

import numpy as np
import pytest

from scitex_stats.resampling import auc_ci, delta_auc_ci


def _make_paired_scorers(n=300, seed=0):
    """Return labels plus a strong and a weak scorer on the SAME samples."""
    rng = np.random.default_rng(seed)
    y = np.repeat([0, 1], n // 2)
    strong = rng.normal(0.0, 1.0, n) + 1.5 * y
    weak = rng.normal(0.0, 1.0, n) + 0.3 * y
    return y, strong, weak


class TestNullCase:
    """Two identical scorers differ by exactly nothing."""

    def test_identical_scorers_give_zero_delta(self):
        # Arrange
        y, strong, _ = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, strong)
        # Assert
        assert res["delta_auc"] == pytest.approx(0.0)

    def test_identical_scorers_give_p_of_one(self):
        # Arrange
        y, strong, _ = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, strong)
        # Assert
        assert res["p_value"] == pytest.approx(1.0)

    def test_identical_scorers_give_zero_standard_error(self):
        # Arrange
        y, strong, _ = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, strong)
        # Assert
        assert res["se"] == pytest.approx(0.0)

    def test_identical_scorers_do_not_divide_by_zero(self):
        # Arrange
        y, strong, _ = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, strong)
        # Assert
        assert np.isfinite(res["z"])


class TestAntisymmetry:
    """Swapping the scorers negates the difference."""

    def test_swap_negates_delta(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        forward = delta_auc_ci(y, strong, weak)
        reverse = delta_auc_ci(y, weak, strong)
        # Assert
        assert forward["delta_auc"] == pytest.approx(-reverse["delta_auc"])

    def test_swap_preserves_standard_error(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        forward = delta_auc_ci(y, strong, weak)
        reverse = delta_auc_ci(y, weak, strong)
        # Assert
        assert forward["se"] == pytest.approx(reverse["se"])

    def test_swap_preserves_p_value(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        forward = delta_auc_ci(y, strong, weak)
        reverse = delta_auc_ci(y, weak, strong)
        # Assert
        assert forward["p_value"] == pytest.approx(reverse["p_value"])

    def test_swap_mirrors_the_interval(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        forward = delta_auc_ci(y, strong, weak)
        reverse = delta_auc_ci(y, weak, strong)
        # Assert
        assert forward["ci_lower"] == pytest.approx(-reverse["ci_upper"])


class TestAgreementWithSingleAuc:
    """The component AUCs match the standalone estimator."""

    def test_component_aucs_match_auc_ci(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["auc_a"] == pytest.approx(auc_ci(y, strong)["auc"])
        assert res["auc_b"] == pytest.approx(auc_ci(y, weak)["auc"])

    def test_delta_equals_the_difference_of_components(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["delta_auc"] == pytest.approx(res["auc_a"] - res["auc_b"])


class TestDetection:
    """A genuinely better scorer is detected as better."""

    def test_stronger_scorer_has_positive_delta(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["delta_auc"] > 0

    def test_clear_difference_is_significant(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["p_value"] < 0.05

    def test_significant_interval_excludes_zero(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["ci_lower"] > 0.0

    def test_interval_brackets_the_delta(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["ci_lower"] <= res["delta_auc"] <= res["ci_upper"]

    def test_pure_noise_scorers_are_not_significant(self):
        # Arrange: two independent noise scorers, no real difference
        rng = np.random.default_rng(11)
        y = np.repeat([0, 1], 150)
        noise_a = rng.normal(size=300)
        noise_b = rng.normal(size=300)
        # Act
        res = delta_auc_ci(y, noise_a, noise_b)
        # Assert
        assert res["p_value"] > 0.05

    def test_higher_confidence_widens_the_interval(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        narrow = delta_auc_ci(y, strong, weak, ci=90.0)
        wide = delta_auc_ci(y, strong, weak, ci=99.0)
        # Assert
        assert (wide["ci_upper"] - wide["ci_lower"]) > (
            narrow["ci_upper"] - narrow["ci_lower"]
        )


class TestResultShape:
    """The returned contract."""

    def test_all_documented_keys_are_present(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert set(res) == {
            "delta_auc",
            "auc_a",
            "auc_b",
            "ci_lower",
            "ci_upper",
            "ci_level",
            "se",
            "z",
            "p_value",
            "method",
            "n",
            "n_positive",
            "n_negative",
            "formatted",
        }

    def test_formatted_string_reports_delta_and_p(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act
        res = delta_auc_ci(y, strong, weak)
        # Assert
        assert res["formatted"].startswith("dAUC = +")
        assert "p = " in res["formatted"]


class TestValidation:
    """Invalid input fails loudly."""

    def test_mismatched_score_lengths_raise(self):
        # Arrange
        y = np.array([0, 0, 1, 1])
        score_a = np.array([0.1, 0.2, 0.3, 0.4])
        score_b = np.array([0.1, 0.2, 0.3])
        # Act / Assert
        with pytest.raises(ValueError, match="same samples"):
            delta_auc_ci(y, score_a, score_b)

    def test_label_length_mismatch_raises(self):
        # Arrange
        y = np.array([0, 0, 1])
        score_a = np.array([0.1, 0.2, 0.3, 0.4])
        score_b = np.array([0.4, 0.3, 0.2, 0.1])
        # Act / Assert
        with pytest.raises(ValueError, match="y_true has"):
            delta_auc_ci(y, score_a, score_b)

    def test_single_class_raises(self):
        # Arrange
        y = np.array([0, 0, 0, 0])
        score_a = np.array([0.1, 0.2, 0.3, 0.4])
        score_b = np.array([0.4, 0.3, 0.2, 0.1])
        # Act / Assert
        with pytest.raises(ValueError, match="both classes"):
            delta_auc_ci(y, score_a, score_b)

    def test_out_of_range_confidence_level_raises(self):
        # Arrange
        y, strong, weak = _make_paired_scorers()
        # Act / Assert
        with pytest.raises(ValueError, match="ci must be"):
            delta_auc_ci(y, strong, weak, ci=0.0)


# EOF
