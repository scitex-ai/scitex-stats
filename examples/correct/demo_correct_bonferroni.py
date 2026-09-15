#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: scitex_stats/correct/_demo_correct_bonferroni.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for Bonferroni correction.

Run with: python -m scitex_stats.correct._demo_correct_bonferroni
"""

"""Imports"""
import argparse

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from scitex_stats._logging import getLogger
from scitex_stats.correct._correct_bonferroni import correct_bonferroni

logger = getLogger(__name__)


def main(args):
    """Demonstrate Bonferroni correction."""
    logger.info("Demonstrating Bonferroni correction")

    # Example 1: Single test
    logger.info("\n=== Example 1: Single test ===")
    single_result = {
        "var_x": "Control",
        "var_y": "Treatment",
        "pvalue": 0.04,
        "alpha": 0.05,
    }
    correct_bonferroni(single_result, verbose=args.verbose)

    # Example 2: Multiple tests
    logger.info("\n=== Example 2: Three pairwise comparisons ===")
    multiple_results = [
        {"var_x": "A", "var_y": "B", "pvalue": 0.01},
        {"var_x": "A", "var_y": "C", "pvalue": 0.03},
        {"var_x": "B", "var_y": "C", "pvalue": 0.05},
    ]
    correct_bonferroni(multiple_results, alpha=0.05, verbose=args.verbose)

    # Example 3: Many tests
    logger.info("\n=== Example 3: Many tests (m=20) ===")
    rng = np.random.default_rng(42)
    many_results = []
    for i in range(20):
        p = rng.uniform(0.001, 0.1)
        many_results.append({"var_x": f"Var_{i}", "var_y": "Control", "pvalue": p})

    corrected_many = correct_bonferroni(many_results, verbose=args.verbose)
    n_rejected_before = sum(r["pvalue"] < 0.05 for r in many_results)
    n_rejected_after = sum(r["rejected"] for r in corrected_many)
    logger.info(f"Tests with p < 0.05 before correction: {n_rejected_before}")
    logger.info(f"Tests rejected after correction:       {n_rejected_after}")

    # Example 4: DataFrame input/output
    logger.info("\n=== Example 4: DataFrame workflow ===")
    df_input = pd.DataFrame(
        {
            "var_x": ["A", "A", "B"],
            "var_y": ["B", "C", "C"],
            "pvalue": [0.002, 0.025, 0.048],
            "effect_size": [0.8, 0.5, 0.3],
        }
    )
    df_corrected = correct_bonferroni(df_input, verbose=args.verbose)
    if args.verbose:
        logger.info("\nAfter correction:")
        logger.info(df_corrected[["var_x", "var_y", "pvalue", "pvalue_adjusted"]])

    # Visualization
    logger.info("\n=== Creating visualization ===")
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Plot 1: Adjusted vs original p-values
    ax = axes[0, 0]
    m_vals = [3, 5, 10, 20]
    p_orig = 0.03
    for m in m_vals:
        p_adj = min(p_orig * m, 1.0)
        ax.scatter(m, p_adj, s=100, label=f"m = {m}")
    ax.axhline(0.05, color="red", linestyle="--", alpha=0.5, label="α = 0.05")
    ax.axhline(p_orig, color="blue", linestyle="--", alpha=0.5, label="Original p")
    ax.set_xlabel("Number of Tests (m)")
    ax.set_ylabel("Adjusted P-value")
    ax.set_title(f"Bonferroni Adjustment (p_original = {p_orig})")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Power loss with increasing tests
    ax = axes[0, 1]
    m_range = np.arange(1, 51)
    alpha = 0.05
    alpha_adj = alpha / m_range
    ax.plot(m_range, alpha_adj, linewidth=2)
    ax.axhline(0.05, color="red", linestyle="--", alpha=0.5, label="Original α")
    ax.set_xlabel("Number of Tests (m)")
    ax.set_ylabel("Adjusted α Threshold")
    ax.set_title("Bonferroni: Threshold Decreases Linearly")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")

    # Plot 3: Before/after comparison
    ax = axes[1, 0]
    rng = np.random.default_rng(42)
    n_tests = 15
    p_values = rng.beta(2, 20, n_tests)
    p_adjusted = np.minimum(p_values * n_tests, 1.0)
    x_pos = np.arange(n_tests)
    width = 0.35
    bars1 = ax.bar(x_pos - width / 2, p_values, width, label="Original", alpha=0.7)
    bars2 = ax.bar(x_pos + width / 2, p_adjusted, width, label="Adjusted", alpha=0.7)
    for i, (p_o, p_a) in enumerate(zip(p_values, p_adjusted)):
        bars1[i].set_color("green" if p_o < 0.05 else "gray")
        bars2[i].set_color("green" if p_a < 0.05 else "gray")
    ax.axhline(0.05, color="red", linestyle="--", alpha=0.5, linewidth=2)
    ax.set_xlabel("Test Index")
    ax.set_ylabel("P-value")
    ax.set_title("Before vs After Bonferroni Correction")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Plot 4: Comparison table
    ax = axes[1, 1]
    ax.axis("off")
    methods_data = [
        ["Method", "Adjusted α\n(m=10)", "Power", "FWER Control"],
        ["None", "0.050", "High", "No"],
        ["Bonferroni", "0.005", "Low", "Strong"],
        ["Holm", "0.005-0.05", "Medium", "Strong"],
        ["FDR", "~0.05", "High", "Weak (FDR)"],
    ]
    table = ax.table(
        cellText=methods_data, cellLoc="center", loc="center", bbox=[0, 0, 1, 1]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for i in range(4):
        table[(0, i)].set_facecolor("#40466e")
        table[(0, i)].set_text_props(weight="bold", color="white")
    for i in range(1, 5):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor("#f0f0f0")
    ax.set_title("Multiple Comparison Methods Comparison", pad=20, fontweight="bold")

    plt.tight_layout()

    fig.savefig("./bonferroni_demo.jpg")
    plt.close(fig)
    logger.info("Visualization saved")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Demonstrate Bonferroni correction")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()


def run_main():
    """Run main without the scitex umbrella session helpers.

    Force the matplotlib Agg backend so the demo runs headlessly in CI.
    """
    import matplotlib

    matplotlib.use("Agg")

    args = parse_args()
    return main(args)


if __name__ == "__main__":
    run_main()

# EOF
