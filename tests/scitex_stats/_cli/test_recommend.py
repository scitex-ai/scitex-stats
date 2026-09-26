"""CLI: tests check-applicability / recommend-test / execute-all."""

from __future__ import annotations

import json

from click.testing import CliRunner

from scitex_stats._cli import main

SAMPLE_CSV = "a,b\n5.1,6.3\n4.9,6.8\n5.6,6.1\n5.8,7.0\n6.0,6.6\n5.4,6.9\n5.2,6.4\n5.7,7.2\n"


def _invoke(tmp_path, *args):
    path = tmp_path / "data.csv"
    path.write_text(SAMPLE_CSV)
    return CliRunner().invoke(main, ["tests", *args[:1], str(path), *args[1:]])


def test_recommend_test_json_names_welch(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "recommend-test", "--design", "independent")
    # Assert
    assert json.loads(result.stdout)["primary"]["test_id"] == "ttest_welch"


def test_check_applicability_text_marks_tests(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "check-applicability", "--design", "independent", "--no-json")
    # Assert
    assert "✓ Welch's t-test" in result.output


def test_execute_all_text_shows_warning(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "execute-all", "--design", "independent", "--no-json")
    # Assert
    assert "p-hacking" in result.output


def test_execute_all_text_labels_primary(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "execute-all", "--design", "independent", "--no-json")
    # Assert
    assert "[primary    ] Welch's t-test" in result.output


def test_execute_all_non_applicable_primary_reports_error(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "execute-all", "--design", "independent", "--primary", "chi2")
    # Assert
    assert "not applicable" in result.output


def test_deprecated_applicability_spelling_still_answers(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "applicability", "--design", "independent", "--no-json")
    # Assert
    assert "✓ Welch's t-test" in result.output


def test_deprecated_run_all_spelling_still_answers(tmp_path):
    # Arrange
    # Act
    result = _invoke(tmp_path, "run-all", "--design", "independent", "--no-json")
    # Assert
    assert "p-hacking" in result.output
