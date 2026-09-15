#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: examples/correct/demo_correct_sidak.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for Šidák correction.

Run with: python examples/correct/demo_correct_sidak.py
"""

"""Imports"""
import argparse

import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger
from scitex_stats.correct._correct_bonferroni import correct_bonferroni
from scitex_stats.correct._correct_holm import correct_holm
from scitex_stats.correct._correct_sidak import correct_sidak
from scitex_stats.tests.parametric import test_ttest_ind

logger = getLogger(__name__)


def main():
    """Comprehensive examples of Šidák correction."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose output",
    )
    args = parser.parse_args([])

    logger.info("=" * 70)
    logger.info("Šidák Correction Examples")
    logger.info("=" * 70)

    # Example 1: Basic usage with 5 independent tests
    logger.info("\n[Example 1] Basic Šidák correction with 5 independent t-tests")
    logger.info("-" * 70)

    rng = np.random.default_rng(42)
    results = []
    for i in range(5):
        x = rng.normal(0, 1, 30)
        y = rng.normal(0.3, 1, 30)
        r = test_ttest_ind(x, y, var_x=f"Group_{i}_A", var_y=f"Group_{i}_B")
        results.append(r)

    corrected = correct_sidak(results, alpha=0.05, verbose=args.verbose)

    # Example 2: Comparison with Bonferroni
    logger.info("\n[Example 2] Šidák vs Bonferroni comparison")
    logger.info("-" * 70)

    bonf = correct_bonferroni(results, alpha=0.05, verbose=False)

    logger.info(f"Number of tests: {len(results)}")
    logger.info(f"Šidák alpha: {corrected[0]['alpha_adjusted']:.6f}")
    logger.info(f"Bonferroni alpha: {bonf[0]['alpha_adjusted']:.6f}")
    logger.info(
        f"Difference: {corrected[0]['alpha_adjusted'] - bonf[0]['alpha_adjusted']:.6f}"
    )

    n_rejected_sidak = sum(r["rejected"] for r in corrected)
    n_rejected_bonf = sum(r["rejected"] for r in bonf)

    logger.info(f"\nŠidák rejections: {n_rejected_sidak}/{len(results)}")
    logger.info(f"Bonferroni rejections: {n_rejected_bonf}/{len(results)}")

    # Example 3: Large number of tests
    logger.info("\n[Example 3] Large number of tests (m=20)")
    logger.info("-" * 70)

    rng = np.random.default_rng(123)
    results_20 = []
    for i in range(20):
        x = rng.normal(0, 1, 50)
        y = rng.normal(0.2, 1, 50)
        r = test_ttest_ind(x, y)
        results_20.append(r)

    corrected_20 = correct_sidak(results_20, alpha=0.05, verbose=False)
    bonf_20 = correct_bonferroni(results_20, alpha=0.05, verbose=False)

    logger.info("With 20 tests:")
    logger.info(f"  Šidák alpha: {corrected_20[0]['alpha_adjusted']:.6f}")
    logger.info(f"  Bonferroni alpha: {bonf_20[0]['alpha_adjusted']:.6f}")
    logger.info(
        f"  Power gain: {(corrected_20[0]['alpha_adjusted'] / bonf_20[0]['alpha_adjusted'] - 1) * 100:.2f}%"
    )

    # Example 4: Comparison with Holm
    logger.info("\n[Example 4] Šidák vs Holm (sequential Bonferroni)")
    logger.info("-" * 70)

    holm = correct_holm(results, alpha=0.05, verbose=False)
    n_rejected_holm = sum(r["rejected"] for r in holm)

    logger.info(f"Number of tests: {len(results)}")
    logger.info(f"Šidák rejections: {n_rejected_sidak}")
    logger.info(f"Holm rejections: {n_rejected_holm}")
    logger.info(f"Bonferroni rejections: {n_rejected_bonf}")
    logger.info(
        "\nNote: Holm is typically more powerful than both Šidák and Bonferroni"
    )

    # Example 5: DataFrame input/output
    logger.info("\n[Example 5] DataFrame input and output")
    logger.info("-" * 70)

    df_input = pd.DataFrame(results)
    df_corrected = correct_sidak(df_input, alpha=0.05, verbose=args.verbose)

    if args.verbose:
        logger.info(f"Input type: {type(df_input)}")
        logger.info(f"Output type: {type(df_corrected)}")
        logger.info("\nCorrected DataFrame (first 3 rows):")
        logger.info(
            df_corrected[  # type: ignore[index]
                ["var_x", "var_y", "pvalue", "pvalue_adjusted", "rejected"]
            ]
            .head(3)
            .to_string()
        )

    # Example 6: Single test
    logger.info("\n[Example 6] Single test (returns dict)")
    logger.info("-" * 70)

    single = correct_sidak(results[0], alpha=0.05, verbose=False)
    logger.info("Input: single dict")
    logger.info(f"Output: {type(single)}")
    logger.info(f"Original p-value: {results[0]['pvalue']:.4f}")
    logger.info(f"Adjusted p-value: {single['pvalue_adjusted']:.4f}")

    # Example 7: Edge cases
    logger.info("\n[Example 7] Edge cases")
    logger.info("-" * 70)

    edge_results = [{"pvalue": 0.001}, {"pvalue": 0.05}, {"pvalue": 0.99}]
    edge_corrected = correct_sidak(edge_results, alpha=0.05, verbose=False)

    for i, (orig, corr) in enumerate(zip(edge_results, edge_corrected)):
        logger.info(
            f"Test {i + 1}: p = {orig['pvalue']:.4f} -> "
            f"p_adj = {corr['pvalue_adjusted']:.4f}"
        )

    # Example 8: Different alpha levels
    logger.info("\n[Example 8] Different alpha levels")
    logger.info("-" * 70)

    for alpha_val in [0.01, 0.05, 0.10]:
        corr = correct_sidak(results, alpha=alpha_val, verbose=False)
        n_rej = sum(r["rejected"] for r in corr)
        logger.info(
            f"Alpha = {alpha_val:.2f}: alpha_adj = {corr[0]['alpha_adjusted']:.4f}, "
            f"rejections = {n_rej}/{len(results)}"
        )

    # Example 9: Export
    logger.info("\n[Example 9] Export corrected results")
    logger.info("-" * 70)
    if hasattr(df_corrected, "to_csv"):
        df_corrected.to_csv("./sidak_corrected.csv", index=False)  # type: ignore[union-attr]

    # Example 10: Mathematical properties
    logger.info("\n[Example 10] Mathematical properties demonstration")
    logger.info("-" * 70)

    m_values = [2, 5, 10, 20, 50, 100]
    alpha = 0.05
    logger.info(f"For alpha = {alpha}:")
    logger.info(f"{'m':<5} {'Bonferroni':<12} {'Šidák':<12} {'Ratio':<8}")
    logger.info("-" * 40)
    for m in m_values:
        bonf_alpha = alpha / m
        sidak_alpha = 1.0 - (1.0 - alpha) ** (1.0 / m)
        ratio = sidak_alpha / bonf_alpha
        logger.info(f"{m:<5} {bonf_alpha:.6f}     {sidak_alpha:.6f}     {ratio:.4f}")

    logger.info("\nNote: Šidák is always ≥ Bonferroni (more powerful)")
    logger.info("Difference increases with larger m")

    return 0


def run_main():
    """Run main without the scitex umbrella session helpers."""
    import matplotlib

    matplotlib.use("Agg")
    return main()


if __name__ == "__main__":
    run_main()

# EOF
