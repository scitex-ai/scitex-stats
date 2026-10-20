#!/usr/bin/env python3
# File: tests/test_cli.py

"""Tests for scitex-stats CLI commands.

Verifies that all CLI subcommands work via subprocess and via
the internal main() entry point.
"""

import subprocess
import sys

import pytest

PYTHON = sys.executable
CLI_MODULE = [PYTHON, "-m", "scitex_stats"]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_cli(*args, timeout=30):
    """Run scitex-stats CLI and return CompletedProcess."""
    cmd = CLI_MODULE + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ===================================================================
# 1. Top-level commands
# ===================================================================


class TestTopLevelCLI:
    """Test top-level CLI flags."""

    def test_help_returncode_1(self):
        # Arrange
        # Act
        result = _run_cli("--help")
        # Assert
        assert result.returncode == 0

    def test_help_scitex_stats_lower_stdout(self):
        # Arrange
        # Act
        result = _run_cli("--help")
        # Assert
        assert (
            "scitex-stats" in result.stdout.lower() or "scitex" in result.stdout.lower()
        )

    def test_help_mcp_stdout(self):
        # Arrange
        # Act
        result = _run_cli("--help")
        # Assert
        assert "mcp" in result.stdout

    def test_version_returncode_1(self):
        # Arrange
        # Act
        result = _run_cli("-V")
        # Assert
        assert result.returncode == 0

    def test_version_scitex_stats_stdout(self):
        # Arrange
        # Act
        result = _run_cli("-V")
        # Assert
        assert "scitex-stats" in result.stdout

    def test_help_recursive_returncode(self):
        # Arrange
        # Act
        result = _run_cli("--help-recursive")
        # Assert
        assert result.returncode == 0

    def test_help_recursive_mcp_stdout(self):
        # Arrange
        # Act
        result = _run_cli("--help-recursive")
        # Assert
        assert "mcp" in result.stdout

    def test_help_recursive_list_tools_stdout(self):
        # Arrange
        # Act
        result = _run_cli("--help-recursive")
        # Assert
        assert "list-tools" in result.stdout or "list_tools" in result.stdout

    def test_no_args_shows_help_returncode(self):
        # Arrange
        # Act
        result = _run_cli()
        # Assert
        assert result.returncode == 0

    def test_no_args_shows_help_usage_scitex_lower_stdout(self):
        # Arrange
        # Act
        result = _run_cli()
        # Assert
        assert "usage" in result.stdout.lower() or "scitex" in result.stdout.lower()


# ===================================================================
# 2. list-python-apis
# ===================================================================


class TestListPythonAPIs:
    """Test list-python-apis subcommand."""

    def test_list_python_apis_returncode(self):
        # Arrange
        # Act
        result = _run_cli("list-python-apis")
        # Assert
        assert result.returncode == 0

    def test_list_python_apis_scitex_stats_stdout_api(self):
        # Arrange
        # Act
        result = _run_cli("list-python-apis")
        # Assert
        assert "scitex_stats" in result.stdout or "API" in result.stdout

    def test_list_python_apis_json_returncode(self):
        # Arrange
        # Act
        # 60s, not 30s: same cold-start flake guard as mcp-doctor above —
        # `list-python-apis --json` imports the full battery + serializes,
        # and exceeded 30s on py3.11/org-06 under xdist load (develop CI
        # 2026-10-20) while 3.12/3.13 passed; local single-run is ~2s.
        result = _run_cli("list-python-apis", "--json", timeout=60)
        # Assert
        assert result.returncode == 0
        import json

        data = json.loads(result.stdout)

    def test_list_python_apis_json_case_2(self):
        # Arrange
        result = _run_cli("list-python-apis", "--json", timeout=60)
        import json

        # Act
        data = json.loads(result.stdout)
        # Assert
        assert isinstance(data, list)


# ===================================================================
# 3. mcp subcommands
# ===================================================================


