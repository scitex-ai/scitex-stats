"""Exercise descriptive-statistics responses through the real stdio server."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def stdio_parameters(tmp_path):
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "scitex_stats", "mcp", "start"],
        env={
            **{
                key: value
                for key, value in os.environ.items()
                if key
                in {
                    "COVERAGE_PROCESS_START",
                    "COVERAGE_PROCESS_CONFIG",
                    "COVERAGE_FILE",
                }
            },
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(tmp_path),
            "SCITEX_DIR": str(tmp_path / "state"),
            "FASTMCP_CHECK_FOR_UPDATES": "off",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        },
        cwd=tmp_path,
    )


def test_stdio_describe_rejects_empty_data_and_accepts_numbers(
    tmp_path, stdio_parameters
):
    # Arrange
    parameters = stdio_parameters

    async def collect_results():
        with (tmp_path / "server.log").open("w") as errors:
            async with (
                stdio_client(parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                empty = await session.call_tool("describe", {"data": []})
                valid = await session.call_tool("describe", {"data": [1, 2, 3]})
                return (
                    json.loads(empty.content[0].text),
                    json.loads(valid.content[0].text),
                )

    # Act
    empty, valid = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert (
        empty,
        (valid["success"], valid["n"], valid["mean"]),
    ) == (
        {"success": False, "error": "No valid data points"},
        (True, 3, 2.0),
    )


def test_stdio_describe_preserves_custom_percentiles(tmp_path, stdio_parameters):
    # Arrange
    cases = [
        ([2.5, 2.9], {"2.5": 2.5, "2.9": 2.9}),
        (
            [25.0000001, 25.0000002],
            {"25.0000001": 25.0000001, "25.0000002": 25.0000002},
        ),
        ([], {}),
        ([0.0, 25.0, 100.0], {"0": 0.0, "25": 25.0, "100": 100.0}),
    ]

    async def collect_results():
        with (tmp_path / "custom-server.log").open("w") as errors:
            async with (
                stdio_client(stdio_parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                results = []
                for percentiles, _ in cases:
                    response = await session.call_tool(
                        "describe",
                        {"data": [0.0, 100.0], "percentiles": percentiles},
                    )
                    data = json.loads(response.content[0].text)
                    # SDK 2 uses snake_case; older supported SDKs use camelCase.
                    error_flag = (
                        response.is_error
                        if hasattr(response, "is_error")
                        else response.isError
                    )
                    results.append(
                        (bool(error_flag), data["success"], data["percentiles"])
                    )
                return results

    # Act
    actual = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert actual == [
        (False, True, pytest.approx(expected, abs=1e-12, rel=0))
        for _, expected in cases
    ]


def test_stdio_effect_size_rejects_unsupported_unpooled_mode(
    tmp_path, stdio_parameters
):
    # Arrange
    arguments = dict(group1=[1, 2, 3], group2=[4, 5, 6], measure="cohens_d")

    async def collect_results():
        with (tmp_path / "effect-server.log").open("w") as errors:
            async with (
                stdio_client(stdio_parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                default = await session.call_tool("effect_size", arguments)
                unpooled = await session.call_tool(
                    "effect_size", {**arguments, "pooled": False}
                )
                return json.loads(default.content[0].text), json.loads(
                    unpooled.content[0].text
                )

    # Act
    default, unpooled = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert (
        default["success"],
        default["value"],
        unpooled["success"],
        "pooled=False" in unpooled.get("error", ""),
    ) == (True, -3.0, False, True)


def test_stdio_normality_never_labels_too_few_samples_as_success(
    tmp_path, stdio_parameters
):
    # Arrange
    async def collect_results():
        with (tmp_path / "normality-server.log").open("w") as errors:
            async with (
                stdio_client(stdio_parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                invalid = await session.call_tool("normality_test", {"data": [1, 2]})
                valid = await session.call_tool("normality_test", {"data": [1, 2, 3]})
                return json.loads(invalid.content[0].text), json.loads(
                    valid.content[0].text
                )

    # Act
    invalid, valid = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert (
        invalid["success"],
        "3 data points" in invalid["error"],
        valid["success"],
        valid["n"],
        valid["p_value"],
    ) == (False, True, True, 3, pytest.approx(1.0))


def test_stdio_correction_rejects_out_of_range_and_preserves_valid_result(
    tmp_path, stdio_parameters
):
    # Arrange
    async def collect_results():
        with (tmp_path / "correction-server.log").open("w") as errors:
            async with (
                stdio_client(stdio_parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                invalid = await session.call_tool(
                    "correct_pvalues", {"pvalues": [-0.1, 0.2]}
                )
                valid = await session.call_tool(
                    "correct_pvalues", {"pvalues": [0.01, 0.04, 0.03]}
                )
                return json.loads(invalid.content[0].text), json.loads(
                    valid.content[0].text
                )

    # Act
    invalid, valid = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert (
        invalid["success"],
        bool(invalid["error"]),
        valid["success"],
        valid["corrected_pvalues"],
        valid["method_used"],
    ) == (False, True, True, pytest.approx([0.03, 0.04, 0.04]), "fdr_bh")


def test_stdio_formatting_reports_real_presets(tmp_path, stdio_parameters):
    # Arrange
    styles = ["apa", "nature", "brief", "science"]

    async def collect_results():
        with (tmp_path / "formatting-server.log").open("w") as errors:
            async with (
                stdio_client(stdio_parameters, errlog=errors) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                results = []
                for style in styles:
                    response = await session.call_tool(
                        "format_results",
                        {
                            "test_name": "ttest_ind",
                            "statistic": 2.0,
                            "p_value": 0.04,
                            "style": style,
                        },
                    )
                    body = json.loads(response.content[0].text)
                    results.append(
                        (
                            body["success"],
                            body["style"],
                            body["style_used"],
                            body["formatted"],
                        )
                    )
                return results

    # Act
    results = asyncio.run(asyncio.wait_for(collect_results(), timeout=30))
    # Assert
    assert results == [
        (True, "apa", "apa_latex", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
        (True, "nature", "nature_latex", r"\mathit{t} = 2.00, \mathit{P} = 0.040"),
        (True, "brief", "plain", "t = 2.00, p = 0.040"),
        (True, "science", "apa_latex", r"\mathit{t} = 2.00, \mathit{p} = 0.040"),
    ]
