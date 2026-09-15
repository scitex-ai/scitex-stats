#!/usr/bin/env python3
# Timestamp: "2025-10-01 18:53:25 (ywatanabe)"
# File: examples/tests/categorical/demo_chi2.py
# ----------------------------------------

"""
Demo script for chi-square test examples.

Run with: python examples/tests/categorical/demo_chi2.py
"""

from __future__ import annotations

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger
from scitex_stats._utils._normalizers import force_dataframe
from scitex_stats.tests.categorical._test_chi2 import test_chi2

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

logger = getLogger(__name__)


def main(args):
    """Run demonstration."""
    logger.info("=" * 70)
    logger.info("Chi-square Test of Independence - Examples")
    logger.info("=" * 70)

    # Example 1: Treatment × Outcome (2×2 table)
    logger.info("\nExample 1: Treatment × Outcome (2×2 table)")
    logger.info("-" * 70)
    observed1 = np.array(
        [
            [30, 10],  # Treatment A: Success, Failure
            [20, 40],  # Treatment B: Success, Failure
        ]
    )
    result1 = test_chi2(
        observed1,
        var_row="Treatment",
        var_col="Outcome",
        plot=True,
        verbose=True,
    )
    logger.info(force_dataframe(result1))

    # Save the figure using plt.gcf()
    plt.gcf().savefig("./example1_treatment_outcome.jpg")
    plt.close("all")

    # Example 2: Education × Income (3×3 table)
    logger.info("\nExample 2: Education × Income level")
    logger.info("-" * 70)
    observed2 = np.array(
        [
            [20, 15, 5],  # High school: Low, Med, High income
            [15, 30, 15],  # Bachelor: Low, Med, High income
            [5, 15, 30],  # Graduate: Low, Med, High income
        ]
    )
    result2 = test_chi2(
        observed2,
        var_row="Education",
        var_col="Income",
        plot=True,
        verbose=True,
    )
    logger.info(force_dataframe(result2))

    plt.gcf().savefig("./example2_education_income.jpg")
    plt.close("all")

    # Example 3: Gender × Product preference
    logger.info("\nExample 3: Gender × Product preference")
    logger.info("-" * 70)
    observed3 = np.array(
        [
            [25, 30, 15],  # Male: Product A, B, C
            [20, 25, 35],  # Female: Product A, B, C
        ]
    )
    result3 = test_chi2(observed3, var_row="Gender", var_col="Product", verbose=True)
    logger.info(force_dataframe(result3))

    # Example 4: Using pandas DataFrame
    print("\nExample 4: Using pandas DataFrame with labels")
    print("-" * 70)
    df4 = pd.DataFrame(
        [[45, 25, 10], [30, 40, 30]],
        index=["Control", "Treatment"],
        columns=["Improved", "Unchanged", "Worse"],
    )
    df4.index.name = "Group"
    df4.columns.name = "Outcome"
    result4 = test_chi2(df4, plot=True)
    print(force_dataframe(result4))
    plt.gcf().savefig("./fig4.jpg")
    plt.close("all")

    # Example 5: Small expected frequencies (warning)
    print("\nExample 5: Small expected frequencies (assumption violation)")
    print("-" * 70)
    observed5 = np.array([[2, 8], [3, 7]])
    result5 = test_chi2(observed5, var_row="Group", var_col="Response", plot=False)
    print(force_dataframe(result5))
    if "warnings" in result5:
        print(f"Warning: {result5['warnings']}")

    # Example 6: No association (null example)
    print("\nExample 6: No association (random data)")
    print("-" * 70)
    rng = np.random.default_rng(42)
    n_samples = 200
    row_probs = [0.5, 0.5]
    col_probs = [0.3, 0.4, 0.3]
    observed6 = rng.multinomial(
        n_samples, [p * q for p in row_probs for q in col_probs]
    ).reshape(2, 3)
    result6 = test_chi2(observed6, var_row="Factor1", var_col="Factor2", plot=True)
    print(force_dataframe(result6))
    plt.gcf().savefig("./example6_no_association.jpg")
    plt.close("all")

    # Example 7: Strong association
    print("\nExample 7: Strong association")
    print("-" * 70)
    observed7 = np.array(
        [
            [50, 5, 5],  # Group A mostly in category 1
            [5, 50, 5],  # Group B mostly in category 2
            [5, 5, 50],  # Group C mostly in category 3
        ]
    )
    result7 = test_chi2(observed7, var_row="Group", var_col="Category", plot=True)
    print(force_dataframe(result7))
    print(f"Very strong association: V = {result7['effect_size']:.3f}")
    plt.gcf().savefig("./example7_strong_association.jpg")
    plt.close("all")

    # Example 8: Yates' correction vs no correction (2×2)
    print("\nExample 8: Yates' correction comparison (2×2 table)")
    print("-" * 70)
    observed8 = np.array([[10, 15], [20, 25]])
    result8_yates = test_chi2(observed8, correction=True, plot=False)
    result8_no = test_chi2(observed8, correction=False, plot=False)
    print("With Yates' correction:")
    print(f"  chi2 = {result8_yates['statistic']:.3f}, p = {result8_yates['pvalue']:.4f}")
    print("Without correction:")
    print(f"  chi2 = {result8_no['statistic']:.3f}, p = {result8_no['pvalue']:.4f}")

    # Example 9: Export to CSV
    print("\nExample 9: Export to CSV")
    print("-" * 70)
    result9 = test_chi2(
        observed3, var_row="Gender", var_col="Product", return_as="dataframe"
    )
    result9.to_csv("chi2_demo.csv", index=False)  # type: ignore[union-attr]
    # stx.io.save(result9, 'chi2_demo.tex') removed -- leaf-rule
    print("Exported to CSV")
    print(result9)

    # Example 10: Large contingency table (4×5)
    print("\nExample 10: Larger contingency table (4×5)")
    print("-" * 70)
    rng = np.random.default_rng(43)
    observed10 = rng.integers(10, 40, size=(4, 5))
    result10 = test_chi2(observed10, var_row="Factor_A", var_col="Factor_B", plot=True)
    print(force_dataframe(result10))
    plt.gcf().savefig("./example10_large_table.jpg")
    plt.close("all")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="")
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
