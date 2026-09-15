"""APA 7 conformance of recommender strings, checked with the library's validate_apa."""

from __future__ import annotations

from scitex_stats._recommend import recommend_test, run_all_applicable
from scitex_stats._recommend._messages import fmt_alpha, fmt_stat
from scitex_stats._utils._apa import validate_apa


def _rows(data, **kw):
    kw.setdefault("design", "independent")
    return recommend_test(data, **kw)["assumption_checks"]["rows"]


def test_shapiro_w_has_no_leading_zero_and_two_decimals(sample_ui):
    # Arrange
    # Act
    apa = [r["apa"] for r in _rows(sample_ui) if r["check"] == "Shapiro–Wilk"][0]
    # Assert
    assert apa.startswith("W = .97,")


def test_assumption_rows_pass_validate_apa(sample_ui, three_normal_unequal, nonnormal_small):
    # Arrange
    rows = _rows(sample_ui) + _rows(three_normal_unequal) + _rows(nonnormal_small)
    # Diagnostic variance checks carry no effect size; their magnitude is the variance-ratio row.
    waived = {"APA-MISSING-EFFECT"}
    # Act
    bad = [
        (r["apa"], [v for v in validate_apa(r["apa"])["violations"] if v["code"] not in waived])
        for r in rows if r["apa"] and r["symbol"]
    ]
    # Assert
    assert not [b for b in bad if b[1]], bad


def test_thresholds_use_apa_alpha(sample_ui):
    # Arrange
    # Act
    texts = [r["threshold"]["text"] for r in _rows(sample_ui) if r["threshold"]["text"].startswith("p ")]
    # Assert
    assert texts and all(t.startswith("p ≥ .05:") for t in texts)


def test_threshold_texts_pass_validate_apa(sample_ui):
    # Arrange
    texts = [r["threshold"]["text"].split(":")[0] for r in _rows(sample_ui) if r["threshold"]["text"].startswith("p ")]
    # Act
    violations = [v for t in texts for v in validate_apa(t)["violations"]]
    # Assert
    assert violations == []


def test_applicability_reasons_use_apa_alpha(sample_ui):
    # Arrange
    rows = recommend_test(sample_ui, design="independent")["applicability"]
    # Act
    reasons = [x for r in rows for x in r["reasons"] if "Shapiro–Wilk p" in x]
    # Assert
    assert reasons and all("p ≥ .05" in x or "p < .05" in x for x in reasons)


def test_agreement_uses_apa_alpha(sample_ui):
    # Arrange
    # Act
    summary = run_all_applicable(sample_ui, design="independent")["agreement"]["summary"]
    # Assert
    assert "α = .05" in summary


def test_fmt_alpha_keeps_needed_third_decimal():
    # Arrange
    # Act
    text = fmt_alpha(0.005)
    # Assert
    assert text == ".005"


def test_fmt_stat_keeps_leading_zero_for_unbounded_f():
    # Arrange
    # Act
    text = fmt_stat(0.004, "F")
    # Assert
    assert text == "0.00"
