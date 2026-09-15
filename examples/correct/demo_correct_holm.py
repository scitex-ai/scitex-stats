#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: examples/correct/demo_correct_holm.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for Holm-Bonferroni correction.

Run with: python examples/correct/demo_correct_holm.py
"""

"""Imports"""
import argparse

import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger
from scitex_stats.correct._correct_bonferroni import correct_bonferroni
from scitex_stats.correct._correct_holm import correct_holm
from scitex_stats.tests.parametric._test_anova import test_anova
from scitex_stats.tests.parametric._test_ttest import test_ttest_ind

logger = getLogger(__name__)


def main(args):
    """Demonstrate Holm correction functionality."""
    logger.info("Demonstrating Holm-Bonferroni correction")

    # Example 1: Basic usage with multiple tests
    logger.info("\n=== Example 1: Basic usage ===")
    results = [
        {"test_method": "Test 1", "pvalue": 0.001},
        {"test_method": "Test 2", "pvalue": 0.040},
        {"test_method": "Test 3", "pvalue": 0.030},
        {"test_method": "Test 4", "pvalue": 0.015},
        {"test_method": "Test 5", "pvalue": 0.060},
    ]
    correct_holm(results, alpha=0.05, verbose=args.verbose)

    # Example 2: Comparison with Bonferroni
    logger.info("\n=== Example 2: Holm vs Bonferroni comparison ===")
    results = [
        {"test_method": "Comparison A", "pvalue": 0.005},
        {"test_method": "Comparison B", "pvalue": 0.015},
        {"test_method": "Comparison C", "pvalue": 0.025},
        {"test_method": "Comparison D", "pvalue": 0.035},
        {"test_method": "Comparison E", "pvalue": 0.045},
    ]
    holm_results = correct_holm(results, alpha=0.05, verbose=args.verbose)
    bonf_results = correct_bonferroni(results, alpha=0.05, verbose=args.verbose)

    holm_rejections = sum(r["rejected"] for r in holm_results)
    bonf_rejections = sum(r["rejected"] for r in bonf_results)
    logger.info(f"Holm rejections: {holm_rejections}/5")
    logger.info(f"Bonferroni rejections: {bonf_rejections}/5")
    logger.info("Note: Holm is uniformly more powerful than Bonferroni")

    # Example 3: Post-hoc after ANOVA
    logger.info("\n=== Example 3: Post-hoc pairwise comparisons after ANOVA ===")
    rng = np.random.default_rng(42)

    group1 = rng.normal(5, 1, 30)
    group2 = rng.normal(7, 1, 30)
    group3 = rng.normal(9, 1, 30)
    groups = [group1, group2, group3]
    names = ["Group A", "Group B", "Group C"]

    anova_result = test_anova(groups, var_names=names)
    logger.info(
        f"Overall ANOVA: F = {anova_result['statistic']:.3f}, "
        f"p = {anova_result['pvalue']:.4f}"
    )

    holm_corrected = None
    if anova_result["significant"]:
        logger.info("Performing pairwise t-tests with Holm correction")
        pairwise_results = []
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                result = test_ttest_ind(
                    groups[i], groups[j], var_x=names[i], var_y=names[j]
                )
                pairwise_results.append(result)
        holm_corrected = correct_holm(
            pairwise_results, alpha=0.05, verbose=args.verbose
        )

    # Example 4: DataFrame input/output
    logger.info("\n=== Example 4: DataFrame input/output ===")
    df_input = pd.DataFrame(
        [
            {"comparison": "A vs B", "pvalue": 0.001, "effect_size": 0.8},
            {"comparison": "A vs C", "pvalue": 0.020, "effect_size": 0.5},
            {"comparison": "A vs D", "pvalue": 0.030, "effect_size": 0.4},
            {"comparison": "B vs C", "pvalue": 0.015, "effect_size": 0.6},
            {"comparison": "B vs D", "pvalue": 0.040, "effect_size": 0.3},
            {"comparison": "C vs D", "pvalue": 0.050, "effect_size": 0.2},
        ]
    )
    df_corrected = correct_holm(df_input, alpha=0.05, verbose=args.verbose)
    if args.verbose:
        logger.info("\nCorrected DataFrame:")
        logger.info(
            df_corrected[
                ["comparison", "pvalue", "pvalue_adjusted", "rejected"]
            ].to_string(index=False)  # type: ignore[index]
        )

    # Example 5: Edge cases
    logger.info("\n=== Example 5: Edge cases ===")
    single = [{"test_method": "Single test", "pvalue": 0.04}]
    single_corr = correct_holm(single, alpha=0.05, verbose=False)
    logger.info(
        f"Single test: p = 0.04 → p_adj = {single_corr[0]['pvalue_adjusted']:.4f}"
    )

    small_ps = [
        {"test_method": f"Test {i}", "pvalue": 0.0001 * (i + 1)} for i in range(5)
    ]
    small_corr = correct_holm(small_ps, alpha=0.05, verbose=False)
    rejections = sum(r["rejected"] for r in small_corr)
    logger.info(f"All small p-values: {rejections}/5 rejected")

    large_ps = [{"test_method": f"Test {i}", "pvalue": 0.1 + 0.1 * i} for i in range(5)]
    large_corr = correct_holm(large_ps, alpha=0.05, verbose=False)
    rejections = sum(r["rejected"] for r in large_corr)
    logger.info(f"All large p-values: {rejections}/5 rejected")

    # Example 6: Export corrected results
    logger.info("\n=== Example 6: Export corrected results ===")
    if holm_corrected is not None:
        pd.DataFrame(holm_corrected).to_csv("./holm_corrected.csv", index=False)

    # Example 7: Power comparison with different α levels
    logger.info("\n=== Example 7: Different alpha levels ===")
    results = [
        {"test_method": f"Test {i}", "pvalue": 0.01 * (i + 1)} for i in range(10)
    ]
    for alpha_level in [0.01, 0.05, 0.10]:
        corrected = correct_holm(results, alpha=alpha_level, verbose=False)
        rejections = sum(r["rejected"] for r in corrected)
        logger.info(f"α = {alpha_level:.2f}: {rejections}/10 tests rejected")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Demonstrate Holm correction")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()


def run_main():
    """Run main without the scitex umbrella session helpers."""
    import matplotlib

    matplotlib.use("Agg")

    args = parse_args()
    return main(args)


if __name__ == "__main__":
    run_main()

# EOF
