#!/usr/bin/env python3
# File: src/scitex_stats/_cli/recommend.py
"""CLI workers for check_applicability / recommend_test / run_all_applicable."""

from __future__ import annotations

import json
import sys
from typing import Any, List, Optional, Tuple

import click


def _load_groups(data: str, columns: Optional[str]) -> Tuple[Any, Optional[List[str]]]:
    """CSV/TSV: one column per group (``--groups`` picks columns); JSON: list of groups or table."""
    if data == "-":
        return json.load(sys.stdin), None
    if data.endswith(".json"):
        with open(data) as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return list(payload.values()), [str(k) for k in payload]
        return payload, None
    if data.endswith((".csv", ".tsv")):
        import pandas as pd

        df = pd.read_csv(data, sep="\t" if data.endswith(".tsv") else ",")
        if columns:
            names = [c.strip() for c in columns.split(",")]
            missing = [c for c in names if c not in df.columns]
            if missing:
                raise SystemExit(f"Error: column(s) {missing} not found. Available: {list(df.columns)}")
            df = df[names]
        return [df[c].tolist() for c in df.columns], [str(c) for c in df.columns]
    raise SystemExit(f"Unsupported data format: {data} (use .csv / .tsv / .json or '-' for stdin JSON)")


def _print_text(out: dict) -> None:
    rows = out.get("applicability", [])
    for row in rows:
        mark = "✓" if row["applicable"] else "✗"
        click.echo(f"{mark} {row['label']}")
        for reason in row["reasons"]:
            click.echo(f"    - {reason}")
    if out.get("primary"):
        click.echo(f"\nRecommended: {out['primary']['label']}\n  {out['primary']['reason']}\n  Path: {out['summary']}")
    for note in out.get("notes", []):
        click.echo(f"  note: {note['text']}")


def run_applicability(*, data: str, groups: Optional[str] = None, design: Optional[str] = None, scale: Optional[str] = None, as_json: bool = True) -> int:
    """Print ✓/✗ with reasons for every test. Returns 0."""
    import scitex_stats as ss

    values, names = _load_groups(data, groups)
    rows = ss.check_applicability(values, design, scale=scale, group_names=names)
    if as_json:
        click.echo(json.dumps(rows, indent=2, default=str))
    else:
        _print_text({"applicability": rows})
    return 0


def run_recommend_test(*, data: str, groups: Optional[str] = None, design: Optional[str] = None, scale: Optional[str] = None, assume_equal_variance: bool = False, as_json: bool = True) -> int:
    """Print the primary recommendation, decision path and applicability. Returns 0."""
    import scitex_stats as ss

    values, names = _load_groups(data, groups)
    out = ss.recommend_test(values, design, scale=scale, group_names=names, assume_equal_variance=assume_equal_variance)
    if as_json:
        click.echo(json.dumps(out, indent=2, default=str))
    else:
        _print_text(out)
    return 0


def run_run_all(*, data: str, groups: Optional[str] = None, design: Optional[str] = None, scale: Optional[str] = None, primary: Optional[str] = None, alternative: str = "two-sided", as_json: bool = True) -> int:
    """Run every applicable test (primary + sensitivity). Returns 0, or 1 on invalid input."""
    import scitex_stats as ss

    values, names = _load_groups(data, groups)
    try:
        out = ss.run_all_applicable(values, design, scale=scale, group_names=names, primary=primary, alternative=alternative)
    except ValueError as exc:
        click.echo(json.dumps({"error": str(exc)}), err=True)
        return 1
    if as_json:
        click.echo(json.dumps(out, indent=2, default=str))
        return 0
    click.echo(f"WARNING: {out['warning']}\n")
    for r in out["results"]:
        p = f"p {r['p_apa']}" if r["p_apa"] else (r["error"] or "no p-value")
        click.echo(f"[{r['role']:<11}] {r['label']}: {r['stat_symbol']} = {r['statistic']}, {p}")
    click.echo(f"\nAgreement: {out['agreement']['summary']}")
    return 0


# EOF
