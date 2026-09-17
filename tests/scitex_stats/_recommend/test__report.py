"""Explicit assumption-check section: per-sample statistics, thresholds, neutral note, Q-Q data."""

from __future__ import annotations

from scitex_stats._recommend import recommend_test
from scitex_stats._utils._apa import validate_apa


def _section(data, **kw):
    kw.setdefault("design", "independent")
    return recommend_test(data, **kw)["assumption_checks"]


def test_shapiro_row_per_group(sample_ui):
    # Arrange
    # Act
    rows = [r for r in _section(sample_ui)["rows"] if r["check"] == "Shapiro–Wilk"]
    # Assert
    assert [r["sample"] for r in rows] == ["Group 1", "Group 2"]


def test_shapiro_rows_carry_w_and_p(sample_ui):
    # Arrange
    # Act
    rows = [r for r in _section(sample_ui)["rows"] if r["check"] == "Shapiro–Wilk"]
    # Assert
    assert all(r["symbol"] == "W" and r["statistic"] is not None and r["p"] is not None for r in rows)


def test_brown_forsythe_and_levene_rows_carry_f_df_p(sample_ui):
    # Arrange
    # Act
    rows = {r["check"]: r for r in _section(sample_ui)["rows"]}
    # Assert
    assert rows["Brown–Forsythe"]["df"] == [1, 14] and rows["Levene"]["p"] is not None


def test_every_row_states_its_threshold(sample_ui):
    # Arrange
    # Act
    rows = _section(sample_ui)["rows"]
    # Assert
    assert all(r["threshold"]["text"] for r in rows)


def test_expected_count_row_for_tables(small_expected_table):
    # Arrange
    # Act
    rows = _section(small_expected_table, scale="categorical")["rows"]
    # Assert
    assert [r["decision"] for r in rows if r["check"] == "Minimum expected count"] == ["not met"]


def test_diagnostic_note_mentions_multiplicity_and_visual_check(sample_ui):
    # Arrange
    # Act
    text = _section(sample_ui)["notes"][0]["text"]
    # Assert
    assert "multiplicity" in text and "Q-Q" in text


def test_welch_default_note_present_for_welch(sample_ui):
    # Arrange
    # Act
    notes = [n["text"] for n in _section(sample_ui)["notes"]]
    # Assert
    assert any("not used to switch tests" in n for n in notes)


def test_welch_default_note_absent_for_rank_test(nonnormal_small):
    # Arrange
    # Act
    notes = [n["text"] for n in _section(nonnormal_small)["notes"]]
    # Assert
    assert not any("not used to switch tests" in n for n in notes)


def test_qq_coordinates_per_sample(sample_ui):
    # Arrange
    # Act
    qq = _section(sample_ui)["qq"]
    # Assert
    assert [len(q["observed"]) for q in qq] == [8, 8]


def test_paired_qq_uses_differences(paired_normal):
    # Arrange
    # Act
    qq = _section(paired_normal, design="paired")["qq"]
    # Assert
    assert [q["sample"] for q in qq] == ["differences"]


def _rows(data, **kw):
    return _section(data, **kw)["rows"]


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
        for r in rows
        if r["apa"] and r["symbol"]
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
