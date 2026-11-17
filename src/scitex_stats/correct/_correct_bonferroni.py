#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-01 20:47:38 (ywatanabe)"
# File: scitex_stats/correct/_correct_bonferroni.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionalities:
  - Apply Bonferroni correction for multiple comparisons
  - Adjust p-values and significance thresholds
  - Support both dict and DataFrame inputs
  - Maintain full result information with adjusted values

Dependencies:
  - packages: numpy, pandas

IO:
  - input: Test results with p-values (dict, list of dicts, or DataFrame)
  - output: Results with adjusted p-values and significance (same format as input)
"""

"""Imports"""
from typing import Any, Dict, List, Optional, Union

import matplotlib
import matplotlib.axes
import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger

logger = getLogger(__name__)

"""Functions"""


def correct_bonferroni(
    results: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    alpha: float = 0.05,
    return_as: str = None,
    verbose: bool = True,
    plot: bool = False,
    ax: Optional[matplotlib.axes.Axes] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]:
    """
    Apply Bonferroni correction for multiple comparisons.

    Parameters
    ----------
    results : dict, list of dict, or DataFrame
        Test results containing 'pvalue' field(s)
        - Single dict: one test result
        - List of dicts: multiple test results
        - DataFrame: multiple test results (one per row)
    alpha : float, default 0.05
        Family-wise error rate (FWER) to control
    return_as : {'dict', 'dataframe', None}, optional
        Force specific return format. If None, matches input format.
    verbose : bool, default True
        Whether to log progress information
    plot : bool, default False
        Whether to generate visualization
    ax : matplotlib.axes.Axes, optional
        Axes object to plot on. If None and plot=True, creates new figure.
        If provided, automatically enables plotting.

    Returns
    -------
    results : dict, list of dict, or DataFrame
        Results with added fields:
        - pvalue_adjusted: Bonferroni-adjusted p-value
        - alpha_adjusted: Threshold for comparing unadjusted p-values
        - rejected: Whether adjusted p-value is strictly below the original alpha
        - pstars: Significance stars (using adjusted p-value)

    Notes
    -----
    The Bonferroni correction is the most conservative method for controlling
    the family-wise error rate (FWER) in multiple comparisons.

    Decisions compare adjusted p-values with the original family alpha using
    strict ``<``. A non-missing per-row ``alpha`` overrides the function value.
    ``alpha_adjusted`` remains the threshold for unadjusted p-values; comparing
    an adjusted p-value to it would apply the correction twice.

    For m tests with family-wise error rate α:

    .. math::
        p_{adj,i} = \\min(m \\cdot p_i, 1.0)

    .. math::
        \\alpha_{adj} = \\frac{\\alpha}{m}

    The method guarantees:

    .. math::
        P(\\text{at least one false positive}) \\leq \\alpha

    **Advantages:**
    - Simple and intuitive
    - Strong FWER control
    - No assumptions about test dependencies

    **Disadvantages:**
    - Very conservative (low statistical power)
    - Power decreases linearly with number of tests
    - May miss true effects (Type II errors)

    **When to use:**
    - Small number of planned comparisons (m < 10)
    - Need strict control of false positives
    - Tests are independent or positively correlated

    References
    ----------
    .. [1] Bonferroni, C. E. (1936). "Teoria statistica delle classi e calcolo
           delle probabilità". Pubblicazioni del R Istituto Superiore di
           Scienze Economiche e Commerciali di Firenze, 8, 3-62.
    .. [2] Dunn, O. J. (1961). "Multiple Comparisons Among Means". Journal of
           the American Statistical Association, 56(293), 52-64.

    Examples
    --------
    >>> # Single test (no correction needed)
    >>> result = {'pvalue': 0.04, 'var_x': 'A', 'var_y': 'B'}
    >>> corrected = correct_bonferroni(result)
    >>> corrected['pvalue_adjusted']
    0.04

    >>> # Multiple tests
    >>> results = [
    ...     {'pvalue': 0.01, 'var_x': 'A', 'var_y': 'B'},
    ...     {'pvalue': 0.03, 'var_x': 'A', 'var_y': 'C'},
    ...     {'pvalue': 0.05, 'var_x': 'B', 'var_y': 'C'}
    ... ]
    >>> corrected = correct_bonferroni(results)
    >>> [r['pvalue_adjusted'] for r in corrected]
    [0.03, 0.09, 0.15]

    >>> # DataFrame input
    >>> df = pd.DataFrame({'pvalue': [0.01, 0.03, 0.05]})
    >>> df_corrected = correct_bonferroni(df)
    >>> df_corrected['alpha_adjusted'].iloc[0]
    0.0166...
    """
    from scitex_stats._utils._formatters import p2stars
    from scitex_stats._utils._normalizers import force_dataframe, to_dict

    if verbose:
        logger.info("Applying Bonferroni correction")

    # Store original input type
    input_type = type(results)
    is_single_dict = isinstance(results, dict)

    # Convert to DataFrame for processing
    if isinstance(results, dict):
        results_list = [results]
    elif isinstance(results, list):
        results_list = results
    else:  # DataFrame
        results_list = None

    if results_list is not None:
        # Supply the caller alpha before normalization can insert its 0.05 default.
        records = [
            {**row, "alpha": alpha if row.get("alpha") is None else row["alpha"]}
            for row in results_list
        ]
        df = force_dataframe(records, fill_na=False, enforce_types=False)
    else:
        df = results.copy()

    # Number of tests
    m = len(df)
    if verbose:
        logger.info(f"Number of tests: {m}, alpha: {alpha}")

    # Compute adjusted p-values (Bonferroni)
    df["pvalue_adjusted"] = np.minimum(df["pvalue"] * m, 1.0)

    # Compute adjusted alpha threshold
    if "alpha" in df.columns:
        alpha_values = df["alpha"].fillna(alpha)
    else:
        alpha_values = alpha

    df["alpha_adjusted"] = alpha_values / m

    # Adjust the probability or the threshold, never both.
    df["rejected"] = df["pvalue_adjusted"] < alpha_values

    # Update significance stars based on adjusted p-values
    df["pstars"] = df["pvalue_adjusted"].apply(p2stars)

    # Log results summary
    if verbose:
        rejections = df["rejected"].sum()
        logger.info(
            f"Bonferroni correction complete: {rejections}/{m} hypotheses rejected"
        )
        logger.info(f"Adjusted alpha threshold: {alpha / m:.6f}")

        # Log detailed results if not too many tests
        if m <= 10:
            logger.info("\nDetailed results:")
            for idx, row in df.iterrows():
                comparison = ""
                if "var_x" in row and "var_y" in row:
                    comparison = f"{row['var_x']} vs {row['var_y']}: "
                elif "test_method" in row:
                    comparison = f"{row['test_method']}: "
                elif "comparison" in row:
                    comparison = f"{row['comparison']}: "

                logger.info(
                    f"  {comparison}"
                    f"p = {row['pvalue']:.4f} → p_adj = {row['pvalue_adjusted']:.4f} "
                    f"{row['pstars']}, rejected = {row['rejected']}"
                )

    # Auto-enable plotting if ax is provided
    if ax is not None:
        plot = True

    # Generate plot if requested
    if plot:
        if ax is None:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))
        _plot_bonferroni(df, alpha, ax)

    # Determine return format
    if return_as == "dataframe":
        return df
    elif return_as == "dict":
        if is_single_dict:
            return to_dict(df, row=0)
        else:
            return df.to_dict("records")
    else:
        # Match input format
        if input_type == dict:
            return to_dict(df, row=0)
        elif input_type == list:
            return df.to_dict("records")
        else:  # DataFrame
            return df


def _plot_bonferroni(df, alpha, ax):
    """Create visualization for Bonferroni correction on given axes."""
    m = len(df)
    x = np.arange(m)

    # Plot original and adjusted p-values
    ax.scatter(x, df["pvalue"], label="Original p-values", alpha=0.7, s=100, color="C0")
    ax.scatter(
        x,
        df["pvalue_adjusted"],
        label="Adjusted p-values",
        alpha=0.7,
        s=100,
        color="C1",
        marker="s",
    )

    # Connect original to adjusted with lines
    for i in range(m):
        ax.plot(
            [i, i],
            [df["pvalue"].iloc[i], df["pvalue_adjusted"].iloc[i]],
            "k-",
            alpha=0.3,
            linewidth=0.5,
        )

    # Add significance thresholds
    ax.axhline(
        alpha,
        color="red",
        linestyle="--",
        linewidth=2,
        alpha=0.5,
        label=f"α = {alpha}",
    )
    ax.axhline(
        alpha / m,
        color="orange",
        linestyle="--",
        linewidth=2,
        alpha=0.5,
        label=f"α_adj = {alpha / m:.4f}",
    )

    # Formatting
    ax.set_xlabel("Test Index")
    ax.set_ylabel("P-value")
    ax.set_title(
        f"Bonferroni Correction (m={m} tests)\n"
        f"{df['rejected'].sum()}/{m} hypotheses rejected"
    )
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Set x-axis labels if there are comparison names
    if m <= 20:
        labels = []
        for idx, row in df.iterrows():
            if "var_x" in row and "var_y" in row:
                labels.append(f"{row['var_x']}\nvs\n{row['var_y']}")
            elif "test_method" in row:
                labels.append(row["test_method"])
            elif "comparison" in row:
                labels.append(row["comparison"])
            else:
                labels.append(f"Test {idx + 1}")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    else:
        ax.set_xlabel(f"Test Index (1-{m})")


# Demo lives in _demo_correct_bonferroni.py.

# EOF
