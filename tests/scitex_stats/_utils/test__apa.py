#!/usr/bin/env python3
"""APA 7 rendering per test: exact lines, symbols, table rows, validator agreement."""

import pytest

from scitex_stats import run_test
from scitex_stats._utils._apa import (
    MINUS,
    RULES,
    apa_render,
    format_number,
    format_p,
    rule_by_key,
    validate_apa,
)

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]
B2 = [6.3, 4.8, 7.1, 7.9, 5.6, 6.9, 8.4, 5.2]
C = [5.9, 6.2, 5.5, 6.4, 6.1, 5.8, 6.0, 6.3]
TABLE = [[12, 5], [4, 9]]

CASES = {
    "ttest_ind": dict(data=A, data2=B),
    "ttest_welch": dict(data=A, data2=B2),
    "ttest_rel": dict(data=A, data2=B),
    "ttest_1samp": dict(data=A, popmean=5),
    "mannwhitneyu": dict(data=A, data2=B2),
    "brunner_munzel": dict(data=A, data2=B2),
    "ks_2samp": dict(data=A, data2=B2),
    "ks_1samp": dict(data=A),
    "wilcoxon": dict(data=A, data2=B2),
    "anova": dict(groups=[A, B, C]),
    "kruskal": dict(groups=[A, B, C]),
    "friedman": dict(groups=[A, B, C]),
    "pearson": dict(data=A, data2=B),
    "spearman": dict(data=A, data2=B),
    "kendall": dict(data=A, data2=B),
    "shapiro": dict(data=A),
    "chi2": dict(groups=TABLE),
    "fisher": dict(groups=TABLE),
}

EXPECTED = {
    "ttest_ind": "t(14) = −6.35, p < .001, d = −3.18, 95% CI [−4.65, −1.70], n₁ = 8, n₂ = 8",
    "ttest_welch": "t(8.21) = −2.25, p = .054, d = −1.12, 95% CI [−2.18, −0.07], n₁ = 8, n₂ = 8",
    "ttest_rel": "t(7) = −7.28, p < .001, d_z = −2.58, 95% CI [−4.01, −1.14], n = 8",
    "ttest_1samp": "t(7) = 3.46, p = .011, d = 1.22, 95% CI [0.31, 2.14], n = 8",
    "mannwhitneyu": "U = 17.00, z = −1.58, p = .127, r_rb = −.47, n₁ = 8, n₂ = 8",
    "brunner_munzel": "W_BM(8.06) = 1.61, p = .145, P(X > Y) = .25, n₁ = 8, n₂ = 8",
    "ks_2samp": "D = .62, p = .087, n₁ = 8, n₂ = 8",
    "ks_1samp": "D = 1.00, p < .001, n = 8",
    "wilcoxon": "T = 6.00, z = −1.68, p = .102, r_rb = −.67, n = 8",
    "anova": "F(2, 21) = 23.36, p < .001, η² = .69, N = 24",
    "kruskal": "H(2) = 16.72, p < .001, ε² = .70, N = 24",
    "friedman": "χ²_F(2, N = 8) = 14.25, p < .001, W = .89",
    "pearson": "r(6) = .24, 95% CI [−.56, .81], p = .569",
    "spearman": "rₛ(6) = .33, p = .420",
    "kendall": "τ_b = .21, p = .548, N = 8",
    "shapiro": "W = .97, p = .921, n = 8",
    "chi2": "χ²(1, N = 30) = 3.23, p = .072, V = .33",
    "fisher": "p = .063, OR = 5.40, 95% CI [1.12, 26.04], N = 30",
}


@pytest.fixture(scope="module")
def results():
    return {name: run_test(name, **kwargs) for name, kwargs in CASES.items()}


@pytest.mark.parametrize("name", list(CASES))
def test_apa_line_matches_exact_apa7_string(results, name):
    # Arrange
    expected = EXPECTED[name]
    # Act
    plain = results[name]["apa"]["plain"]
    # Assert
    assert plain == expected


@pytest.mark.parametrize("name", list(CASES))
def test_rule_table_example_is_the_rendered_line(results, name):
    # Arrange
    rule = rule_by_key(results[name]["apa"]["rule"])
    # Act
    example = rule.example
    # Assert
    assert example == results[name]["apa"]["plain"]


def test_every_rule_is_exercised_by_a_case(results):
    # Arrange
    keys = {r.key for r in RULES}
    # Act
    covered = {res["apa"]["rule"] for res in results.values()}
    # Assert
    assert keys == covered


