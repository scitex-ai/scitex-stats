#!/usr/bin/env python3
# File: tests/scitex_stats/_plot/test__spec.py
"""Plot spec generation per test family (mirrors src/scitex_stats/_plot/_spec.py)."""

from __future__ import annotations

import json

import pytest

import scitex_stats as ss
from scitex_stats._plot import PLOT_SPEC_JSON_SCHEMA, SCHEMA_ID, stack_brackets

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]
C = [5.5, 6.0, 5.9, 6.2, 5.8, 6.1, 5.7, 6.0]
Y = [4.5, 4.1, 4.8, 4.3, 5.7, 5.7, 4.9, 5.7]

CASES = {
    "ttest_ind": ("groups", dict(data=A, data2=B)),
    "mannwhitneyu": ("groups", dict(data=A, data2=B)),
    "anova": ("groups", dict(groups=[A, B, C])),
    "kruskal": ("groups", dict(groups=[A, B, C])),
    "ttest_rel": ("paired", dict(data=A, data2=B)),
    "wilcoxon": ("paired", dict(data=A, data2=B)),
    "pearson": ("correlation", dict(data=A, data2=Y)),
    "spearman": ("correlation", dict(data=A, data2=Y)),
    "chi2": ("contingency", dict(groups=[[10, 20], [30, 15]])),
    "ttest_1samp": ("one_sample", dict(data=A, popmean=5.0)),
}


def _spec(name):
    return ss.run_test(name, plot_spec=True, **CASES[name][1])["plot_spec"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_kind_follows_test_family(name):
    # Arrange
    expected = CASES[name][0]
    # Act
    spec = _spec(name)
    # Assert
    assert spec["kind"] == expected


@pytest.mark.parametrize("name", sorted(CASES))
def test_spec_round_trips_through_json(name):
    # Arrange
    spec = _spec(name)
    # Act
    text = json.dumps(spec, allow_nan=False)
    # Assert
    assert json.loads(text) == spec


@pytest.mark.parametrize("name", sorted(CASES))
def test_spec_validates_against_json_schema(name):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    spec = _spec(name)
    # Act
    errors = list(jsonschema.Draft202012Validator(PLOT_SPEC_JSON_SCHEMA).iter_errors(spec))
    # Assert
    assert errors == []


def test_spec_is_versioned():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    header = (spec["schema"], spec["version"])
    # Assert
    assert header == (SCHEMA_ID, 1)


def test_two_group_bracket_uses_apa_p_text_not_stars():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    text = spec["annotations"]["brackets"][0]["text"]
    # Assert
    assert text == r"$\mathit{p}$ < .001"


def test_stars_are_optional():
    # Arrange
    result = ss.run_test("ttest_ind", data=A, data2=B)
    # Act
    spec = ss.plot_spec(result, data=A, data2=B, stars=True)
    # Assert
    assert spec["annotations"]["brackets"][0]["text"] == "***"


def test_groups_carry_raw_values():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    values = [g["values"] for g in spec["groups"]]
    # Assert
    assert values == [A, B]


def test_n_label_is_italic_mathtext():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    label = spec["groups"][0]["n_text"]
    # Assert
    assert label == r"$\mathit{n}$ = 8"


def test_effect_size_label_carries_symbol_and_ci():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    label = spec["annotations"]["effect_size"]
    # Assert
    assert label == r"$\mathit{d}$ = −3.18, 95% CI [−4.65, −1.70]"


def test_parametric_center_is_mean_ci():
    # Arrange
    spec = _spec("ttest_ind")
    # Act
    center = [layer for layer in spec["layers"] if layer["type"] == "center"][0]["estimator"]
    # Assert
    assert center == "mean_ci"


def test_rank_test_center_is_median_iqr():
    # Arrange
    spec = _spec("mannwhitneyu")
    # Act
    center = [layer for layer in spec["layers"] if layer["type"] == "center"][0]["estimator"]
    # Assert
    assert center == "median_iqr"


def test_paired_spec_has_paired_lines():
    # Arrange
    spec = _spec("ttest_rel")
    # Act
    types = [layer["type"] for layer in spec["layers"]]
    # Assert
    assert "paired_lines" in types


def test_correlation_has_regression_band():
    # Arrange
    spec = _spec("pearson")
    # Act
    reg = [layer for layer in spec["layers"] if layer["type"] == "regression"][0]
    # Assert
    assert len(reg["lower"]) == len(reg["upper"]) == len(reg["x"])


def test_contingency_keeps_counts():
    # Arrange
    spec = _spec("chi2")
    # Act
    counts = spec["table"]["counts"]
    # Assert
    assert counts == [[10.0, 20.0], [30.0, 15.0]]


def test_one_sample_reference_line_at_popmean():
    # Arrange
    spec = _spec("ttest_1samp")
    # Act
    ref = [layer for layer in spec["layers"] if layer["type"] == "reference_line"][0]["value"]
    # Assert
    assert ref == 5.0


def test_omnibus_k_group_draws_no_bracket():
    # Arrange
    spec = _spec("anova")
    # Act
    brackets = spec["annotations"]["brackets"]
    # Assert
    assert brackets == []


def test_posthoc_comparisons_become_stacked_brackets():
    # Arrange
    names = ["A", "B", "C"]
    result = ss.run_test("anova", groups=[A, B, C], group_names=names)
    ph = ss.posthoc.posthoc_tukey([A, B, C], group_names=names, return_as="list")
    # Act
    spec = ss.plot_spec(result, groups=[A, B, C], group_names=names, posthoc=ph)
    # Assert
    assert sorted(b["tier"] for b in spec["annotations"]["brackets"]) == [0, 1, 2]


def test_jitter_is_deterministic():
    # Arrange
    first = _spec("ttest_ind")
    # Act
    second = _spec("ttest_ind")
    # Assert
    assert first["groups"][0]["jitter"] == second["groups"][0]["jitter"]


def test_stack_brackets_keeps_disjoint_spans_on_one_tier():
    # Arrange
    pairs = [(0, 1), (2, 3)]
    # Act
    tiers = stack_brackets(pairs)
    # Assert
    assert tiers == [0, 0]


def test_stack_brackets_lifts_the_enclosing_span():
    # Arrange
    pairs = [(0, 2), (0, 1)]
    # Act
    tiers = stack_brackets(pairs)
    # Assert
    assert tiers == [1, 0]


# EOF