class TestMCPCLI:
    """Test MCP-related CLI subcommands."""

    def test_mcp_help_returncode(self):
        # Click groups invoked without a subcommand exit 2 by default
        # and print the help text to stderr; if the group is configured
        # `invoke_without_command=True`, exit is 0 and help goes to
        # stdout. Both rc and stream are acceptable as long as the help
        # body actually rendered somewhere.
        # Arrange
        # Act
        result = _run_cli("mcp")
        # Assert
        assert result.returncode in (0, 2)
        combined = result.stdout + result.stderr

    def test_mcp_help_list_tools_combined(self):
        # Click groups invoked without a subcommand exit 2 by default
        # and print the help text to stderr; if the group is configured
        # `invoke_without_command=True`, exit is 0 and help goes to
        # stdout. Both rc and stream are acceptable as long as the help
        # body actually rendered somewhere.
        # Arrange
        # Act
        result = _run_cli("mcp")
        combined = result.stdout + result.stderr
        # Assert
        assert "list-tools" in combined

    def test_mcp_help_doctor_combined(self):
        # Click groups invoked without a subcommand exit 2 by default
        # and print the help text to stderr; if the group is configured
        # `invoke_without_command=True`, exit is 0 and help goes to
        # stdout. Both rc and stream are acceptable as long as the help
        # body actually rendered somewhere.
        # Arrange
        # Act
        result = _run_cli("mcp")
        combined = result.stdout + result.stderr
        # Assert
        assert "doctor" in combined

    def test_mcp_list_tools_returncode(self):
        # The xfail markers that used to live here pre-date the
        # `mcp.list_tools()` (async) rewrite — the CLI no longer
        # depends on FastMCP 2.x's `_tool_manager`.
        # Arrange
        # Act
        result = _run_cli("mcp", "list-tools")
        # Assert
        assert result.returncode == 0

    def test_mcp_list_tools_recommend_tests_stdout_run(self):
        # The xfail markers that used to live here pre-date the
        # `mcp.list_tools()` (async) rewrite — the CLI no longer
        # depends on FastMCP 2.x's `_tool_manager`.
        # Arrange
        # Act
        result = _run_cli("mcp", "list-tools")
        # Assert
        assert "recommend_tests" in result.stdout or "run_test" in result.stdout

    def test_mcp_list_tools_json_returncode(self):
        # Arrange
        # Act
        result = _run_cli("mcp", "list-tools", "--json")
        # Assert
        assert result.returncode == 0
        import json

        data = json.loads(result.stdout)

    def test_mcp_list_tools_json_str(self):
        # Arrange
        result = _run_cli("mcp", "list-tools", "--json")
        import json

        # Act
        data = json.loads(result.stdout)
        # Assert
        assert "tools" in str(data)

    def test_mcp_doctor_returncode(self):
        # Arrange
        # Act
        # 60s, not 15s: under xdist's 20-way parallel load on self-hosted
        # runners a cold `mcp doctor` (fresh interpreter + scipy import) can
        # exceed 15s (CI 2026-10-19: TimeoutExpired on py3.11 while
        # 3.12/3.13 passed the same assertion; local single-run is ~1.4s).
        result = _run_cli("mcp", "doctor", timeout=60)
        # Assert
        assert result.returncode in (0, 1)

    def test_mcp_doctor_health_check_stdout_fastmcp(self):
        # Arrange
        # Act
        # Same 60s budget as above: cold-start flake guard, not a slow CLI.
        result = _run_cli("mcp", "doctor", timeout=60)
        # Assert
        assert "Health Check" in result.stdout or "fastmcp" in result.stdout


# ===================================================================
# 4. Internal main() entry point
# ===================================================================


class TestMainEntryPoint:
    """Test the CLI main() function directly."""

    @staticmethod
    def _exit_code(argv):
        """Run main(argv) and return the SystemExit code Click raises on a
        clean exit (None if main returns without exiting)."""
        from scitex_stats._cli import main

        try:
            main(argv)
        except SystemExit as exc:
            return exc.code
        return None

    def test_main_help_recursive_exits_with_code_zero(self):
        # Click's group.main() raises SystemExit(0) on success rather than
        # returning; the post-Click contract is "exits cleanly".
        # Arrange
        argv = ["--help-recursive"]
        # Act
        code = self._exit_code(argv)
        # Assert
        assert code == 0

    def test_main_no_args_exits_with_code_zero(self):
        # Arrange
        argv = []
        # Act
        code = self._exit_code(argv)
        # Assert
        assert code == 0

    def test_main_version_exits_with_code_zero(self):
        # Arrange
        argv = ["-V"]
        # Act
        code = self._exit_code(argv)
        # Assert
        assert code == 0


# EOF
