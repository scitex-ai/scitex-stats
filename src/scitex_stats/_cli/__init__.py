#!/usr/bin/env python3
# File: src/scitex_stats/_cli/__init__.py

"""scitex-stats CLI (Click).

Subcommand groups:
    mcp                 - MCP server commands (start / list-tools / doctor / install)
    tests               - Statistical tests (list / execute / describe / recommend)
    python-api          - Python package introspection (list)
    list-python-apis    - Convenience alias for: python-api list scitex_stats
    format-pvalue       - Convert a p-value to significance stars
"""

from __future__ import annotations

import sys as _sys

from ._version_fastpath import maybe_print_version_and_exit as _maybe_version_exit

# Must run before any import below that transitively pulls in
# `scitex_dev._cli` (see `_version_fastpath.py` for why).
_maybe_version_exit(_sys.argv[1:])

import json
import sys

import click

from .. import __version__
from ._help import print_help_recursive as _print_help_recursive
from ._integrations import attach_scitex_dev_integrations
from .introspect import (
    cmd_api as _cmd_api,
    cmd_list_python_apis as _cmd_list_python_apis,
)
from .mcp import (
    CLAUDE_DESKTOP_CONFIG_CLI,
    CLAUDE_DESKTOP_CONFIG_PYTHON,
    cmd_config as _cmd_config,
    cmd_doctor as _cmd_doctor,
    cmd_list_tools as _cmd_list_tools,
    cmd_start as _cmd_start,
)
from .skills_group import skills_group as _skills_group
from .gui import gui as _gui
from .stats import (
    run_format_pvalue as _run_format_pvalue,
    run_tests_describe as _run_tests_describe,
    run_tests_execute as _run_tests_execute,
    run_tests_list as _run_tests_list,
    run_tests_recommend as _run_tests_recommend,
)


def _get_version() -> str:
    return __version__


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(_get_version(), "-V", "--version", prog_name="scitex-stats")
@click.option(
    "--help-recursive",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_help_recursive,
    help="Show help for the root and every subcommand.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON output where supported (propagates to subcommands).",
)
@click.pass_context
def main(ctx, as_json):
    """SciTeX Stats — publication-ready statistical testing (23 tests, effect sizes,
    power analysis, MCP server).

    \b
    Configuration precedence (highest -> lowest):
      1. Explicit CLI flags
      2. ./config.yaml (project-local)
      3. $SCITEX_STATS_CONFIG (path to a YAML file)
      4. ~/.scitex/stats/config.yaml (user-wide)
      5. Built-in defaults

    \b
    Example:
        $ scitex-stats tests list
        $ scitex-stats tests execute ttest_ind data.csv --x a --y b
        $ scitex-stats mcp start --yes
        $ scitex-stats list-python-apis --json
    """
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ----------------------------------------------------------------------------
# mcp group
# ----------------------------------------------------------------------------


@main.group()
def mcp():
    """MCP (Model Context Protocol) server commands.

    \b
    Quick start:
      scitex-stats mcp list-tools
      scitex-stats mcp doctor
      scitex-stats mcp install
      scitex-stats mcp start
    """


@mcp.command(
    "show-installation", hidden=True, context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def mcp_show_installation_deprecated(ctx):
    """(deprecated) Renamed to `install`."""
    click.echo(
        "error: `scitex-stats mcp show-installation` was renamed to "
        "`scitex-stats mcp install`.\n"
        "Re-run with: scitex-stats mcp install",
        err=True,
    )
    ctx.exit(2)


@mcp.command("install")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON.")
@click.option("--dry-run", is_flag=True, help="Accepted for §2; this verb is informational, never mutates state.")
@click.option("--yes", "-y", is_flag=True, help="Accepted for §2; this verb is informational, never mutates state.")
def mcp_install(as_json, dry_run, yes):
    """Print the Claude Desktop config snippet for the scitex-stats MCP server.

    (rename of show-installation)

    \b
    Example:
        $ scitex-stats mcp install
        $ scitex-stats mcp install --json
    """
    del dry_run, yes  # audit §2 — no-op flags
    return _cmd_config(as_json=as_json)


@mcp.command("list-tools")
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig, -vv +desc, -vvv full."
)
@click.option("-c", "--compact", is_flag=True, help="Compact signatures (single line).")
@click.option("-m", "--module", "module_filter", default=None, help="Filter by module.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def mcp_list_tools(verbose, compact, module_filter, as_json):
    """List all available MCP tools registered under scitex-stats.

    \b
    Example:
        $ scitex-stats mcp list-tools
        $ scitex-stats mcp list-tools -vv
        $ scitex-stats mcp list-tools --module correct --json
    """
    return _cmd_list_tools(
        verbose=verbose, compact=compact, module_filter=module_filter, as_json=as_json
    )


@mcp.command("doctor")
def mcp_doctor():
    """Verify scitex-stats MCP server dependencies + tool count + CLI presence.

    \b
    Example:
        $ scitex-stats mcp doctor
    """
    return _cmd_doctor()


@mcp.command("start")
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport: stdio (default) or sse.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the launch plan without starting the server.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Skip confirmation (mutating: starts a long-running server).",
)
def mcp_start(transport, dry_run, yes):
    """Launch the scitex-stats MCP server.

    \b
    Example:
        $ scitex-stats mcp start                  # stdio (default)
        $ scitex-stats mcp start --transport sse  # SSE for HTTP clients
        $ scitex-stats mcp start --dry-run        # show what would launch
    """
    return _cmd_start(transport=transport, dry_run=dry_run, yes=yes)


