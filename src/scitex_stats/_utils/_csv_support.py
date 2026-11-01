#!/usr/bin/env python3
"""CSV/DataFrame column resolution for seaborn-style data= parameter."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import pandas as pd

# File candidates are scored by consistent multi-column record widths, not
# punctuation in one header. Structured tabs retain their existing priority;
# equally plausible punctuation requires an explicit override. Whitespace is
# considered only when classic separators do not describe the records.
_SEP_PRIORITY = ("\t", ",", ";", "|")


def detect_separator(text: str, *, filename: str = "") -> str:
    """Estimate the delimiter of a tabular text sample.

    Returns one of ``"\\t"``, ``","``, ``";"``, ``"|"``, or ``" "``
    (whitespace: split on runs of whitespace). Falls back to ``","``.
    A ``.tsv`` filename keeps its tab contract without looking.
    Equally plausible punctuation separators raise ``ValueError``; provide
    an explicit ``sep`` to the file loader in that case.
    """
    if str(filename).lower().endswith(".tsv"):
        return "\t"
    lines = [line for line in str(text).lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        return ","
    candidates = []
    for separator in _SEP_PRIORITY:
        try:
            widths = [
                len(row) for row in csv.reader(lines, delimiter=separator, strict=True)
            ]
        except csv.Error:
            continue
        counts = Counter(width for width in widths if width > 1)
        if counts:
            candidates.append((max(counts.values()), separator))
    if candidates:
        score = max(count for count, _ in candidates)
        winners = [separator for count, separator in candidates if count == score]
        # Preserve the documented structured-tab preference over punctuation.
        if "\t" in winners:
            return "\t"
        if len(winners) > 1:
            raise ValueError("Ambiguous separator; specify sep explicitly.")
        return winners[0]
    # The space dialect collapses runs but respects quoted labels. Keep the
    # existing strict consistency requirement for whitespace-only detection.
    try:
        fields = list(
            csv.reader(lines, delimiter=" ", skipinitialspace=True, strict=True)
        )
    except csv.Error:
        return ","
    if (
        fields
        and len(fields[0]) > 1
        and all(len(row) == len(fields[0]) for row in fields)
    ):
        return " "
    return ","


def _load_file(path: str, sep: str | None = None) -> pd.DataFrame:
    """Load a tabular file as DataFrame.

    Parameters
    ----------
    path : str
        File path. ``.tsv`` keeps its tab contract (same as scitex-io).
    sep : str or None
        Hard separator specification; ``" "`` splits on whitespace runs.
        None (default) estimates via :func:`detect_separator`.
    """
    if sep is None:
        if str(path).lower().endswith(".tsv"):
            sep = "\t"
        else:
            with open(path, encoding="utf-8-sig") as f:
                sep = detect_separator(f.read(65536))
    if sep == " ":
        return pd.read_csv(path, sep=r"\s+", encoding="utf-8-sig")
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig")


def resolve_columns(
    data: Union[pd.DataFrame, str, Path],
    *,
    preserve_rows: bool = False,
    sep: str | None = None,
    **col_map: Any,
) -> Dict[str, np.ndarray]:
    """Resolve string column names from a DataFrame or CSV to arrays.

    Parameters
    ----------
    data : DataFrame, str, or Path
        DataFrame or path to CSV file.
    preserve_rows : bool, default False
        Keep missing values at their original positions so paired callers
        can apply their existing joint mask. The default drops missing
        values independently in each resolved column.
    sep : str or None, default None
        Hard file separator (``" "`` = whitespace runs); None estimates.
    **col_map
        Keyword arguments mapping param names to values.
        String values are treated as column names and resolved.
        Non-string values are passed through unchanged.

    Returns
    -------
    dict
        Resolved arrays keyed by parameter name.

    Raises
    ------
    ValueError
        If a string column name is not found in the DataFrame.

    Examples
    --------
    >>> df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    >>> resolved = resolve_columns(df, x="a", y="b")
    >>> resolved["x"]
    array([1, 2, 3])
    """
    if isinstance(data, (str, Path)):
        data = _load_file(str(data), sep=sep)

    result = {}
    for key, val in col_map.items():
        if isinstance(val, str):
            if val not in data.columns:
                raise ValueError(
                    f"Column '{val}' not found in data. "
                    f"Available columns: {list(data.columns)}"
                )
            column = data[val] if preserve_rows else data[val].dropna()
            result[key] = column.values
        else:
            result[key] = val
    return result


def resolve_groups(
    data: Union[pd.DataFrame, str, Path],
    value_col: str,
    group_col: str,
    *,
    sep: str | None = None,
) -> Tuple[List[np.ndarray], List[str]]:
    """Split a DataFrame into groups by a column.

    Parameters
    ----------
    data : DataFrame, str, or Path
        DataFrame or path to CSV file.
    value_col : str
        Column containing measurement values.
    group_col : str
        Column containing group labels.
    sep : str or None, default None
        Hard file separator (``" "`` = whitespace runs); None estimates.

    Returns
    -------
    groups : list of np.ndarray
        One array per group, NaN values dropped.
    names : list of str
        Group names in sorted order.

    Raises
    ------
    ValueError
        If value_col or group_col is not found in the DataFrame.

    Examples
    --------
    >>> df = pd.DataFrame({"score": [1, 2, 3, 4], "group": ["A", "A", "B", "B"]})
    >>> groups, names = resolve_groups(df, "score", "group")
    >>> names
    ['A', 'B']
    """
    if isinstance(data, (str, Path)):
        data = _load_file(str(data), sep=sep)

    for col_name, col_label in [
        (value_col, "value_col"),
        (group_col, "group_col"),
    ]:
        if col_name not in data.columns:
            raise ValueError(
                f"{col_label} '{col_name}' not found in data. "
                f"Available columns: {list(data.columns)}"
            )

    groups: List[np.ndarray] = []
    names: List[str] = []
    for name, group in data.groupby(group_col):
        groups.append(group[value_col].dropna().values)
        names.append(str(name))
    return groups, names
