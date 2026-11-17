"""Full-report verification can receive its native source result over CLI/MCP."""

import asyncio
import json
from copy import deepcopy

import pytest
from click.testing import CliRunner

import scitex_stats as stats
from scitex_stats._cli.verify import verify as verify_command
from scitex_stats._mcp._handlers._verify import verify_result_handler
from scitex_stats._mcp.tool_schemas import get_tool_schemas

X = [5.1, 4.9, 6.2, 5.8, 6., 5.5, 5.3, 6.1]
Y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7., 6.6]


@pytest.fixture(scope="module")
def report_pair():
    base = stats.run_test("mannwhitneyu", data=X, data2=Y)
    report = stats.full_report(base, data=X, data2=Y, n_bootstrap=400)
    return base, report


@pytest.mark.parametrize("file_input", [False, True])
def test_mcp_full_report_verifies_with_source_result(report_pair, tmp_path, file_input):
    # Arrange
    base, report = deepcopy(report_pair)
    before = deepcopy((base, report))
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    arguments = {"result_file": str(path)} if file_input else {"result": report}
    # Act
    actual = asyncio.run(verify_result_handler(**arguments, source_result=base))
    # Assert
    assert (actual["success"], actual["verified"],
            {row["status"] for row in actual["checks"]}, (base, report)) == (
        True, True, {"pass"}, before,
    )


@pytest.mark.parametrize("changed", ["source", "report", "data"])
def test_mcp_full_report_keeps_tamper_checks(report_pair, changed):
    # Arrange
    base, report = deepcopy(report_pair)
    arguments = {"result": report, "source_result": base, "data": X.copy()}
    if changed == "source":
        base["statistic"] += 1.
    elif changed == "report":
        report["statistic"] += 1.
    else:
        arguments["data"][0] += 1.
    # Act
    actual = asyncio.run(verify_result_handler(**arguments))
    # Assert
    assert (actual["success"], actual["verified"]) == (True, False)


@pytest.mark.parametrize("supply_source", [False, True])
def test_cli_full_report_source_option_preserves_exit_contract(report_pair, tmp_path, supply_source):
    # Arrange
    base, report = report_pair
    path, source = tmp_path / "report.json", tmp_path / "base.json"
    path.write_text(json.dumps(report))
    source.write_text(json.dumps(base))
    arguments = [str(path)] + (["--source-result", str(source)] if supply_source else [])
    # Act
    result = CliRunner().invoke(verify_command, arguments)
    actual = json.loads(result.output)
    # Assert
    assert (result.exit_code, actual["verified"]) == (0 if supply_source else 1, supply_source)


def test_cli_source_option_keeps_tampered_source_unverified(report_pair, tmp_path):
    # Arrange
    base, report = deepcopy(report_pair)
    base["statistic"] += 1.
    path, source = tmp_path / "report.json", tmp_path / "base.json"
    path.write_text(json.dumps(report))
    source.write_text(json.dumps(base))
    # Act
    result = CliRunner().invoke(verify_command, [str(path), "--source-result", str(source)])
    actual = json.loads(result.output)
    # Assert
    assert (result.exit_code, actual["verified"]) == (1, False)


def test_wire_schema_exposes_optional_source_result():
    # Arrange
    tool = next(t for t in get_tool_schemas() if t.name == "verify_result")
    # Act
    schema = tool.model_dump(by_alias=True)["inputSchema"]
    # Assert
    assert ("source_result" in schema["properties"],
            "source_result" in schema.get("required", [])) == (True, False)