# ----------------------------------------------------------------------------
# tests group
# ----------------------------------------------------------------------------


@main.group()
def tests():
    """Statistical tests — list / execute / describe / recommend.

    \b
    Quick start:
      scitex-stats tests list
      scitex-stats tests execute ttest_ind data.csv --x a --y b
      scitex-stats tests describe data.csv -c group_a
      scitex-stats tests recommend --n-groups 2 --sample-sizes 30,28
    """


@tests.command("list")
@click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="Emit JSON list (default) or one name per line.",
)
def tests_list(as_json):
    """List all available statistical test names.

    \b
    Example:
        $ scitex-stats tests list
        $ scitex-stats tests list --no-json
    """
    return _run_tests_list(as_json=as_json)


@tests.command("execute")
@click.argument("test_name")
@click.argument("data")
@click.option("--x", default=None, help="Column for the first sample.")
@click.option("--y", default=None, help="Column for the second sample.")
@click.option(
    "--groups",
    default=None,
    help="Comma-separated columns for K groups (anova/kruskal).",
)
@click.option(
    "--popmean", type=float, default=0.0, help="Population mean (1-sample tests)."
)
@click.option(
    "--alternative",
    type=click.Choice(["two-sided", "greater", "less"]),
    default="two-sided",
    help="Alternative hypothesis.",
)
@click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="JSON output (default) or plain key/value pairs.",
)
def tests_execute(test_name, data, x, y, groups, popmean, alternative, as_json):
    """Run a named statistical test on CSV/NPY/JSON data.

    \b
    Example:
        $ scitex-stats tests execute ttest_ind data.csv --x group_a --y group_b
        $ scitex-stats tests execute anova data.csv --groups col1,col2,col3
        $ scitex-stats tests execute pearson data.csv --x x --y y
        $ scitex-stats tests execute chi2 contingency.csv
    """
    return _run_tests_execute(
        test_name=test_name,
        data=data,
        x=x,
        y=y,
        groups=groups,
        popmean=popmean,
        alternative=alternative,
        as_json=as_json,
    )


@tests.command("describe")
@click.argument("data")
@click.option(
    "-c",
    "--column",
    default=None,
    help="Column to describe (CSV only). Defaults to all numeric.",
)
@click.option(
    "--funcs",
    default=None,
    help="Comma-separated funcs to compute (e.g. 'mean,std,median').",
)
@click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="JSON output (default) or plain key/value pairs.",
)
def tests_describe(data, column, funcs, as_json):
    """Compute descriptive statistics from a CSV/NPY/JSON file.

    \b
    Example:
        $ scitex-stats tests describe data.csv -c group_a
        $ scitex-stats tests describe data.npy --funcs mean,std,median
        $ cat numbers.json | scitex-stats tests describe -
    """
    return _run_tests_describe(data=data, column=column, funcs=funcs, as_json=as_json)


