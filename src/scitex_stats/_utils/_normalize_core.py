#!/usr/bin/env python3
# File: scitex_stats/_utils/_normalize_core.py
# ----------------------------------------
"""Normalisation primitives (schemas + dict/DataFrame coercion).

Split out from `_normalizers.py` so the file-size budget stays
honoured. Public symbols are re-exported by `_normalizers.py` for
backward compatibility — existing
`from scitex_stats._utils._normalizers import …` callsites keep
working without changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

# Standard columns for statistical test outputs
STANDARD_COLUMNS = [
    "test_method",
    "statistic_name",
    "statistic",
    "alternative",
    "n_samples",
    "n_x",
    "n_y",
    "n_pairs",
    "var_x",
    "var_y",
    "pvalue",
    "pvalue_adjusted",
    "pstars",
    "alpha",
    "alpha_adjusted",
    "rejected",
    "effect_size",
    "effect_size_metric",
    "effect_size_interpretation",
    "effect_size_secondary",
    "effect_size_secondary_metric",
    "effect_size_secondary_interpretation",
    "power",
    "H0",
]

# Default values for standard columns
STANDARD_DEFAULTS = {
    "alternative": "two-sided",
    "pstars": "ns",
    "rejected": False,
    "alpha": 0.05,
    "alpha_adjusted": np.nan,
    "pvalue_adjusted": np.nan,
    "power": np.nan,
    "n_samples": np.nan,
    "n_x": np.nan,
    "n_y": np.nan,
    "n_pairs": np.nan,
    "var_x": "",
    "var_y": "",
}

# Column types
COLUMN_TYPES = {
    "test_method": str,
    "statistic_name": str,
    "statistic": float,
    "alternative": str,
    "n_samples": "Int64",  # Nullable integer
    "n_x": "Int64",
    "n_y": "Int64",
    "n_pairs": "Int64",
    "var_x": str,
    "var_y": str,
    "pvalue": float,
    "pvalue_adjusted": float,
    "pstars": str,
    "alpha": float,
    "alpha_adjusted": float,
    "rejected": bool,
    "effect_size": float,
    "effect_size_metric": str,
    "effect_size_interpretation": str,
    "effect_size_secondary": float,
    "effect_size_secondary_metric": str,
    "effect_size_secondary_interpretation": str,
    "power": float,
    "H0": str,
}


def normalize_result(
    result: Dict[str, Any], fill_missing: bool = True
) -> Dict[str, Any]:
    """Normalize a result without overwriting caller decisions or stars.

    Adjusted probabilities use family ``alpha`` (default 0.05); raw
    probabilities use ``alpha_adjusted`` when supplied, otherwise family alpha.
    Inferred rejection retains the strict ``<`` comparison.
    """
    normalized = result.copy()

    pvalue_for_decision = normalized.get("pvalue_adjusted", normalized.get("pvalue"))
    alpha_for_decision = normalized.get("alpha", 0.05)
    if "pvalue_adjusted" not in normalized:
        alpha_for_decision = normalized.get("alpha_adjusted", alpha_for_decision)

    if "pstars" not in normalized and pvalue_for_decision is not None:
        from ._formatters import p2stars

        normalized["pstars"] = p2stars(pvalue_for_decision)

    if "rejected" not in normalized and pvalue_for_decision is not None:
        normalized["rejected"] = pvalue_for_decision < alpha_for_decision

    if fill_missing:
        for col, default in STANDARD_DEFAULTS.items():
            if col not in normalized:
                normalized[col] = default

    return normalized


def to_dataframe(
    results: Union[Dict[str, Any], List[Dict[str, Any]]],
    normalize: bool = True,
) -> pd.DataFrame:
    """Convert test result(s) to DataFrame."""
    if isinstance(results, dict):
        results = [results]

    if normalize:
        results = [normalize_result(r) for r in results]

    return pd.DataFrame(results)


def force_dataframe(
    results: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    columns: Optional[List[str]] = None,
    fill_na: bool = True,
    defaults: Optional[Dict[str, Any]] = None,
    enforce_types: bool = True,
) -> pd.DataFrame:
    """Ensure DataFrame output with consistent columns and types."""
    if not isinstance(results, pd.DataFrame):
        df = to_dataframe(results, normalize=True)
    else:
        df = results.copy()

    all_defaults = STANDARD_DEFAULTS.copy()
    if defaults:
        all_defaults.update(defaults)

    if columns:
        for col in columns:
            if col not in df.columns:
                default_val = all_defaults.get(col, np.nan)
                df[col] = default_val

    if fill_na:
        for col, default_val in all_defaults.items():
            if col in df.columns:
                df[col] = df[col].fillna(default_val)

    if enforce_types:
        for col, dtype in COLUMN_TYPES.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except (ValueError, TypeError):
                    pass

    return df


def to_dict(df: pd.DataFrame, row: int = 0) -> Dict[str, Any]:
    """Convert a DataFrame row to a dictionary."""
    return df.iloc[row].to_dict()


def combine_results(
    results_list: List[Union[Dict, pd.DataFrame]], **kwargs
) -> pd.DataFrame:
    """Combine multiple test results into a single DataFrame."""
    dfs = []
    for result in results_list:
        if isinstance(result, dict):
            df = to_dataframe(result)
        elif isinstance(result, pd.DataFrame):
            df = result
        else:
            raise TypeError(f"Expected dict or DataFrame, got {type(result)}")
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    return force_dataframe(combined, **kwargs)


# EOF
