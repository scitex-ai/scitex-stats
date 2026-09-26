#!/usr/bin/env python3
# File: src/scitex_stats/_cli/stats.py

"""CLI worker functions for statistical operations (Click-friendly, no argparse).

Wraps the public Python API:
    run_tests_list       - list available test names
    run_tests_execute    - run a named test
    run_tests_describe   - descriptive statistics
    run_tests_recommend  - recommend tests for a study design
    run_format_pvalue    - p-value -> significance stars
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _read_data(path: str) -> "Any":
    """Read CSV / NumPy / JSON file or stdin JSON into numpy/pandas object.

    Supported input formats (auto-detected from extension):
      - .csv  -> pandas.DataFrame (uses pd.read_csv)
      - .tsv  -> pandas.DataFrame (sep='\\t')
      - .npy  -> numpy.ndarray
      - .json -> numpy.ndarray (loads list-of-list as 2D, list as 1D)
      - "-"   -> read JSON from stdin
    """
    import numpy as np

    if path == "-":
        return np.asarray(json.load(sys.stdin))
    if path.endswith(".npy"):
        return np.load(path)
    if path.endswith(".json"):
        with open(path) as f:
            return np.asarray(json.load(f))
    if path.endswith(".csv") or path.endswith(".tsv"):
        import pandas as pd

        sep = "\t" if path.endswith(".tsv") else ","
        return pd.read_csv(path, sep=sep)
    raise ValueError(
        f"Unsupported data format: {path} (use .csv / .tsv / .npy / .json or '-' for stdin JSON)"
    )


def _select_column(df, name: "str | None"):
    """Pick a single column from a DataFrame -> np.ndarray. Pass-through if not DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        return df
    if not isinstance(df, pd.DataFrame):
        return df
    if name is None:
        if df.shape[1] == 1:
            return df.iloc[:, 0].to_numpy()
        raise SystemExit(f"Error: data has {df.shape[1]} columns; specify --x / --y")
    if name not in df.columns:
        raise SystemExit(
            f"Error: column {name!r} not found. Available: {list(df.columns)}"
        )
    return df[name].to_numpy()


def _emit(payload: "dict | list", as_json: bool = True, indent: int = 2):
    """Print payload to stdout. JSON if as_json else readable."""
    if as_json:
        print(json.dumps(payload, indent=indent, default=str))
    else:
        if isinstance(payload, list):
            for item in payload:
                print(item)
        else:
            for k, v in payload.items():
                print(f"  {k:25s} {v}")


def run_tests_list(*, as_json: bool = True) -> int:
    """List available test names to stdout as JSON (default) or plain text. Returns 0."""
    import scitex_stats as ss

    tests = ss.available_tests()
    if as_json:
        print(json.dumps(tests, indent=2))
    else:
        for t in tests:
            print(t)
    return 0


