#!/usr/bin/env python3
"""Tests for the report model (`reporting/_pdf/_build.py`): sections, content, determinism, offline."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from scitex_stats.reporting._pdf import (
    SECTIONS,
    build_report,
    model_text,
    render_html,
    render_markdown,
)

THREE = {"Control": [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], "Drug A": [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2],
         "Drug B": [5.9, 6.2, "", 6.0, 5.8, "n/a", 6.4, 6.1]}
TWO = [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]]
NULL3 = [[5.1, 5.3, 4.9, 5.2, 5.0, 5.1], [5.0, 5.2, 5.1, 4.8, 5.3, 5.0], [5.2, 4.9, 5.1, 5.0, 5.2, 5.1]]
STAMP = "2026-01-01T00:00:00Z"


@pytest.fixture(scope="module")
def three_model():
    return build_report(THREE, "between", timestamp=STAMP)


def _section(model, sid):
    return next(s for s in model["sections"] if s["id"] == sid)


def _text(blocks):
    return model_text({"title": "", "subtitle": "", "sections": [{"title": "", "blocks": blocks}]})


def test_sections_come_in_the_documented_order(three_model):
    # Arrange
    expected = [title for _, title in SECTIONS]
    # Act
    titles = [s["title"] for s in three_model["sections"]]
    # Assert
    assert titles == expected


def test_excluded_cells_are_listed_with_reasons(three_model):
    # Arrange
    data = _section(three_model, "data")
    # Act
    text = _text(data["blocks"])
    # Assert
    assert "empty cell" in text and "non-numeric value 'n/a'" in text


def test_auto_posthoc_follows_the_recommender_welch_then_games_howell(three_model):
    """The report does not pick a post-hoc itself: the recommender's primary test decides.

    The recommender defaults to Welch's ANOVA and never switches test on the strength
    of an assumption check, so the matching correction is Games-Howell (which does not
    assume equal variances), not Tukey.
    """
    # Arrange
    summary = three_model["summary"]
    # Act
    ph = summary["posthoc"]
    # Assert
    assert (summary["primary_test"], ph["method"], ph["ran"]) == ("welch_anova", "games_howell", True)


def test_posthoc_table_shows_adjusted_p_and_correction(three_model):
    # Arrange
    ph = _section(three_model, "posthoc")
    # Act
    text = _text(ph["blocks"])
    # Assert
    assert "p (adjusted)" in text and "Multiplicity correction: Games\u2013Howell" in text


def test_sensitivity_section_is_labelled_and_warns_about_p_hacking(three_model):
    # Arrange
    sens = _section(three_model, "sensitivity")
    # Act
    text = _text(sens["blocks"])
    # Assert
    assert "SENSITIVITY ANALYSIS" in text and "p-hacking" in text


def test_methods_paragraph_names_test_alpha_and_seed(three_model):
    # Arrange
    methods = _section(three_model, "methods")
    # Act
    text = _text(methods["blocks"])
    # Assert
    assert "one-way analysis of variance" in text and "α = .05" in text and "seed 42" in text


def test_references_include_apa_manual_and_the_chosen_procedure(three_model):
    # Arrange
    refs = _section(three_model, "references")
    # Act
    text = _text(refs["blocks"])
    # Assert
    assert "American Psychological Association. (2020)" in text and "Games, P. A., & Howell, J. F. (1976)" in text


def test_statistical_symbols_are_italic_in_html(three_model):
    # Arrange
    html = render_html(three_model)
    # Act
    italic_p = '<i class="sym">p</i>' in html
    # Assert
    assert italic_p


def test_figure_is_svg_with_brackets_for_significant_pairs(three_model):
    # Arrange
    fig = _section(three_model, "figures")["blocks"][0]
    # Act
    brackets = fig["spec"]["annotations"]["brackets"]
    # Assert
    assert fig["svg"].lstrip().startswith("<?xml") and len(brackets) >= 1


def test_same_input_gives_identical_html():
    # Arrange
    first = render_html(build_report(THREE, "between", timestamp=STAMP))
    # Act
    second = render_html(build_report(THREE, "between", timestamp=STAMP))
    # Assert
    assert first == second


def test_only_the_timestamp_differs_between_runs():
    # Arrange
    first = model_text(build_report(TWO, "between")).splitlines()
    # Act
    second = model_text(build_report(TWO, "between")).splitlines()
    # Assert
    assert [a for a, b in zip(first, second) if a != b and not a.startswith("Generated (UTC)")] == []


_OFFLINE_SCRIPT = """
import sys
def guard(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.bind", "urllib.Request"):
        raise RuntimeError("network access attempted: " + event)
sys.addaudithook(guard)
from scitex_stats.reporting._pdf import report
out = report([[5.1, 4.9, 5.6, 5.8, 6.0], [6.3, 6.8, 6.1, 7.0, 6.6], [5.9, 6.2, 6.0, 5.8, 6.4]],
             output=None, formats=["html", "md"] + (["pdf"] if "--pdf" in sys.argv else []))
print("OFFLINE-OK", out["summary"]["primary_test"])
"""


def test_report_builds_without_network(tmp_path):
    # Arrange: a Python audit hook that raises on any socket or URL activity
    from scitex_stats.reporting._pdf import pdf_renderer

    script = tmp_path / "offline.py"
    script.write_text(_OFFLINE_SCRIPT, encoding="utf-8")
    args = [sys.executable, str(script)] + (["--pdf"] if pdf_renderer() else [])
    # Act
    proc = subprocess.run(args, capture_output=True, text=True, timeout=240, env={**os.environ, "MPLBACKEND": "Agg"})
    # Assert
    assert "OFFLINE-OK" in proc.stdout, proc.stderr[-2000:]


def test_non_significant_omnibus_reports_posthoc_not_run():
    # Arrange
    model = build_report(NULL3, "between", timestamp=STAMP)
    # Act
    ph = model["summary"]["posthoc"]
    # Assert
    assert (ph["ran"], ph["omnibus_significant"]) == (False, False)


def test_posthoc_always_flags_non_significant_omnibus():
    # Arrange
    model = build_report(NULL3, "between", posthoc="always", timestamp=STAMP)
    # Act
    flags = model["summary"]["posthoc"]["flags"]
    # Assert
    assert flags == ["omnibus_not_significant"]


def test_two_groups_have_no_posthoc():
    # Arrange
    model = build_report(TWO, "between", timestamp=STAMP)
    # Act
    ph = model["summary"]["posthoc"]
    # Assert
    assert ph is None


def test_within_design_excludes_incomplete_rows_listwise():
    # Arrange
    data = {"Pre": [1.0, 2.0, 3.1, 4.2, 5.0, 6.1], "Post": [1.5, None, 3.9, 4.8, 5.9, 6.4]}
    # Act
    model = build_report(data, "within", timestamp=STAMP)
    # Assert
    assert model["summary"]["n"] == [5, 5]


def test_japanese_group_names_survive_into_markdown():
    # Arrange
    model = build_report({"対照群": TWO[0], "薬剤群": TWO[1]}, "between", timestamp=STAMP)
    # Act
    md = render_markdown(model)
    # Assert
    assert "対照群" in md


def test_single_group_is_rejected():
    # Arrange
    data = {"Only": [1.0, 2.0, 3.0]}
    # Act
    def call():
        return build_report(data, "between")

    # Assert
    with pytest.raises(ValueError, match="at least 2 groups"):
        call()


def test_a_report_with_japanese_names_warns_when_no_cjk_font_is_installed():
    """The warning is measured, not assumed: it is present exactly when the text
    needs a CJK font and the machine has none."""
    # Arrange
    from scitex_stats.reporting._pdf._fonts import cjk_font_available

    model = build_report({"対照群": [5.1, 4.9, 5.6, 5.8], "Drug A": [6.3, 6.8, 6.1, 7.0]}, "between", timestamp=STAMP)
    # Act
    text = _text(_section(model, "meta")["blocks"])
    # Assert
    assert ("no CJK font is installed" in text) == (not cjk_font_available())


def test_long_within_design_pairs_by_subject_id(tmp_path):
    """The reported reproduction: subject ids were sorted and then discarded, so a
    missing cell paired subject 2's A with subject 4's B. Both conditions keep
    subjects 1 and 3 here, and the dropped ones are reported."""
    # Arrange
    rows = ["subject,condition,score",
            "1,A,1.0", "2,A,2.0", "3,A,3.0",
            "1,B,11.0", "3,B,13.0", "4,B,14.0"]
    path = tmp_path / "long.csv"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    # Act
    model = build_report(str(path), {"type": "within", "group_col": "condition", "value_col": "score",
                                     "subject_col": "subject"}, timestamp=STAMP)
    text = _text(_section(model, "data")["blocks"])
    # Assert
    assert ("A | 2 | 1 | 2.00" in text, "B | 2 | 1 | 12.00" in text, "subject has no cell in every condition" in text) == (True, True, True)


def test_the_input_hash_covers_the_raw_cells_not_the_normalized_values():
    """The reported reproduction: invalid raw values were replaced by NaN before
    hashing, so inputs differing only as "foo" versus "bar" produced the same digest
    while their exclusion records differed. The shown digest is now the RAW input's,
    and the normalized analysis data is hashed separately."""
    # Arrange
    # Act
    a = build_report({"A": [1, 2, "foo", 4], "B": [2, 3, 4, 5]}, "between", timestamp=STAMP)
    b = build_report({"A": [1, 2, "bar", 4], "B": [2, 3, 4, 5]}, "between", timestamp=STAMP)
    again = build_report({"A": [1, 2, "foo", 4], "B": [2, 3, 4, 5]}, "between", timestamp=STAMP)
    # Assert
    assert (a["summary"]["input_sha256"] != b["summary"]["input_sha256"],
            a["summary"]["input_sha256"] == again["summary"]["input_sha256"]) == (True, True)


def test_the_report_shows_both_digests_with_their_labels():
    """The user-visible half of the provenance fix: the meta section must say which
    hash is which, so a reader can tell the raw input's digest from the analysis
    data's."""
    # Arrange
    model = build_report(THREE, "between", timestamp=STAMP)
    # Act
    text = _text(_section(model, "meta")["blocks"])
    # Assert
    assert ("Input SHA-256" in text, "Analysis data SHA-256" in text, model["summary"]["input_sha256"][:12] in text) == (True, True, True)


# EOF
