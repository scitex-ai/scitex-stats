"""Check actual MCP initialization, listing and JSON-RPC calls over stdio."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BAD_TYPES = [
    {"p_value": True}, {"p_value": False}, {"p_value": ".01"},
    {"p_value": None}, {"p_value": [.01]},
    {"p_value": .005, "thresholds": [False, .01, .05]},
    {"p_value": .005, "thresholds": [".001", .01, .05]},
    {"p_value": .005, "thresholds": "not an array"},
]
VALID = [({"p_value": 0}, "***"), ({"p_value": .001}, "**"),
         ({"p_value": .01}, "*"), ({"p_value": .05}, "ns"), ({"p_value": 1}, "ns"),
         ({"p_value": .005, "thresholds": [.0001, .001, .01]}, "*"),
         ({"p_value": 0, "thresholds": [0, .5, 1]}, "**"),
         ({"p_value": .5, "thresholds": [0, .5, 1]}, "*")]
BAD_VALUES = [{"p_value": -.1}, {"p_value": 1.1},
              {"p_value": .005, "thresholds": []},
              {"p_value": .005, "thresholds": [.01, .01, .05]},
              {"p_value": .005, "thresholds": [-.1, .01, .05]},
              {"p_value": .005, "thresholds": [.001, .01, .05, .1]}]
TOOLS = {"recommend_tests", "check_applicability", "recommend_test", "run_all_applicable",
         "generate_report", "run_test", "validate_apa", "verify_result", "format_results",
         "power_analysis", "correct_pvalues", "describe", "effect_size", "normality_test",
         "posthoc_test", "p_to_stars", "skills_list", "skills_get"}


def collect_protocol(temporary):
    """Close the real server/session before returning an immutable JSON snapshot."""
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "scitex_stats", "mcp", "start"],
        env={**os.environ, "HOME": str(temporary), "TMPDIR": str(temporary),
             "SCITEX_DIR": str(temporary / "state"), "XDG_CACHE_HOME": str(temporary / "cache"),
             "FASTMCP_CHECK_FOR_UPDATES": "off",
             "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
        cwd=temporary,
    )

    async def collect():
        with (temporary / "server.log").open("w") as errors:
            async with (stdio_client(parameters, errlog=errors) as (read, write),
                        ClientSession(read, write) as session):
                await session.initialize()
                listing = await session.list_tools()
                bad_types = [await session.call_tool("p_to_stars", row) for row in BAD_TYPES]
                valid = [await session.call_tool("p_to_stars", row) for row, _ in VALID]
                bad_values = [await session.call_tool("p_to_stars", row) for row in BAD_VALUES]
                return listing, bad_types, valid, bad_values

    listing, bad_types, valid, bad_values = asyncio.run(asyncio.wait_for(collect(), timeout=30))
    observations = {"listing": {"tools": [{"name": tool.name, "input_schema": tool_schema(tool)} for tool in listing.tools]},
                    "bad_types": [response_data(row) for row in bad_types],
                    "valid": [response_data(row) for row in valid],
                    "bad_values": [response_data(row) for row in bad_values]}
    snapshot = json.dumps(observations, indent=2)
    (temporary / "protocol-results.json").write_text(snapshot)
    return snapshot


def tool_schema(tool):
    schema = getattr(tool, "input_schema", None)
    return tool.inputSchema if schema is None else schema


def response_data(response):
    error = getattr(response, "is_error", None)
    error = response.isError if error is None else error
    return {"is_error": error, "content": [row.model_dump(mode="json") for row in response.content]}


@pytest.fixture(scope="module")
def protocol_snapshot(tmp_path_factory):
    return collect_protocol(tmp_path_factory.mktemp("star-stdio"))


@pytest.fixture
def protocol_results(protocol_snapshot):
    # Each test gets fresh data; no mutable protocol/session objects are shared.
    return json.loads(protocol_snapshot)


@pytest.mark.parametrize("index", range(len(BAD_TYPES)))
def test_stdio_star_rejects_non_numeric_json_types_before_coercion(protocol_results, index):
    # Arrange
    response = protocol_results["bad_types"][index]
    # Act
    rejected = response["is_error"]
    # Assert
    assert rejected is True


@pytest.mark.parametrize("index", range(len(VALID)))
def test_stdio_star_preserves_supported_json_numbers_and_strict_boundaries(protocol_results, index):
    # Arrange
    response = protocol_results["valid"][index]
    arguments, expected = VALID[index]
    thresholds = arguments.get("thresholds", [.001, .01, .05])
    # Act
    report = json.loads(response["content"][0]["text"])
    # Assert
    assert (response["is_error"], report["success"], report["stars"], report["p_value"], report["thresholds"], set(report)) == (False, True, expected, arguments["p_value"], thresholds, {"success", "p_value", "stars", "significance", "thresholds", "timestamp"})


@pytest.mark.parametrize("index", range(len(BAD_VALUES)))
def test_stdio_star_preserves_handler_error_envelope_for_numeric_domain_errors(protocol_results, index):
    # Arrange
    response = protocol_results["bad_values"][index]
    # Act
    report = json.loads(response["content"][0]["text"])
    # Assert
    assert (response["is_error"], report.get("success"), set(report), bool(report.get("error"))) == (False, False, {"success", "error"}, True)


def test_stdio_star_keeps_all_tool_names_and_numeric_parameter_schema(protocol_results):
    # Arrange
    tools = protocol_results["listing"]["tools"]
    schema = next(tool["input_schema"] for tool in tools if tool["name"] == "p_to_stars")
    # Act
    observed = ({tool["name"] for tool in tools}, schema["required"], set(schema["properties"]), schema["properties"]["p_value"]["type"])
    # Assert
    assert observed == (TOOLS, ["p_value"], {"p_value", "thresholds"}, "number")
