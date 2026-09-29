#!/usr/bin/env python3
# File: src/scitex_stats/_cli/introspect.py

"""Introspection CLI worker functions for scitex-stats (Click-friendly, no argparse)."""

from __future__ import annotations

import importlib
import inspect
import sys

import click

TYPE_COLORS = {"M": "blue", "C": "magenta", "F": "green", "V": "cyan"}

ANSI = {
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "yellow": "\033[33m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def _style(text: str, fg: str = None, bold: bool = False) -> str:
    """Apply ANSI styling to text."""
    if not sys.stdout.isatty():
        return text
    prefix = ""
    if bold:
        prefix += ANSI["bold"]
    if fg and fg in ANSI:
        prefix += ANSI[fg]
    if prefix:
        return f"{prefix}{text}{ANSI['reset']}"
    return text


def _simplify_type(ann) -> str:
    """Simplify type annotation to base type name."""
    import types
    import typing

    if isinstance(ann, types.UnionType):
        args = typing.get_args(ann)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args:
            return "Optional"
        return "Union"

    origin = typing.get_origin(ann)
    if origin is not None:
        if origin is typing.Union:
            args = typing.get_args(ann)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1 and type(None) in args:
                return "Optional"
            return "Union"
        return origin.__name__ if hasattr(origin, "__name__") else str(origin)

    if hasattr(ann, "__name__"):
        return ann.__name__

    type_str = str(ann).replace("typing.", "")
    if "[" in type_str:
        type_str = type_str.split("[")[0]
    return type_str


def _format_python_signature(func, multiline: bool = True, indent: str = "  ") -> tuple:
    """Format Python function signature with colors."""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return _style(func.__name__, "green", bold=True), ""

    params = []
    for name, param in sig.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            type_str = _simplify_type(param.annotation)
        else:
            type_str = None

        if param.default != inspect.Parameter.empty:
            default = param.default
            def_str = repr(default) if len(repr(default)) < 20 else "..."
            if type_str:
                p = f"{_style(name, 'white', bold=True)}: {_style(type_str, 'cyan')} = {_style(def_str, 'yellow')}"
            else:
                p = f"{_style(name, 'white', bold=True)} = {_style(def_str, 'yellow')}"
        else:
            if type_str:
                p = f"{_style(name, 'white', bold=True)}: {_style(type_str, 'cyan')}"
            else:
                p = _style(name, "white", bold=True)
        params.append(p)

    ret_str = ""
    if sig.return_annotation != inspect.Parameter.empty:
        ret = sig.return_annotation
        ret_name = ret.__name__ if hasattr(ret, "__name__") else str(ret)
        ret_name = ret_name.replace("typing.", "")
        ret_str = f" -> {_style(ret_name, 'magenta')}"

    name_s = _style(func.__name__, "green", bold=True)

    if multiline and len(params) > 2:
        param_indent = indent + "    "
        params_str = ",\n".join(f"{param_indent}{p}" for p in params)
        sig_s = f"(\n{params_str}\n{indent}){ret_str}"
    else:
        sig_s = f"({', '.join(params)}){ret_str}"

    return name_s, sig_s


def _get_api_tree(module, max_depth: int = 5, docstring: bool = False) -> list:
    """Get API tree for a module."""
    results = []

    def _visit(obj, name: str, depth: int, visited: set):
        if depth > max_depth:
            return
        obj_id = id(obj)
        if obj_id in visited:
            return
        visited.add(obj_id)

        if inspect.ismodule(obj):
            obj_type = "M"
        elif inspect.isclass(obj):
            obj_type = "C"
        elif callable(obj):
            obj_type = "F"
        else:
            obj_type = "V"

        entry = {"Name": name, "Type": obj_type, "Depth": depth}
        if docstring:
            entry["Docstring"] = inspect.getdoc(obj) or ""
        results.append(entry)

        if inspect.ismodule(obj) and depth < max_depth:
            if hasattr(obj, "__all__"):
                members = [(n, getattr(obj, n, None)) for n in obj.__all__]
            else:
                members = [
                    (n, v) for n, v in inspect.getmembers(obj) if not n.startswith("_")
                ]
            for member_name, member_obj in members:
                if member_obj is not None:
                    _visit(member_obj, f"{name}.{member_name}", depth + 1, visited)

    _visit(module, module.__name__.split(".")[-1], 0, set())
    return results


def cmd_api(
    *,
    dotted_path: str,
    verbose: int = 0,
    max_depth: int = 5,
    as_json: bool = False,
) -> int:
    """List API tree of a Python module."""
    dotted_path = dotted_path.replace("-", "_")

    try:
        module = importlib.import_module(dotted_path)
    except ImportError as e:
        click.echo(f"Error importing {dotted_path}: {e}", err=True)
        return 1

    df = _get_api_tree(module, max_depth=max_depth, docstring=(verbose >= 1))

    if as_json:
        import json

        click.echo(json.dumps(df, indent=2))
        return 0

    click.echo(_style(f"API tree of {dotted_path} ({len(df)} items):", fg="cyan"))
    legend = " ".join(
        _style(f"[{t}]={n}", fg=TYPE_COLORS[t])
        for t, n in [
            ("M", "Module"),
            ("C", "Class"),
            ("F", "Function"),
            ("V", "Variable"),
        ]
    )
    click.echo(f"Legend: {legend}")

    for row in df:
        indent = "  " * row["Depth"]
        t = row["Type"]
        type_s = _style(f"[{t}]", fg=TYPE_COLORS.get(t, "yellow"))
        name = row["Name"].split(".")[-1]

        if t == "F":
            try:
                parts = row["Name"].split(".")
                obj = module
                for part in parts[1:]:
                    obj = getattr(obj, part, None)
                    if obj is None:
                        break
                if obj and callable(obj):
                    name_s, sig_s = _format_python_signature(obj, indent=indent)
                    click.echo(f"{indent}{type_s} {name_s}{sig_s}")
                else:
                    name_s = _style(name, "green", bold=True)
                    click.echo(f"{indent}{type_s} {name_s}")
            except Exception:
                name_s = _style(name, "green", bold=True)
                click.echo(f"{indent}{type_s} {name_s}")
        else:
            name_s = _style(name, fg=TYPE_COLORS.get(t, "white"), bold=True)
            click.echo(f"{indent}{type_s} {name_s}")

        if verbose >= 1 and row.get("Docstring"):
            if verbose == 1:
                doc = row["Docstring"].split("\n")[0][:60]
                click.echo(f"{indent}    - {doc}")
            else:
                for ln in row["Docstring"].split("\n"):
                    click.echo(f"{indent}    {ln}")

    return 0


def cmd_list_python_apis(
    *, verbose: int = 0, max_depth: int = 5, as_json: bool = False
) -> int:
    """List Python APIs (alias for: python-api list scitex_stats)."""
    return cmd_api(
        dotted_path="scitex_stats",
        verbose=verbose,
        max_depth=max_depth,
        as_json=as_json,
    )


# EOF
