"""CLI verification reports unverified receipts and invalid JSON without tracebacks."""

import json

import pytest
from click.testing import CliRunner

import scitex_stats as stats
from scitex_stats._cli.verify import verify as verify_command


@pytest.fixture
def valid_result_file(tmp_path):
    result = stats.run_test("ttest_ind", data=[1., 2., 4., 5.], data2=[3., 5., 7., 9.])
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    return path


def test_text_mode_reports_missing_receipt_without_crashing(tmp_path):
    # Arrange
    path = tmp_path / "bare.json"
    path.write_text('{"statistic": 1.0}')
    # Act
    result = CliRunner().invoke(verify_command, [str(path), "--no-json"])
    # Assert
    assert (result.exit_code, type(result.exception).__name__,
            "no provenance receipt" in result.output, "Traceback" in result.output) == (
        1, "SystemExit", True, False,
    )


def test_json_mode_keeps_missing_receipt_unverified(tmp_path):
    # Arrange
    path = tmp_path / "bare.json"
    path.write_text('{"statistic": 1.0}')
    # Act
    result = CliRunner().invoke(verify_command, [str(path)])
    report = json.loads(result.output)
    # Assert
    assert (result.exit_code, report["verified"], report["summary"]) == (
        1, False, "no provenance receipt",
    )


@pytest.mark.parametrize("payload", [b'{"statistic":', b'\xff'])
def test_invalid_result_json_is_an_input_error(tmp_path, payload):
    # Arrange
    path = tmp_path / "invalid.json"
    path.write_bytes(payload)
    # Act
    result = CliRunner().invoke(verify_command, [str(path)])
    # Assert
    assert (result.exit_code, type(result.exception).__name__,
            "RESULT_FILE" in result.output, "Invalid JSON" in result.output,
            "Traceback" in result.output) == (2, "SystemExit", True, True, False)


@pytest.mark.parametrize("payload", [b'{"statistic":', b'\xff'])
def test_invalid_source_json_names_its_option(valid_result_file, tmp_path, payload):
    # Arrange
    source = tmp_path / "invalid source.json"
    source.write_bytes(payload)
    # Act
    result = CliRunner().invoke(verify_command, [str(valid_result_file), "--source-result", str(source)])
    # Assert
    assert (result.exit_code, type(result.exception).__name__,
            "--source-result" in result.output, "Invalid JSON" in result.output,
            "Traceback" in result.output) == (2, "SystemExit", True, True, False)