def run_tests_execute(
    *,
    test_name: str,
    data: str,
    x: "str | None" = None,
    y: "str | None" = None,
    groups: "str | None" = None,
    popmean: float = 0.0,
    alternative: str = "two-sided",
    as_json: bool = True,
) -> int:
    """Run a named statistical test and print results.

    Keyword-only arguments:
      test_name   — name of the test to run (see ``available_tests()``)
      data        — path to input file (.csv, .tsv, .npy, .json) or ``"-"`` for stdin JSON
      x           — column name for first variable (DataFrame input), optional
      y           — column name for second variable (DataFrame input), optional
      groups      — comma-separated column names for multi-group (e.g. ``"A,B,C"``);
                    requires CSV/DataFrame input, optional
      popmean     — population mean for one-sample tests (default 0.0)
      alternative — ``"two-sided"`` (default), ``"less"``, or ``"greater"``
      as_json     — print JSON (True, default) or human-readable

    Returns 0 on success, 1 on error.
    """
    import scitex_stats as ss

    df = _read_data(data)
    kwargs: dict[str, Any] = {
        "alternative": alternative,
        "popmean": popmean,
        "json_safe": True,
    }

    if groups:
        cols = [c.strip() for c in groups.split(",")]
        try:
            import pandas as pd

            if isinstance(df, pd.DataFrame):
                kwargs["groups"] = [df[c].to_numpy() for c in cols]
            else:
                raise SystemExit("--groups requires CSV / DataFrame input.")
        except ImportError:
            raise SystemExit("pandas required for --groups")
    elif x and y:
        kwargs["data"] = _select_column(df, x)
        kwargs["data2"] = _select_column(df, y)
    elif x:
        kwargs["data"] = _select_column(df, x)
    else:
        try:
            import pandas as pd

            kwargs["data"] = df.to_numpy() if isinstance(df, pd.DataFrame) else df
        except ImportError:
            kwargs["data"] = df

    try:
        result = ss.run_test(test_name, **kwargs)
    except Exception as e:
        print(
            json.dumps({"error": str(e), "test": test_name}, indent=2),
            file=sys.stderr,
        )
        return 1

    _emit(result, as_json=as_json)
    return 0


def run_tests_describe(
    *,
    data: str,
    column: "str | None" = None,
    funcs: "str | None" = None,
    as_json: bool = True,
) -> int:
    """Compute descriptive statistics for a data file and print results.

    Keyword-only arguments:
      data    — path to input file (.csv, .tsv, .npy, .json) or ``"-"`` for stdin JSON
      column  — column name to analyze (DataFrame input), optional
      funcs   — comma-separated list of statistic function names (e.g. ``"mean,std"``),
                optional; without it all available descriptives are computed
      as_json — print JSON (True, default) or human-readable

    Returns 0 on success.
    """
    import scitex_stats as ss

    arr = _read_data(data)
    try:
        import pandas as pd

        if isinstance(arr, pd.DataFrame) and column:
            arr = arr[column].to_numpy()
        elif hasattr(arr, "to_numpy"):
            arr = arr.to_numpy()
    except ImportError:
        pass

    if funcs:
        values, names = ss.describe(arr, funcs=funcs.split(","))
    else:
        values, names = ss.describe(arr)
    payload = dict(
        zip(names, [v.tolist() if hasattr(v, "tolist") else v for v in values])
    )
    _emit(payload, as_json=as_json)
    return 0


def run_tests_recommend(
    *,
    n_groups: int,
    sample_sizes: str,
    outcome: str = "continuous",
    design: str = "between",
    paired: bool = False,
    top_k: int = 3,
    as_json: bool = True,
) -> int:
    """Recommend statistical tests for a study design and print results.

    Keyword-only arguments:
      n_groups     — number of groups in the study
      sample_sizes — comma-separated sample sizes (e.g. ``"10,12,9"``), one per group
      outcome      — ``"continuous"`` (default), ``"binary"``, or ``"ordinal"``
      design       — ``"between"`` (default) or ``"within"``
      paired       — if True, override design to within-subject
      top_k        — number of recommendations to return (default 3)
      as_json      — print JSON (True, default) or plain text

    Returns 0 on success.
    """
    import scitex_stats as ss

    sizes = [int(s) for s in sample_sizes.split(",")]
    eff_design = "within" if paired else design
    ctx = ss.StatContext(
        n_groups=n_groups,
        sample_sizes=sizes,
        outcome_type=outcome,
        design=eff_design,
        paired=paired,
    )
    tests = ss.recommend_tests(ctx, top_k=top_k)
    if as_json:
        print(json.dumps(tests, indent=2))
    else:
        for t in tests:
            print(t)
    return 0


def run_format_pvalue(*, p: float, style: "str | None" = None) -> int:
    """Convert a p-value to APA significance stars (e.g. ``"***"``) and print to stdout. Returns 0."""
    import scitex_stats as ss

    stars = ss.p_to_stars(p, style=style)
    print(stars)
    return 0


# EOF
