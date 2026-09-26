#!/usr/bin/env python3
# File: src/scitex_stats/_cli/tests_group.py
"""`scitex-stats tests` — list / execute / describe / recommend / check-applicability / recommend-test / execute-all."""

from __future__ import annotations

import click

from scitex_dev.ecosystem import deprecated_alias

from .recommend import (
    run_applicability as _run_applicability,
    run_recommend_test as _run_recommend_test,
    run_run_all as _run_run_all,
)
from .stats import (
    run_tests_describe as _run_tests_describe,
    run_tests_execute as _run_tests_execute,
    run_tests_list as _run_tests_list,
    run_tests_recommend as _run_tests_recommend,
)


@click.group("tests")
def tests_group():
    """Statistical tests — list / execute / describe / recommend.

    \b
    Quick start:
      scitex-stats tests list
      scitex-stats tests execute ttest_ind data.csv --x a --y b
      scitex-stats tests describe data.csv -c group_a
      scitex-stats tests recommend --n-groups 2 --sample-sizes 30,28
      scitex-stats tests recommend-test data.csv --design independent
      scitex-stats tests execute-all data.csv --design independent
    """


@tests_group.command("list")
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


@tests_group.command("execute")
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


@tests_group.command("describe")
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


@tests_group.command("recommend")
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


_DESIGN = click.option(
    "--design",
    type=click.Choice(["independent", "paired"]),
    default=None,
    help="independent or paired. Unset is treated as independent and flagged in the output.",
)
_SCALE = click.option(
    "--scale",
    type=click.Choice(["continuous", "ordinal", "categorical"]),
    default=None,
    help="Measurement scale (categorical: DATA is a contingency table).",
)
_GROUPS = click.option("--groups", default=None, help="Comma-separated CSV columns to use as groups.")


@tests_group.command("check-applicability")
@click.argument("data")
@_GROUPS
@_DESIGN
@_SCALE
@click.option("--json/--no-json", "as_json", default=True, help="JSON (default) or ✓/✗ lines.")
def tests_applicability(data, groups, design, scale, as_json):
    """Decide for every test whether it applies to DATA, with reasons.

    \b
    Example:
        $ scitex-stats tests check-applicability data.csv --design independent
        $ scitex-stats tests check-applicability table.json --scale categorical --no-json
    """
    return _run_applicability(data=data, groups=groups, design=design, scale=scale, as_json=as_json)


@tests_group.command("recommend-test")
@click.argument("data")
@_GROUPS
@_DESIGN
@_SCALE
@click.option("--assume-equal-variance", is_flag=True, default=False, help="Documented reason to prefer Student over Welch.")
@click.option("--json/--no-json", "as_json", default=True, help="JSON (default) or readable text.")
def tests_recommend_test(data, groups, design, scale, assume_equal_variance, as_json):
    """Recommend ONE primary test for DATA, with reason and decision path.

    \b
    Example:
        $ scitex-stats tests recommend-test data.csv --design independent --no-json
        $ scitex-stats tests recommend-test data.csv --groups pre,post --design paired
    """
    return _run_recommend_test(
        data=data, groups=groups, design=design, scale=scale,
        assume_equal_variance=assume_equal_variance, as_json=as_json,
    )


@tests_group.command("execute-all")
@click.argument("data")
@_GROUPS
@_DESIGN
@_SCALE
@click.option("--primary", default=None, help="Pre-registered primary test id (default: the recommendation).")
@click.option(
    "--alternative",
    type=click.Choice(["two-sided", "greater", "less"]),
    default="two-sided",
    help="Alternative hypothesis (two-group tests).",
)
@click.option("--json/--no-json", "as_json", default=True, help="JSON (default) or readable text.")
def tests_run_all(data, groups, design, scale, primary, alternative, as_json):
    """Run every applicable test: primary + sensitivity analyses (never picks by p-value).

    \b
    Example:
        $ scitex-stats tests execute-all data.csv --design independent --no-json
        $ scitex-stats tests execute-all data.csv --design paired --primary wilcoxon
    """
    return _run_run_all(
        data=data, groups=groups, design=design, scale=scale,
        primary=primary, alternative=alternative, as_json=as_json,
    )


# §1 leaf-noun doctrine (scitex-dev CLI conventions): a leaf named as a bare
# noun reads as a transitive action with its object missing. Both commands
# below shipped as nouns — `applicability` / `run-all` — and the audit fails
# the build on them. They keep their behaviour under verb-first compound
# names; the old spellings stay as hidden Phase-W warn-forward aliases so no
# existing invocation breaks (the audit skips hidden commands, so the alias
# carries no new finding).
deprecated_alias(tests_group, "applicability", target="check-applicability", remove_in="0.3.0")
deprecated_alias(tests_group, "run-all", target="execute-all", remove_in="0.3.0")


# EOF
