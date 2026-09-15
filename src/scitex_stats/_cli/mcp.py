#!/usr/bin/env python3
# File: src/scitex_stats/_cli/mcp.py

"""MCP CLI worker functions for scitex-stats (Click-friendly, no argparse)."""

from __future__ import annotations

import shutil
import sys

from .. import __version__


def _list_tool_objects():
    """Return the MCP server's registered tool objects (version-robust).

    The FastMCP tool-enumeration API has churned across releases:

    - 1.x exposed ``FastMCP.list_tools()`` (removed in 2.x).
    - 2.x exposes ``FastMCP.get_tools()`` (async ``{name: Tool}`` map);
      its internal Tool exposes ``.parameters`` and ``.fn``.
    - 3.x dropped ``get_tools()``.

    The one accessor stable across every major is the in-memory
    ``fastmcp.Client`` transport, which returns MCP wire ``Tool`` objects
    exposing ``.name`` / ``.description`` / ``.inputSchema``. Prefer the
    richer in-process ``get_tools()`` when present (keeps return-type
    annotations in signatures), and fall back to the client otherwise.
    """
    import asyncio

    from .._mcp import mcp

    get_tools = getattr(mcp, "get_tools", None)
    if callable(get_tools):
        tools = asyncio.run(get_tools())
        return list(tools.values()) if isinstance(tools, dict) else list(tools)

    from fastmcp import Client

    async def _collect():
        async with Client(mcp) as client:
            return await client.list_tools()

    return asyncio.run(_collect())


CLAUDE_DESKTOP_CONFIG_CLI = """{
  "mcpServers": {
    "scitex-stats": {
      "command": "/path/to/.venv/bin/scitex-stats",
      "args": ["mcp", "start"]
    }
  }
}"""

CLAUDE_DESKTOP_CONFIG_PYTHON = """{
  "mcpServers": {
    "scitex-stats": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "scitex_stats", "mcp", "start"]
    }
  }
}"""


def cmd_start(
    *, transport: str = "stdio", dry_run: bool = False, yes: bool = False
) -> int:
    """Start the MCP server."""
    if dry_run:
        print(f"DRY RUN — would start scitex-stats MCP server (transport={transport})")
        return 0
    if not yes and not sys.stdin.isatty():
        # Non-interactive context without --yes — proceed (no prompt to wait on)
        pass
    from .._mcp import run_server

    run_server(transport=transport)
    return 0