@pytest.mark.parametrize("name", list(CASES))
def test_formatter_output_passes_validator(results, name):
    # Arrange
    apa = results[name]["apa"]
    # Act
    report = validate_apa(apa["plain"], html=apa["html"], result=results[name])
    # Assert
    assert report["violations"] == []


@pytest.mark.parametrize(
    "name, fragments",
    [
        ("ttest_ind", ['<i class="stx-sym">t</i>(14) = −6.35', '<i class="stx-sym">p</i> &lt; .001',
                       '<i class="stx-sym">n</i><sub>1</sub> = 8']),
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


@pytest.mark.parametrize("p, expected", [(0.0, "< .001"), (0.00001, "< .001"), (0.0421, "= .042"), (1.0, "> .999")])
def test_format_p_never_prints_zero_or_leading_zero(p, expected):
    # Arrange
    value = p
    # Act
    text = format_p(value)
    # Assert
    assert text == expected


@pytest.mark.parametrize("value, leading_zero, expected", [(-6.3542, True, MINUS + "6.35"), (-0.001, True, "0.00"), (0.239, False, ".24")])
def test_format_number_two_decimals_real_minus_optional_zero(value, leading_zero, expected):
    # Arrange
    kwargs = {"leading_zero": leading_zero}
    # Act
    text = format_number(value, **kwargs)
    # Assert
    assert text == expected


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


@pytest.mark.parametrize(
    "text, code",
    [
        ("t(14) = -6.354, p = 0.0000, d = 3.2, n = 16", "APA-P-ZERO"),
        ("t(14) = -6.35, p < .001, d = -3.18, n = 16", "APA-MINUS"),
        ("t = 6.35, p < .001, d = 3.18, n = 16", "APA-MISSING-DF"),
        ("t(14) = 6.354, p < .001, d = 3.18, n = 16", "APA-DECIMALS"),
        ("r(28) = 0.45, p = .012", "APA-LEADING-ZERO"),
        ("t(14) = 2.35, p = 0.032, d = 0.90, n = 16", "APA-LEADING-ZERO"),
        ("t(14) = 2.35, p = .032, d = .90, n = 16", "APA-MISSING-ZERO"),
        ("t(14) = 2.35, p = .032*, d = 0.90, n = 16", "APA-ASTERISK"),
        ("χ²(2) = 5.12, p = .077, V = .29", "APA-CHI2-N"),
        ("F(2) = 4.51, p = .020, η² = .25, N = 30", "APA-DF-PAIR"),
        ("t(14) = 2.35, p = .032, n = 16", "APA-MISSING-EFFECT"),
        ("t(14) = 2.35, p = .032, d = 0.90", "APA-MISSING-N"),
        ("U = 12.00, z = −2.35, p = .0192, r_rb = .59, n₁ = 8, n₂ = 8", "APA-P-DECIMALS"),
        ("t(14) = 2.35, p=.032, d = 0.90, n = 16", "APA-SPACING"),
    ],
)
def test_validator_flags_bad_strings(text, code):
    # Arrange
    report_text = text
    # Act
    codes = {v["code"] for v in validate_apa(report_text)["violations"]}
    # Assert
    assert code in codes


@pytest.mark.parametrize(
    "html, code",
    [
        ("t(14) = 2.35, <i>p</i> = .032, <i>d</i> = 0.90, <i>n</i> = 16", "APA-NOT-ITALIC"),
        ("<i>χ</i><sup>2</sup>(1, <i>N</i> = 30) = 3.23, <i>p</i> = .072, <i>V</i> = .33", "APA-GREEK-ITALIC"),
    ],
)
def test_validator_checks_italics_in_html(html, code):
    # Arrange
    markup = html
    # Act
    codes = {v["code"] for v in validate_apa(html=markup)["violations"]}
    # Assert
    assert code in codes


def test_render_of_non_result_is_none():
    # Arrange
    value = "not a result"
    # Act
    rendered = apa_render(value)
    # Assert
    assert rendered is None


def test_html_escapes_untrusted_metric():
    # Arrange
    result = {"statistic": 1.0, "pvalue": 0.5, "effect_size": 0.1,
              "effect_size_metric": "<script>", "stat_symbol": "<script>"}
    # Act
    html = apa_render(result)["html"]
    # Assert
    assert "<script>" not in html