@tests.command("recommend")
@click.option("--n-groups", type=int, required=True, help="Number of groups (1, 2, K).")
@click.option(
    "--sample-sizes",
    required=True,
    help="Comma-separated per-group sample sizes (e.g. 30,28).",
)
@click.option(
    "--outcome",
    type=click.Choice(["continuous", "ordinal", "binary", "categorical"]),
    default="continuous",
    help="Outcome variable type.",
)
@click.option(
    "--design",
    type=click.Choice(["between", "within", "mixed"]),
    default="between",
    help="Experimental design.",
)
@click.option(
    "--paired",
    is_flag=True,
    default=False,
    help="Paired/related samples (also sets --design=within).",
)
@click.option("--top-k", type=int, default=3, help="How many tests to return.")
@click.option(
    "--json/--no-json",
    "as_json",
    default=True,
    help="JSON output (default) or one name per line.",
)
def tests_recommend(n_groups, sample_sizes, outcome, design, paired, top_k, as_json):
    """Recommend statistical tests for a study design.

    \b
    Example:
        $ scitex-stats tests recommend --n-groups 2 --sample-sizes 30,28 --outcome continuous
        $ scitex-stats tests recommend --n-groups 3 --sample-sizes 20,20,20 --paired
    """
    return _run_tests_recommend(
        n_groups=n_groups,
        sample_sizes=sample_sizes,
        outcome=outcome,
        design=design,
        paired=paired,
        top_k=top_k,
        as_json=as_json,
    )


# ----------------------------------------------------------------------------
# python-api group + list-python-apis alias
# ----------------------------------------------------------------------------


@main.group("python-api")
def python_api():
    """Python package introspection — `python-api list <dotted_path>`.

    \b
    Quick start:
      scitex-stats python-api list scitex_stats
      scitex-stats python-api list scitex_stats -v --max-depth 3
      scitex-stats python-api list scitex_stats.correct --json
    """


@python_api.command("list")
@click.argument("dotted_path")
@click.option("-v", "--verbose", count=True, help="Verbosity: -v +doc, -vv full doc.")
@click.option(
    "-d", "--max-depth", type=int, default=5, help="Max recursion depth (default: 5)."
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def python_api_list(dotted_path, verbose, max_depth, as_json):
    """List the public API tree of a Python module.

    \b
    Example:
        $ scitex-stats python-api list scitex_stats
        $ scitex-stats python-api list scitex_stats -v --max-depth 3
        $ scitex-stats python-api list scitex_stats.correct --json
    """
    return _cmd_api(
        dotted_path=dotted_path,
        verbose=verbose,
        max_depth=max_depth,
        as_json=as_json,
    )


@main.command("list-python-apis")
@click.option("-v", "--verbose", count=True, help="Verbosity: -v +doc, -vv full doc.")
@click.option(
    "-d", "--max-depth", type=int, default=5, help="Max recursion depth (default: 5)."
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def list_python_apis(verbose, max_depth, as_json):
    """List Python APIs (alias for: scitex-stats python-api list scitex_stats).

    \b
    Example:
        $ scitex-stats list-python-apis
        $ scitex-stats list-python-apis -v --max-depth 3
        $ scitex-stats list-python-apis --json
    """
    return _cmd_list_python_apis(verbose=verbose, max_depth=max_depth, as_json=as_json)


# ----------------------------------------------------------------------------
# format-pvalue leaf
# ----------------------------------------------------------------------------


@main.command("format-pvalue")
@click.argument("p", type=float)
@click.option("--style", default=None, help="Style ID (default: built-in).")
def format_pvalue(p, style):
    """Convert a p-value to significance stars.

    \b
    Example:
        $ scitex-stats format-pvalue 0.001
        $ scitex-stats format-pvalue 0.5
    """
    return _run_format_pvalue(p=p, style=style)


# ----------------------------------------------------------------------------
# skills group (self-contained — list / get / install bundled _skills/)
# ----------------------------------------------------------------------------

main.add_command(_skills_group, name="skills")

# gui group (standalone Statistics app: open / serve / status / stop). The
# import is cheap (reads only DEFAULT_PORT); the scitex-app SDK is pulled
# lazily inside the subcommands, so a base install (no [server]) still works.
main.add_command(_gui, name="gui")


# §1a install-shell-completion/print-shell-completion + optional scitex-dev
# docs/skills subcommands — both best-effort, see _integrations.py.
attach_scitex_dev_integrations(main)


def _entry(argv=None) -> int:
    """Console-script entry point."""
    try:
        main.main(args=argv, standalone_mode=False, prog_name="scitex-stats")
        return 0
    except click.exceptions.Exit as e:
        return int(e.exit_code or 0)
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except SystemExit as e:
        return int(e.code or 0)


if __name__ == "__main__":
    sys.exit(_entry())

# EOF


# audit §4 — inject version into root --help
try:
    from importlib.metadata import version as _v
    main.help = (
        f"scitex-stats (v{_v('scitex-stats')}) — "
        + (main.help or "").lstrip()
    )
except Exception:
    pass
