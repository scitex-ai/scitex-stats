#!/usr/bin/env python3
# File: src/scitex_stats/_cli/verify.py

"""``scitex-stats verify`` — check a saved result against its provenance receipt."""

from __future__ import annotations

import json
import sys

import click


@click.command("verify")
@click.argument("result_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("data", required=False)
@click.option("--x", default=None, help="Column holding `data` (CSV input).")
@click.option("--y", default=None, help="Column holding `data2` (CSV input).")
@click.option("--groups", default=None, help="Comma-separated columns for `groups`.")
@click.option("--no-recompute", is_flag=True, default=False, help="Only check hashes.")
@click.option("--json/--no-json", "as_json", default=True, help="JSON report (default).")
def verify(result_file, data, x, y, groups, no_recompute, as_json):
    """Verify RESULT_FILE (a saved result JSON) bit-for-bit.

    Checks the receipt hash, the result hash, the input-data hashes and a
    recompute. Without DATA the copy embedded in the receipt is used.
    Exit code 0 when verified, 1 otherwise.

    \b
    Example:
        $ scitex-stats verify result.json
        $ scitex-stats verify result.json data.csv --x group_a --y group_b
        $ scitex-stats verify result.json data.csv --groups a,b,c --no-recompute
    """
    from scitex_stats._verify import verify as _verify

    from .stats import _read_data, _select_column

    kwargs = {}
    if data is not None:
        table = _read_data(data)
        if groups:
            kwargs["groups"] = [table[c.strip()].to_numpy() for c in groups.split(",")]
        elif x:
            kwargs["data"] = _select_column(table, x)
            if y:
                kwargs["data2"] = _select_column(table, y)
        else:
            kwargs["data"] = table.to_numpy() if hasattr(table, "to_numpy") else table

    report = _verify(result_file, recompute=not no_recompute, **kwargs)
    if as_json:
        click.echo(json.dumps(report, indent=2, default=str))
    else:
        click.echo(report["summary"])
        for check in report["checks"]:
            click.echo(f"  {check['status']:4s}  {check['name']:9s}  {check['detail']}")
        for warning in report["warnings"]:
            click.echo(f"  warn  {warning}")
    sys.exit(0 if report["verified"] else 1)


# EOF