def _style(text: str, fg: str = None, bold: bool = False) -> str:
    """Apply ANSI color styling."""
    if not sys.stdout.isatty():
        return text
    codes = {
        "green": "\033[32m",
        "cyan": "\033[36m",
        "yellow": "\033[33m",
        "magenta": "\033[35m",
        "white": "\033[37m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    prefix = ""
    if bold:
        prefix += codes["bold"]
    if fg and fg in codes:
        prefix += codes[fg]
    return f"{prefix}{text}{codes['reset']}" if prefix else text


def _format_tool_signature(tool, compact: bool = False, indent: str = "  ") -> str:
    """Format tool as Python-like function signature with colors."""
    import inspect

    params = []
    # The JSON-schema attribute name differs across FastMCP majors:
    # 2.x exposes ``parameters`` on the internal Tool; the MCP wire Tool
    # (and some 3.x objects) expose ``inputSchema``. Accept either.
    schema = getattr(tool, "parameters", None) or getattr(tool, "inputSchema", None)
    if schema:
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for name, info in props.items():
            ptype = info.get("type", "any")
            default = info.get("default")
            name_s = _style(name, "white", bold=True)
            type_s = _style(ptype, "cyan")
            if name in required:
                params.append(f"{name_s}: {type_s}")
            elif default is not None:
                def_str = repr(default) if len(repr(default)) < 20 else "..."
                def_s = _style(f"= {def_str}", "yellow")
                params.append(f"{name_s}: {type_s} {def_s}")
            else:
                def_s = _style("= None", "yellow")
                params.append(f"{name_s}: {type_s} {def_s}")

    ret_type = ""
    if hasattr(tool, "fn") and tool.fn:
        try:
            sig = inspect.signature(tool.fn)
            if sig.return_annotation != inspect.Parameter.empty:
                ret = sig.return_annotation
                ret_name = ret.__name__ if hasattr(ret, "__name__") else str(ret)
                ret_type = f" -> {_style(ret_name, 'magenta')}"
        except Exception:
            pass

    name_s = _style(tool.name, "green")
    if compact or len(params) <= 2:
        return f"{indent}{name_s}({', '.join(params)}){ret_type}"
    else:
        param_indent = indent + "    "
        params_str = ",\n".join(f"{param_indent}{p}" for p in params)
        return f"{indent}{name_s}(\n{params_str}\n{indent}){ret_type}"


def _get_tool_module(name: str) -> str:
    """Get logical module for a tool name."""
    if "recommend" in name or "applicab" in name:
        return "auto"
    if "correct" in name:
        return "correct"
    if "posthoc" in name:
        return "posthoc"
    if "power" in name:
        return "power"
    if "effect" in name:
        return "effect_sizes"
    if "normality" in name:
        return "normality"
    if "describe" in name:
        return "descriptive"
    if "format" in name:
        return "formatting"
    if "p_to_stars" in name:
        return "formatting"
    return "general"


def cmd_list_tools(
    *,
    verbose: int = 0,
    compact: bool = False,
    module_filter: str | None = None,
    as_json: bool = False,
) -> int:
    """List all available MCP tools."""
    tool_objects = _list_tool_objects()
    tools_by_name = {t.name: t for t in tool_objects}
    tools = list(tools_by_name.keys())
    total = len(tools)

    # Group by logical module
    modules: dict[str, list[str]] = {}
    for tool_name in sorted(tools):
        module = _get_tool_module(tool_name)
        modules.setdefault(module, []).append(tool_name)

    if module_filter:
        module_filter = module_filter.lower()
        if module_filter not in modules:
            print(f"ERROR: Unknown module '{module_filter}'")
            print(f"Available modules: {', '.join(sorted(modules.keys()))}")
            return 1
        modules = {module_filter: modules[module_filter]}

    if as_json:
        import json

        output = {
            "name": "scitex-stats",
            "total": sum(len(t) for t in modules.values()),
            "modules": {},
        }
        for mod, tool_list in modules.items():
            output["modules"][mod] = {
                "count": len(tool_list),
                "tools": tool_list,
            }
        print(json.dumps(output, indent=2))
        return 0

    print(_style("SciTeX Stats MCP: scitex-stats", "cyan", bold=True))
    print(f"Tools: {total} ({len(modules)} modules)\n")

    for module in sorted(modules.keys()):
        mod_tools = sorted(modules[module])
        print(_style(f"{module}: {len(mod_tools)} tools", "green", bold=True))
        for tool_name in mod_tools:
            tool_obj = tools_by_name.get(tool_name)

            if verbose == 0:
                print(f"  {tool_name}")
            elif verbose == 1:
                sig = (
                    _format_tool_signature(tool_obj, compact=compact)
                    if tool_obj
                    else f"  {tool_name}"
                )
                print(sig)
            elif verbose == 2:
                sig = (
                    _format_tool_signature(tool_obj, compact=compact)
                    if tool_obj
                    else f"  {tool_name}"
                )
                print(sig)
                if tool_obj and tool_obj.description:
                    desc = tool_obj.description.split("\n")[0].strip()
                    print(f"    {desc}")
                print()
            else:
                sig = (
                    _format_tool_signature(tool_obj, compact=compact)
                    if tool_obj
                    else f"  {tool_name}"
                )
                print(sig)
                if tool_obj and tool_obj.description:
                    for line in tool_obj.description.strip().split("\n"):
                        print(f"    {line}")
                print()
        print()

    return 0


def cmd_doctor() -> int:
    """Check MCP server health and configuration."""
    print(f"scitex-stats {__version__}\n")
    print("Health Check")
    print("=" * 40)

    checks = []

    try:
        import fastmcp

        checks.append(("fastmcp", True, fastmcp.__version__))
    except ImportError:
        checks.append(("fastmcp", False, "not installed"))

    try:
        tool_count = len(_list_tool_objects())
        checks.append(("MCP server", True, f"{tool_count} tools"))
    except Exception as e:
        checks.append(("MCP server", False, str(e)))

    scitex_path = shutil.which("scitex-stats")
    if scitex_path:
        checks.append(("CLI", True, scitex_path))
    else:
        checks.append(("CLI", False, "not in PATH"))

    all_ok = True
    for name, ok, info in checks:
        status = "+" if ok else "x"
        if not ok:
            all_ok = False
        print(f"  {status} {name}: {info}")

    print()
    if all_ok:
        print("All checks passed!")
    else:
        print("Some checks failed. Run 'pip install scitex-stats[mcp]' to fix.")

    return 0 if all_ok else 1


def cmd_config(*, as_json: bool = False) -> int:
    """Show Claude Desktop configuration snippet."""
    scitex_path = shutil.which("scitex-stats")

    if as_json:
        import json as _json

        payload = {
            "package": "scitex-stats",
            "version": __version__,
            "installation_path": scitex_path,
            "config_paths": {
                "macos": "~/Library/Application Support/Claude/claude_desktop_config.json",
                "linux": "~/.config/Claude/claude_desktop_config.json",
            },
            "snippets": {
                "cli": CLAUDE_DESKTOP_CONFIG_CLI,
                "python_module": CLAUDE_DESKTOP_CONFIG_PYTHON,
            },
        }
        print(_json.dumps(payload, indent=2))
        return 0

    print(f"scitex-stats {__version__}\n")
    print("Add this to your Claude Desktop config file:\n")
    print("  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json")
    print("  Linux: ~/.config/Claude/claude_desktop_config.json\n")

    if scitex_path:
        print(f"Your installation path: {scitex_path}\n")

    print("Option 1: CLI command (replace path with your installation)")
    print(CLAUDE_DESKTOP_CONFIG_CLI)
    print("\nOption 2: Python module (replace path with your installation)")
    print(CLAUDE_DESKTOP_CONFIG_PYTHON)
    return 0


# EOF
