"""Default catalog schemas, derived from the actual registered MCP server."""

from __future__ import annotations

import asyncio

import pytest

mcp_types = pytest.importorskip("mcp.types")


def _catalog():
    from scitex_stats._mcp.tool_schemas import get_tool_schemas

    return get_tool_schemas()


def _schema_of(tool):
    """JSON-schema dict across MCP SDK majors (2.x: input_schema)."""
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return schema


EXPECTED_TOOLS = {
    "recommend_tests",
    "run_test",
    "format_results",
    "power_analysis",
    "correct_pvalues",
    "describe",
    "effect_size",
    "normality_test",
    "posthoc_test",
    "p_to_stars",
}


def test_get_tool_schemas_returns_list_of_tools_case_1():
    # Arrange
    # Act
    tools = _catalog()
    # Assert
    assert isinstance(tools, list) and tools


def test_get_tool_schemas_returns_list_of_tools_all_mcp_types():
    # Arrange
    # Act
    tools = _catalog()
    # Assert
    assert all(isinstance(t, mcp_types.Tool) for t in tools)


def test_get_tool_schemas_covers_every_expected_tool():
    # Arrange
    # Act
    tools = _catalog()
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    # Assert
    assert not missing, f"missing tool schemas: {missing}"


def test_each_schema_has_description_and_object_input_schema_with_properties():
    # Arrange
    # Act
    schemas = _catalog()
    # Assert
    for t in schemas:
        # Each tool must carry a non-empty str description and an object
        # input schema (dict, type=="object") that declares properties.
        schema = _schema_of(t)
        well_formed = (
            isinstance(t.description, str)
            and bool(t.description)
            and isinstance(schema, dict)
            and schema.get("type") == "object"
            and "properties" in schema
        )
        assert well_formed, f"{t.name} has a malformed schema: {schema!r}"


def test_run_test_schema_lists_all_23_tests():
    """The `run_test` schema's `test_name` enum is the source of truth
    for which tests the MCP surface accepts. Catch additions / removals
    early."""
    # Arrange
    # Act
    schema = _schema_of(next(t for t in _catalog() if t.name == "run_test"))
    enum_vals = (schema or {})["properties"]["test_name"]["enum"]
    # Assert
    assert len(enum_vals) == 23, f"expected 23 tests, got {len(enum_vals)}"


def _metadata(tools):
    return {
        t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
        for t in tools
    }


async def _registered_metadata():
    from fastmcp import Client

    from scitex_stats._server import mcp

    async with Client(mcp) as client:
        return _metadata(await client.list_tools())


def test_sync_catalog_matches_registered_wire_metadata():
    # Arrange
    expected = asyncio.run(_registered_metadata())
    # Act
    result = _metadata(_catalog())
    # Assert
    assert result == expected


def test_sync_catalog_works_inside_a_running_event_loop():
    # Arrange
    async def collect():
        expected = await _registered_metadata()
        return _metadata(_catalog()), expected

    # Act
    actual, expected = asyncio.run(collect())
    # Assert
    assert actual == expected


def test_async_catalog_matches_registered_wire_metadata():
    # Arrange
    from scitex_stats._mcp.tool_schemas import get_tool_schemas_async

    async def collect():
        expected = await _registered_metadata()
        return _metadata(await get_tool_schemas_async()), expected

    # Act
    actual, expected = asyncio.run(collect())
    # Assert
    assert actual == expected


def test_cli_catalog_matches_shared_wire_metadata():
    # Arrange
    from scitex_stats._cli.mcp import _list_tool_objects

    expected = asyncio.run(_registered_metadata())
    # Act
    actual = _metadata(_list_tool_objects())
    # Assert
    assert actual == expected
