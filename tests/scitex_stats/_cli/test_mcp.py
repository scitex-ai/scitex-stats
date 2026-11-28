"""Direct tests for `scitex_stats._cli.mcp`.

The integration test_cli.py exercises `mcp list-tools` and `mcp
doctor` via subprocess, but several branches xfail because the CLI
uses internals that broke in FastMCP 3.x (`_tool_manager`). These
tests cover the parts that don't depend on that API:

- `_get_tool_module` (pure dispatch by name)
- `_style` (no-op when stdout isn't a tty)
- `_format_tool_signature` (with a duck-typed fake tool)
- `cmd_start(dry_run=True)` (no real server start)
- `cmd_config` (text + JSON snippets)
- `cmd_doctor` (returns 0 or 1; doesn't crash)
"""

from __future__ import annotations

import importlib
import json

import pytest

# `from scitex_stats._cli import mcp` resolves to the Click `mcp`
# Group that `_cli/__init__.py` rebinds at line ~138, not the
# `_cli/mcp.py` module file. Reach the file under its package path.
cli_mcp = importlib.import_module("scitex_stats._cli.mcp")

# ----- _get_tool_module ------------------------------------------------- #


@pytest.mark.parametrize(
    "tool_name,expected_module",
    [
        ("recommend_tests", "auto"),
        ("correct_pvalues", "correct"),
        ("posthoc_test", "posthoc"),
        ("power_analysis", "power"),
        ("effect_size", "effect_sizes"),
        ("normality_test", "normality"),
        ("describe_data", "descriptive"),
        ("format_results", "formatting"),
        ("p_to_stars", "formatting"),
        ("run_test", "general"),
    ],
)
def test_get_tool_module_dispatch(tool_name, expected_module):
    # Arrange
    # Act
    # Assert
    assert cli_mcp._get_tool_module(tool_name) == expected_module


# ----- _style ----------------------------------------------------------- #


def test_style_passthrough_when_not_tty_hello_cli_mcp(capsys):
    # Running under pytest, sys.stdout isn't a tty → _style returns text as-is
    # Arrange
    # Act
    # Assert
    assert cli_mcp._style("hello") == "hello"

def test_style_passthrough_when_not_tty_hello_cli_mcp_green(capsys):
    # Running under pytest, sys.stdout isn't a tty → _style returns text as-is
    # Arrange
    # Act
    # Assert
    assert cli_mcp._style("hello", fg="green", bold=True) == "hello"


# ----- _format_tool_signature ------------------------------------------ #


class _FakeTool:
    """Duck-typed stand-in for a fastmcp Tool."""

    def __init__(self, name, parameters, fn=None, description=None):
        self.name = name
        self.parameters = parameters
        self.fn = fn
        self.description = description


def test_format_tool_signature_compact_form_my():
    # Arrange
    tool = _FakeTool(
        name="my_tool",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "number"}},
            "required": ["x"],
        },
    )
    # Act
    out = cli_mcp._format_tool_signature(tool, compact=True)
    # Assert
    assert "my_tool" in out

def test_format_tool_signature_compact_form_case_2():
    # Arrange
    tool = _FakeTool(
        name="my_tool",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "number"}},
            "required": ["x"],
        },
    )
    # Act
    out = cli_mcp._format_tool_signature(tool, compact=True)
    # Assert
    assert "x" in out


def test_format_tool_signature_multiline_for_many_params_big():
    # Arrange
    tool = _FakeTool(
        name="big_tool",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "string", "default": "hi"},
                "c": {"type": "integer"},
                "d": {"type": "boolean"},
            },
            "required": ["a"],
        },
    )
    # Act
    out = cli_mcp._format_tool_signature(tool, compact=False)
    # Assert
    assert "big_tool" in out

def test_format_tool_signature_multiline_for_many_params_case_2():
    # Arrange
    tool = _FakeTool(
        name="big_tool",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "string", "default": "hi"},
                "c": {"type": "integer"},
                "d": {"type": "boolean"},
            },
            "required": ["a"],
        },
    )
    # Act
    out = cli_mcp._format_tool_signature(tool, compact=False)
    # Assert
    assert "\n" in out


# ----- cmd_start (dry-run) --------------------------------------------- #


def test_cmd_start_dry_run_does_not_run_server_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_start(dry_run=True)
    # Act
    captured = capsys.readouterr()
    # Assert
    assert rc == 0

def test_cmd_start_dry_run_does_not_run_server_out_captured(capsys):
    # Arrange
    rc = cli_mcp.cmd_start(dry_run=True)
    # Act
    captured = capsys.readouterr()
    # Assert
    assert "DRY RUN" in captured.out

def test_cmd_start_dry_run_does_not_run_server_stdio_out_captured(capsys):
    # Arrange
    rc = cli_mcp.cmd_start(dry_run=True)
    # Act
    captured = capsys.readouterr()
    # Assert
    assert "stdio" in captured.out


def test_cmd_start_dry_run_honours_transport_rc(capsys):
    # Arrange
    # Act
    rc = cli_mcp.cmd_start(dry_run=True, transport="sse")
    # Assert
    assert rc == 0

