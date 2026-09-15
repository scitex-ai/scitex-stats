#!/usr/bin/env python3
"""Tests for `scitex-stats report` (`_cli/report.py`) and the `generate_report` MCP handler."""

from __future__ import annotations

import asyncio
import json

import pytest
from click.testing import CliRunner

from scitex_stats._cli import main
from scitex_stats._mcp.handlers import generate_report_handler

CSV = "control,drug_a,drug_b\n5.1,6.3,5.9\n4.9,6.8,6.2\n5.6,6.1,6.0\n5.8,7.0,5.8\n6.0,6.6,6.4\n5.4,6.9,6.1\n5.2,6.4,\n5.7,7.2,\n"


@pytest.fixture
def csv_path(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text(CSV, encoding="utf-8")
    return path


def test_report_dry_run_prints_summary_json(csv_path):
    # Arrange
    args = ["report", str(csv_path), "--dry-run", "--json"]
    # Act
    result = CliRunner().invoke(main, args)
    # Assert
    assert json.loads(result.output)["summary"]["posthoc"]["method"] == "tukey"


def test_report_writes_requested_formats(csv_path, tmp_path):
    # Arrange
    out = tmp_path / "out" / "report.pdf"
    # Act
    result = CliRunner().invoke(main, ["report", str(csv_path), "--out", str(out), "--format", "html,md", "--json"])
    # Assert
    assert sorted(json.loads(result.output)["paths"]) == ["figure", "html", "md"]


def test_report_long_format_uses_group_and_value_columns(tmp_path):
    # Arrange
    path = tmp_path / "long.csv"
    rows = ["group,score"] + [f"a,{v}" for v in (1.1, 1.3, 1.2, 1.4, 1.0)] + [f"b,{v}" for v in (2.1, 2.4, 2.2, 2.0, 2.3)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    # Act
    result = CliRunner().invoke(main, ["report", str(path), "--group-col", "group", "--value-col", "score", "--dry-run", "--json"])
    # Assert
    assert json.loads(result.output)["summary"]["groups"] == ["a", "b"]


def test_mcp_generate_report_returns_paths(tmp_path):
    # Arrange
    data = {"A": [5.1, 4.9, 5.6, 5.8], "B": [6.3, 6.8, 6.1, 7.0]}
    # Act
    out = asyncio.run(generate_report_handler(data=data, output=str(tmp_path / "r.pdf"), formats=["md"]))
    # Assert
    assert out["success"] is True and out["paths"]["md"].endswith("r.md")


def test_mcp_generate_report_requires_one_data_source():
    # Arrange
    kwargs = {}
    # Act
    out = asyncio.run(generate_report_handler(**kwargs))
    # Assert
    assert out["success"] is False


# EOF
