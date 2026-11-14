"""Expose the documented hard CSV separator through the actual MCP tool."""

import asyncio
import json
import os
from pathlib import Path
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from scipy import stats

from scitex_stats import _server
from scitex_stats._mcp.handlers import run_test_handler

SAMPLE = [-.2, .1, .4, .9, 1.5, 1.8, 2.3, 2.8]


def write_sample(directory):
    source = directory / "ambiguous.csv"
    source.write_text("sample;unused,tag\n" + "".join(f"{value};1,foo\n" for value in SAMPLE))
    return source


async def registered_call(**kwargs):
    function = getattr(_server.run_test, "fn", _server.run_test)
    return json.loads(await function(**kwargs))


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
def test_explicit_separator_selects_the_requested_column(call, tmp_path):
    # Arrange
    source = write_sample(tmp_path)
    expected = stats.ttest_1samp(SAMPLE, 0., alternative="greater")
    # Act
    report = asyncio.run(call(test_name="ttest_1samp", data_file=str(source), columns=["sample"], alternative="greater", sep=";"))
    # Assert
    assert (report["success"], report["statistic"], report["p_value"]) == (
        True, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
def test_wrong_explicit_separator_is_not_silently_ignored(call, tmp_path):
    # Arrange
    source = write_sample(tmp_path)
    # Act
    report = asyncio.run(call(test_name="ttest_1samp", data_file=str(source), columns=["sample"], sep=","))
    # Assert
    assert (report["success"], "Columns not found" in report["error"]) == (False, True)


@pytest.mark.parametrize("call", [run_test_handler, registered_call])
@pytest.mark.parametrize("options", [{}, {"sep": None}])
def test_automatic_separator_keeps_existing_ambiguity_failure(call, options, tmp_path):
    # Arrange
    source = write_sample(tmp_path)
    # Act
    report = asyncio.run(call(test_name="ttest_1samp", data_file=str(source), columns=["sample"], **options))
    # Assert
    assert report == {"success": False, "error": "Ambiguous separator; specify sep explicitly."}


def collect_protocol(directory):
    source = write_sample(directory)
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "scitex_stats", "mcp", "start"],
        env={**os.environ, "HOME": str(directory), "TMPDIR": str(directory),
             "SCITEX_DIR": str(directory/"state"), "XDG_CACHE_HOME": str(directory/"cache"),
             "FASTMCP_CHECK_FOR_UPDATES": "off",
             "PYTHONPATH": str(Path(__file__).resolve().parents[2]/"src")}, cwd=directory)

    async def collect():
        with (directory/"server.log").open("w") as errors:
            async with (stdio_client(params, errlog=errors) as (read, write),
                        ClientSession(read, write) as session):
                await session.initialize()
                listing = await session.list_tools()
                base = {"test_name": "ttest_1samp", "data_file": str(source),
                        "columns": ["sample"], "alternative": "greater"}
                responses = [await session.call_tool("run_test", {**base, **options})
                             for options in [{"sep": ";"}, {"sep": ","}, {}, {"sep": None}]]
                return listing, responses

    listing, responses = asyncio.run(asyncio.wait_for(collect(), timeout=30))
    schemas = {}
    for tool in listing.tools:
        schema = getattr(tool, "input_schema", None)
        schemas[tool.name] = tool.inputSchema if schema is None else schema
    rows = []
    for response in responses:
        error = getattr(response, "is_error", None)
        error = response.isError if error is None else error
        text = response.content[0].text
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"transport_text": text}
        rows.append({"is_error": error, "payload": payload})
    result = {"schemas": schemas, "responses": rows}
    snapshot = json.dumps(result, indent=2)
    (directory/"protocol-results.json").write_text(snapshot)
    return snapshot


@pytest.fixture(scope="module")
def protocol_snapshot(tmp_path_factory):
    return collect_protocol(tmp_path_factory.mktemp("separator-stdio"))


@pytest.fixture
def protocol(protocol_snapshot):
    return json.loads(protocol_snapshot)


def test_stdio_catalogue_exposes_optional_nullable_separator(protocol):
    # Arrange
    schema = protocol["schemas"]["run_test"]
    # Act
    field = schema["properties"].get("sep", {})
    # Assert
    assert (len(protocol["schemas"]), {row["type"] for row in field.get("anyOf", [])}, field.get("default"), "sep" in schema["required"]) == (
        18, {"string", "null"}, None, False,
    )


def test_stdio_separator_reaches_loader_and_matches_scipy(protocol):
    # Arrange
    expected = stats.ttest_1samp(SAMPLE, 0., alternative="greater")
    response = protocol["responses"][0]
    # Act
    report = response["payload"]
    # Assert
    assert (response["is_error"], report.get("success"), report.get("statistic"), report.get("p_value")) == (
        False, True, pytest.approx(float(expected.statistic)), pytest.approx(float(expected.pvalue)),
    )


def test_stdio_wrong_separator_preserves_loader_failure(protocol):
    # Arrange
    response = protocol["responses"][1]
    # Act
    report = response["payload"]
    # Assert
    assert (response["is_error"], report.get("success"), "Columns not found" in report.get("error", "")) == (False, False, True)


@pytest.mark.parametrize("index", [2, 3])
def test_stdio_auto_separator_preserves_ambiguity_failure(protocol, index):
    # Arrange
    response = protocol["responses"][index]
    # Act
    report = response["payload"]
    # Assert
    assert (response["is_error"], report) == (False, {"success": False, "error": "Ambiguous separator; specify sep explicitly."})
