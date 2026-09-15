#!/usr/bin/env python3
# File: src/scitex_stats/_cli/validate_apa.py
"""``scitex-stats validate-apa``: check statistics text against APA 7."""

from __future__ import annotations

import json
import sys

import click


@click.command("validate-apa")
@click.argument("text", required=False)
@click.option("--html", "html_text", default=None, help="HTML rendering to check italics in.")
@click.option("--result", "result_path", default=None, type=click.Path(exists=True, dir_okay=False),
              help="JSON result from `tests execute` to compare against.")
@click.option("--json", "as_json", is_flag=True, help="Print the full report as JSON.")
def validate_apa_cmd(text, html_text, result_path, as_json):
    """Report APA 7 violations in a results string (TEXT, or stdin).

    \b
    Example:
        $ scitex-stats validate-apa "t(14) = -6.354, p = 0.0000, d = 3.2"
        $ echo "F(2, 27) = 4.51, p = .020, η² = .25, N = 30" | scitex-stats validate-apa
    """
    from scitex_stats._utils._apa import validate_apa

    if text is None and html_text is None:
        text = sys.stdin.read()
    result = None
    if result_path:
        with open(result_path) as f:
            result = json.load(f)
    report = validate_apa(text or "", html=html_text, result=result)
    if as_json:
        click.echo(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for v in report["violations"]:
            click.echo(f"{v['code']}: {v['message']} Fix: {v['fix']} [{v['reference']}] «{v['excerpt']}»")
        if report["expected"]:
            click.echo(f"expected: {report['expected']}")
        click.echo("OK" if report["ok"] else f"{len(report['violations'])} violation(s)")
    sys.exit(0 if report["ok"] else 1)


# EOF
