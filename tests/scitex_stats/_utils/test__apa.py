#!/usr/bin/env python3
"""APA rendering: italic Latin symbols, p < .001, no leading zero, real minus."""

import pytest

from scitex_stats import run_test
from scitex_stats._utils._apa import MINUS, apa_render, format_number, format_p

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]


@pytest.mark.parametrize(
    "p, expected",
    [(0.00001, "< .001"), (0.0421, "= .042"), (1.0, "> .999")],
)
def test_format_p_follows_apa_relation_without_leading_zero(p, expected):
    # Arrange
    value = p
    # Act
    text = format_p(value)
    # Assert
    assert text == expected


@pytest.mark.parametrize(
    "value, leading_zero, expected",
    [(-6.3542, True, MINUS + "6.354"), (-0.0001, True, "0.000"), (0.239, False, ".239")],
)
def test_format_number_uses_real_minus_and_optional_leading_zero(value, leading_zero, expected):
    # Arrange
    kwargs = {"leading_zero": leading_zero}
    # Act
    text = format_number(value, **kwargs)
    # Assert
    assert text == expected


@pytest.fixture(scope="module")
def ttest_apa():
    return run_test("ttest_ind", data=A, data2=B)["apa"]


def test_ttest_plain_summary_is_apa(ttest_apa):
    # Arrange
    expected = f"t = {MINUS}6.354, p < .001, Cohen's d = {MINUS}3.177, ***"
    # Act
    text = ttest_apa["plain"]
    # Assert
    assert text == expected


@pytest.mark.parametrize(
    "fragment",
    ['<i class="stx-sym">t</i> = ', '<i class="stx-sym">p</i> &lt; .001', 'Cohen&#x27;s <i class="stx-sym">d</i>'],
)
def test_ttest_html_italicizes_only_symbols(ttest_apa, fragment):
    # Arrange
    html = ttest_apa["html"]
    # Act
    found = fragment in html
    # Assert
    assert found


def test_ttest_latex_wraps_symbols_in_math(ttest_apa):
    # Arrange
    latex = ttest_apa["latex"]
    # Act
    head = latex[: len("$t$ = $-$6.354, $p$ $<$ .001")]
    # Assert
    assert head == "$t$ = $-$6.354, $p$ $<$ .001"


def test_formatted_key_is_unchanged_for_existing_callers():
    # Arrange
    kwargs = {"data": A, "data2": B}
    # Act
    res = run_test("ttest_ind", **kwargs)
    # Assert
    assert res["formatted"].startswith("t = -6.354, p = 0.0000")


def test_pearson_drops_leading_zero_and_duplicate_effect():
    # Arrange
    kwargs = {"data": A, "data2": B}
    # Act
    apa = run_test("pearson", **kwargs)["apa"]
    # Assert
    assert apa["plain"] == "r = .239, p = .569, ns"


def test_spearman_statistic_is_upright_rho():
    # Arrange
    kwargs = {"data": A, "data2": B}
    # Act
    apa = run_test("spearman", **kwargs)["apa"]
    # Assert
    assert apa["stat_symbol"] == [{"text": "ρ", "kind": "greek"}]


def test_anova_carries_df_and_eta_squared():
    # Arrange
    groups = [A, B]
    # Act
    apa = run_test("anova", groups=groups)["apa"]
    # Assert
    assert apa["plain"].startswith("F(1, 14) = 40.370, p < .001, η² = .743")


def test_html_escapes_untrusted_metric():
    # Arrange
    result = {"statistic": 1.0, "pvalue": 0.5, "effect_size": 0.1,
              "effect_size_metric": "<script>", "stat_symbol": "t"}
    # Act
    html = apa_render(result)["html"]
    # Assert
    assert "<script>" not in html
