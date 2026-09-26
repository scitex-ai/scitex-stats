#!/usr/bin/env python3
"""apa_render: exact APA 7 lines, italic symbols, tables and descriptives."""

import pytest

from .conftest import A, CASES

from scitex_stats._utils._apa import apa_render


@pytest.mark.parametrize("name", list(CASES))
def test_apa_line_matches_exact_apa7_string(results, expected, name):
    # Arrange
    want = expected[name]
    # Act
    plain = results[name]["apa"]["plain"]
    # Assert
    assert plain == want


@pytest.mark.parametrize(
    "name, fragments",
    [
        (
            "ttest_ind",
            [
                '<i class="stx-sym">t</i>(14) = −6.35',
                '<i class="stx-sym">p</i> &lt; .001',
                '<i class="stx-sym">n</i><sub>1</sub> = 8',
            ],
        ),
        ("spearman", ['<i class="stx-sym">r</i><sub>s</sub>(6)']),
        ("chi2", ['<span class="stx-sym stx-sym--greek">χ</span><sup>2</sup>(1, <i class="stx-sym">N</i> = 30)']),
        ("friedman", ['χ</span><sup>2</sup><sub>F</sub>(2, <i class="stx-sym">N</i> = 8)']),
    ],
)
def test_html_italicizes_latin_and_keeps_greek_and_subscripts_upright(results, name, fragments):
    # Arrange
    html = results[name]["apa"]["html"]
    # Act
    missing = [f for f in fragments if f not in html]
    # Assert
    assert missing == []


def test_no_significance_asterisks_in_any_inline_line(results):
    # Arrange
    lines = [r["apa"]["plain"] for r in results.values()]
    # Act
    starred = [line for line in lines if "*" in line or " ns" in line]
    # Assert
    assert starred == []


def test_table_has_df_row_and_labelled_group_sizes(results):
    # Arrange
    rows = results["ttest_ind"]["apa"]["table"]
    # Act
    labels = {r["label_plain"]: r["value_plain"] for r in rows}
    # Assert
    assert (labels["Degrees of freedom (df)"], labels["n₁ (x)"], labels["n₂ (y)"]) == ("14", "8", "8")


def test_table_keeps_exact_p_beside_apa_p(results):
    # Arrange
    rows = results["ttest_ind"]["apa"]["table"]
    # Act
    values = {r["key"]: r["value_plain"] for r in rows}
    # Assert
    assert (values["p"], values["p_exact"]) == ("< .001", "1.79 × 10⁻⁵")


def test_descriptives_line_reports_n_mean_sd_per_group(results):
    # Arrange
    desc = results["ttest_ind"]["apa"]["descriptives"]
    # Act
    plain = desc["plain"]
    # Assert
    assert plain == "x (n = 8, M = 5.46, SD = 0.38); y (n = 8, M = 6.66, SD = 0.38)"


def test_rank_tests_describe_groups_with_median_and_iqr(results):
    # Arrange
    desc = results["mannwhitneyu"]["apa"]["descriptives"]
    # Act
    header = [c[0]["text"] for c in desc["columns"]]
    # Assert
    assert header == ["Group", "n", "Mdn", "IQR"]


def test_symbols_in_table_labels_and_descriptives_are_italic(results):
    # Arrange
    apa = results["ttest_ind"]["apa"]
    segs = [s for r in apa["table"] for s in r["label"]] + apa["descriptives"]["segments"]
    # Act
    upright = [s["text"] for s in segs if s["kind"] == "text" and s["text"].strip() in {"t", "p", "n", "M", "SD", "df", "d"}]
    # Assert
    assert upright == []


def test_raw_p_value_is_not_rounded_at_source(results):
    # Arrange
    p = results["mannwhitneyu"]["pvalue"]
    # Act
    decimals = len(repr(p).split(".")[1])
    # Assert
    assert decimals > 3


def test_one_sample_cohens_d_is_relative_to_popmean(results):
    # Arrange
    res = results["ttest_1samp"]
    # Act
    d = res["effect_size"]
    # Assert
    assert d == pytest.approx((sum(A) / 8 - 5) / 0.37773, rel=1e-3)


def test_render_of_non_result_is_none():
    # Arrange
    value = "not a result"
    # Act
    rendered = apa_render(value)
    # Assert
    assert rendered is None


def test_html_escapes_untrusted_metric():
    # Arrange
    result = {
        "statistic": 1.0,
        "pvalue": 0.5,
        "effect_size": 0.1,
        "effect_size_metric": "<script>",
        "stat_symbol": "<script>",
    }
    # Act
    html = apa_render(result)["html"]
    # Assert
    assert "<script>" not in html