def test_cmd_start_dry_run_honours_transport_sse_out_readouterr_capsys(capsys):
    # Arrange
    # Act
    rc = cli_mcp.cmd_start(dry_run=True, transport="sse")
    # Assert
    assert "sse" in capsys.readouterr().out


# ----- cmd_config ------------------------------------------------------- #


def test_cmd_config_text_form_prints_snippets_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=False)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_config_text_form_prints_snippets_scitex_stats(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=False)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "scitex-stats" in out

def test_cmd_config_text_form_prints_snippets_option_claude_desktop(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=False)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "Option 1" in out or "claude_desktop_config" in out


def test_cmd_config_json_form_is_parseable_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0
    payload = json.loads(out)

def test_cmd_config_json_form_is_parseable_scitex_stats_payload_package(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = json.loads(out)
    # Assert
    assert payload["package"] == "scitex-stats"

def test_cmd_config_json_form_is_parseable_snippets_payload(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = json.loads(out)
    # Assert
    assert "snippets" in payload

def test_cmd_config_json_form_is_parseable_cli_payload_snippets(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = json.loads(out)
    # Assert
    assert "cli" in payload["snippets"]

def test_cmd_config_json_form_is_parseable_python_module_payload_snippets(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = json.loads(out)
    # Assert
    assert "python_module" in payload["snippets"]

def test_cmd_config_json_form_is_parseable_paths_payload(capsys):
    # Arrange
    rc = cli_mcp.cmd_config(as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = json.loads(out)
    # Assert
    assert "config_paths" in payload


# ----- cmd_doctor ------------------------------------------------------- #


def test_cmd_doctor_returns_zero_or_one_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_doctor()
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc in (0, 1)

def test_cmd_doctor_returns_zero_or_one_health_check(capsys):
    # Arrange
    rc = cli_mcp.cmd_doctor()
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "Health Check" in out

def test_cmd_doctor_returns_zero_or_one_fastmcp(capsys):
    # Arrange
    rc = cli_mcp.cmd_doctor()
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "fastmcp" in out

def test_cmd_doctor_returns_zero_or_one_cli(capsys):
    # Arrange
    rc = cli_mcp.cmd_doctor()
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "CLI" in out


# ----- cmd_list_tools (in-process, FastMCP 3.x compatible) ----------- #


def test_cmd_list_tools_text_output_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_list_tools_text_output_scitex_stats_mcp(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "SciTeX Stats MCP" in out

def test_cmd_list_tools_text_output_recommend_tests(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "recommend_tests" in out

def test_cmd_list_tools_text_output_run_test(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "run_test" in out


def test_cmd_list_tools_json_output_rc(capsys):
    # Arrange
    import json as _json
    rc = cli_mcp.cmd_list_tools(verbose=0, as_json=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0
    payload = _json.loads(out)

def test_cmd_list_tools_json_output_scitex_stats_payload_name(capsys):
    # Arrange
    import json as _json
    rc = cli_mcp.cmd_list_tools(verbose=0, as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = _json.loads(out)
    # Assert
    assert payload["name"] == "scitex-stats"

def test_cmd_list_tools_json_output_payload_total(capsys):
    # Arrange
    import json as _json
    rc = cli_mcp.cmd_list_tools(verbose=0, as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = _json.loads(out)
    # Assert
    assert payload["total"] >= 10

def test_cmd_list_tools_json_output_modules_payload(capsys):
    # Arrange
    import json as _json
    rc = cli_mcp.cmd_list_tools(verbose=0, as_json=True)
    out = capsys.readouterr().out
    # Act
    payload = _json.loads(out)
    # Assert
    assert "modules" in payload


def test_cmd_list_tools_verbose_1_emits_signatures_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=1)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_list_tools_verbose_1_emits_signatures_test_name_data(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=1)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "test_name" in out or "data" in out


def test_cmd_list_tools_verbose_2_emits_descriptions_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=2, compact=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_list_tools_verbose_2_emits_descriptions_value_statistical_test(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=2, compact=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "p_value" in out or "Statistical" in out or "test" in out


def test_cmd_list_tools_verbose_3_emits_full_descriptions_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=3, compact=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_list_tools_verbose_3_emits_full_descriptions_case_2(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=3, compact=True)
    # Act
    out = capsys.readouterr().out
    # Assert
    assert out


def test_cmd_list_tools_module_filter_accepts_known_module_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0, module_filter="auto")
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 0

def test_cmd_list_tools_module_filter_accepts_known_module_recommend_tests(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0, module_filter="auto")
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "recommend_tests" in out


def test_cmd_list_tools_module_filter_rejects_unknown_rc(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0, module_filter="not_a_module")
    # Act
    out = capsys.readouterr().out
    # Assert
    assert rc == 1

def test_cmd_list_tools_module_filter_rejects_unknown_case_2(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0, module_filter="not_a_module")
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "Unknown module" in out

def test_cmd_list_tools_module_filter_rejects_unknown_available_modules(capsys):
    # Arrange
    rc = cli_mcp.cmd_list_tools(verbose=0, module_filter="not_a_module")
    # Act
    out = capsys.readouterr().out
    # Assert
    assert "Available modules" in out
