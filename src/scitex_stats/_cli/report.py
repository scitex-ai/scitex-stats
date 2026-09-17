#!/usr/bin/env python3
# File: src/scitex_stats/_cli/report.py

"""``scitex-stats generate-report`` — one bundled PDF (plus HTML/Markdown) for a dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.command("generate-report")
@click.argument("data", type=click.Path(exists=True, dir_okay=False))
@click.option("--out", "-o", "out", default="report.pdf", show_default=True, help="PDF path; HTML/Markdown go next to it.")
@click.option("--design", type=click.Choice(["between", "within", "paired"]), default="between", show_default=True,
              help="Independent groups, or repeated measures (rows are subjects).")
@click.option("--group-col", default=None, help="Long format: column naming the group.")
@click.option("--value-col", default=None, help="Long format: column holding the values.")
@click.option("--subject-col", default=None, help="Long format, within design: column naming the subject.")
@click.option("--alpha", type=float, default=0.05, show_default=True)
@click.option("--posthoc", type=click.Choice(["auto", "always", "never"]), default="auto", show_default=True,
              help="auto: after a significant omnibus test on 3+ groups; always: run and flag.")
@click.option("--format", "formats", default="pdf,html,md", show_default=True, help="Comma-separated: pdf, html, md.")
@click.option("--title", default="Statistical report", show_default=True)
@click.option("--y-label", default="Value", show_default=True)
@click.option("--dry-run", is_flag=True, help="Analyse and print the summary; write nothing.")
@click.option("--yes", "-y", "overwrite", is_flag=True, help="Overwrite an existing output file instead of refusing.")
@click.option("--json", "as_json", is_flag=True, help="Print the summary and written paths as JSON.")
def report(data, out, design, group_col, value_col, subject_col, alpha, posthoc, formats, title, y_label, dry_run, overwrite, as_json):
    """Write a bundled statistical report for DATA (CSV/TSV, one column per group).

    Sections: report information, data summary, assumption checks, test
    selection, primary result, sensitivity analyses, post-hoc comparisons,
    figures, methods paragraph, references.

    \b
    Example:
        $ scitex-stats generate-report data.csv --out report.pdf
        $ scitex-stats generate-report long.csv --group-col condition --value-col score --design within
        $ scitex-stats generate-report data.csv --dry-run --json
    """
    from scitex_stats.reporting._pdf import (
        RendererUnavailable,
        build_report,
        planned_paths,
    )
    from scitex_stats.reporting._pdf import report as _report

    if not dry_run and not overwrite:
        wanted = [f.strip() for f in formats.split(",") if f.strip()]
        # The named output AND every sidecar the writer would produce: checking only
        # --out silently replaced an existing same-stem .html, .md and figure.
        candidates = [Path(out)] + [path for path in planned_paths(out, wanted) if path != Path(out)]
        existing = [path for path in candidates if path.exists()]
        if existing:
            listed = ", ".join(str(path) for path in existing)
            click.echo(f"Error: {listed} already exist(s); pass --yes to overwrite.", err=True)
            sys.exit(1)

    spec = {"type": design}
    for key, value in (("group_col", group_col), ("value_col", value_col), ("subject_col", subject_col)):
        if value:
            spec[key] = value
    kwargs = dict(alpha=alpha, posthoc=posthoc, title=title, y_label=y_label)
    try:
        if dry_run:
            payload = {"summary": build_report(data, spec, **kwargs)["summary"], "paths": {}}
        else:
            wanted = [f.strip() for f in formats.split(",") if f.strip()]
            result = _report(data, spec, out, formats=wanted, **kwargs)
            payload = {"summary": result["summary"], "paths": result["paths"]}
    except RendererUnavailable as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except (ValueError, TypeError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    if as_json:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return
    s = payload["summary"]
    click.echo(f"Primary: {s['primary_test']}  {s['primary_apa']}")
    ph = s.get("posthoc")
    if ph:
        state = "run" if ph["ran"] else "not run"
        click.echo(f"Post-hoc: {ph['method']} ({ph['correction']}), {state}")
    for kind, path in payload["paths"].items():
        click.echo(f"Wrote {kind}: {path}")


# EOF
