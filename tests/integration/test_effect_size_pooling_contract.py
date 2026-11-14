"""Refuse a pooling option the implementation does not support."""

import asyncio

import pytest

from scitex_stats._mcp._handlers._effect_size import effect_size_handler


@pytest.mark.parametrize("measure", ["cohens_d", "hedges_g", "glass_delta", "cliffs_delta"])
def test_false_pooling_returns_an_error_instead_of_an_unrequested_calculation(measure):
    # Arrange: unequal spreads make ignoring the option scientifically material.
    # Act
    result = asyncio.run(effect_size_handler(
        group1=[1.0, 2.0, 3.0, 4.0], group2=[2.0, 4.0, 8.0, 16.0],
        measure=measure, pooled=False,
    ))
    # Assert: no numerical result is claimed for an unsupported option.
    assert result == {
        "success": False,
        "error": "pooled=False is not supported; choose an explicit effect-size measure",
    }


def test_effect_size_wire_schema_advertises_only_supported_pooling():
    # Arrange
    from scitex_stats._mcp.tool_schemas import get_tool_schemas

    # Act
    tool = next(tool for tool in get_tool_schemas() if tool.name == "effect_size")
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema")
    # Assert
    assert schema["properties"]["pooled"]["enum"] == [True]


def test_effect_size_registered_server_schema_refuses_false_pooling():
    # Arrange: owning CLI discovery uses the actual registered FastMCP instance.
    from scitex_stats._cli.mcp import _list_tool_objects

    # Act
    tool = next(tool for tool in _list_tool_objects() if tool.name == "effect_size")
    schema = (getattr(tool, "parameters", None) or getattr(tool, "inputSchema", None)
              or getattr(tool, "input_schema", None))
    pooling = schema["properties"]["pooled"]
    # Assert
    assert pooling.get("const") is True or pooling.get("enum") == [True]
