"""Exercise descriptive-statistics responses through the real stdio server."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_describe_rejects_empty_data_and_accepts_numbers(tmp_path):
    # Arrange
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "scitex_stats", "mcp", "start"],
        env={
            **{
                key: value
                for key, value in os.environ.items()
                if key in {"COVERAGE_PROCESS_START", "COVERAGE_PROCESS_CONFIG", "COVERAGE_FILE"}
            },
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(tmp_path),
            "SCITEX_DIR": str(tmp_path / "state"),
            "FASTMCP_CHECK_FOR_UPDATES": "off",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        },
        cwd=tmp_path,
    )

    async def collect_results():
        with (tmp_path / "server.log").open("w") as errors:
            async with (
                stdio_client(parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                empty = await session.call_tool("describe", {"data": []})
                valid = await session.call_tool("describe", {"data": [1, 2, 3]})
                fractional = await session.call_tool(
                    "describe", {"data": [0, 100], "percentiles": [2.1, 2.9, 97.5]}
                )
                return (
                    json.loads(empty.content[0].text),
                    json.loads(valid.content[0].text),
                    json.loads(fractional.content[0].text),
                )

    # Act
    empty, valid, fractional = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert (
        empty,
        (valid["success"], valid["n"], valid["mean"]),
        (fractional["success"], fractional["percentiles"]),
    ) == (
        {"success": False, "error": "No valid data points"},
        (True, 3, 2.0),
        (True, pytest.approx({"2.1": 2.1, "2.9": 2.9, "97.5": 97.5})),
    )
