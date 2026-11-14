"""Qualify real native/MCP verification mapping with default native options."""

import asyncio
import copy
import json

import pytest
import scitex_stats as stats
from scitex_stats import _server

X = [5.1, 4.9, 6.2, 5.8, 6.0, 5.5, 5.3, 6.1]
Y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7.0, 6.6]
MODES = ("embedded", "supplied", "groups", "file", "tampered", "wrong_data", "no_receipt")


def arguments(mode, temporary):
    result = stats.run_test("ttest_ind", data=X, data2=Y)
    tool = {"result": result, "result_file": None, "data": None, "data2": None, "groups": None}
    verified = True
    if mode == "supplied":
        tool.update(data=X.copy(), data2=Y.copy())
    elif mode == "groups":
        groups = [X, Y, [4.0, 5.5, 5.0, 6.5]]
        tool.update(result=stats.run_test("anova", groups=groups), groups=groups)
    elif mode == "file":
        path = temporary / "result.json"
        path.write_text(json.dumps(result, default=str))
        tool.update(result=None, result_file=str(path))
    elif mode == "tampered":
        result["pvalue"] = .5
        verified = False
    elif mode == "wrong_data":
        tool.update(data=X + [100.0], data2=Y.copy())
        verified = False
    elif mode == "no_receipt":
        tool["result"] = {}
        verified = False
    native = {name: tool[name] for name in ("data", "data2", "groups")}
    native["result"] = tool["result"] if tool["result"] is not None else tool["result_file"]
    return tool, native, verified


def call_tool(kwargs):
    function = getattr(_server.verify_result, "fn", _server.verify_result)
    return json.loads(asyncio.run(function(**kwargs)))


@pytest.mark.parametrize("mode", MODES)
def test_verify_tool_runs_native_verification_in_worker_with_default_options(mode, tmp_path, observe_native):
    # Arrange
    tool, native, verified = arguments(mode, tmp_path)
    expected = {**native, "source_result": None, "recompute": True}
    # Act
    with observe_native(stats.verify) as calls:
        report = call_tool(tool)
    observed = [{key: call[key] for key in expected} for call in calls]
    # Assert
    assert (report["success"], report["verified"], observed) == (True, verified, [expected])


@pytest.mark.parametrize("mode", MODES)
def test_verify_tool_preserves_complete_native_payload(mode, tmp_path):
    # Arrange
    tool, native, _ = arguments(mode, tmp_path)
    expected = stats.verify(**native)
    # Act
    report = call_tool(tool)
    # Assert
    assert report == {"success": True, **expected}


def bad_arguments(mode, temporary):
    path = temporary / "bad-result.json"
    kwargs = {}
    message = "Provide exactly one"
    if mode == "both":
        kwargs = {"result": {}, "result_file": str(path)}
    elif mode == "malformed":
        path.write_text("not json")
        kwargs, message = {"result_file": str(path)}, "Expecting value"
    elif mode == "absent":
        kwargs, message = {"result_file": str(path)}, "No such file"
    return kwargs, message


@pytest.mark.parametrize("mode", ["missing", "both", "malformed", "absent"])
def test_verify_tool_preserves_transport_failures_for_source_and_file_errors(mode, tmp_path):
    # Arrange
    kwargs, message = bad_arguments(mode, tmp_path)
    # Act
    report = call_tool(kwargs)
    # Assert
    assert (set(report), report.get("success"), message in report.get("error", "")) == ({"success", "error"}, False, True)


def test_verify_tool_does_not_modify_receipt_or_supplied_data(tmp_path):
    # Arrange
    tool, _, _ = arguments("supplied", tmp_path)
    before = copy.deepcopy(tool)
    # Act
    report = call_tool(tool)
    # Assert
    assert (tool, report["success"], report["verified"]) == (before, True, True)


def test_native_hash_only_verification_remains_incomplete(tmp_path):
    # Arrange
    _, native, _ = arguments("embedded", tmp_path)
    # Act
    report = stats.verify(**native, recompute=False)
    # Assert
    assert (report["verified"], {item["name"]: item["status"] for item in report["checks"]}) == (False, {"receipt": "pass", "result": "pass", "inputs": "pass", "recompute": "skip"})


def test_cli_hash_only_verification_returns_incomplete_report_and_exit_one(tmp_path):
    # Arrange
    from click.testing import CliRunner
    from scitex_stats._cli.verify import verify as command
    tool, _, _ = arguments("file", tmp_path)
    # Act
    result = CliRunner().invoke(command, [tool["result_file"], "--no-recompute"])
    report = json.loads(result.stdout)
    # Assert
    assert (result.exit_code, report["verified"], {item["name"]: item["status"] for item in report["checks"]}["recompute"]) == (1, False, "skip")
