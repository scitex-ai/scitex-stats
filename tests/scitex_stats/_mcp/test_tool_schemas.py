"""Direct test for `scitex_stats._mcp.tool_schemas.get_tool_schemas`.

The module is mostly a single big `return [...]` of `mcp.types.Tool`
instances. Coverage was 0 % only because nothing imported and called
it. Calling it once verifies the shape and registers the lines.
"""

from __future__ import annotations

import pytest

mcp_types = pytest.importorskip("mcp.types")

from scitex_stats._mcp.tool_schemas import get_tool_schemas


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
    tools = get_tool_schemas()
    # Assert
    assert isinstance(tools, list) and tools

def test_get_tool_schemas_returns_list_of_tools_all_mcp_types():
    # Arrange
    # Act
    tools = get_tool_schemas()
    # Assert
    assert all(isinstance(t, mcp_types.Tool) for t in tools)


def test_get_tool_schemas_covers_every_expected_tool():
    # Arrange
    # Act
    tools = get_tool_schemas()
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    # Assert
    assert not missing, f"missing tool schemas: {missing}"


def test_each_schema_has_description_and_object_input_schema_with_properties():
    # Arrange
    # Act
    schemas = get_tool_schemas()
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
    schema = _schema_of(next(t for t in get_tool_schemas() if t.name == "run_test"))
    enum_vals = (schema or {})["properties"]["test_name"]["enum"]
    # Assert
    assert len(enum_vals) == 23, f"expected 23 tests, got {len(enum_vals)}"
