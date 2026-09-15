#!/usr/bin/env python3
# Timestamp: "2025-10-01 15:30:00 (ywatanabe)"
# File: examples/tests/normality/demo_shapiro.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for Shapiro-Wilk normality test.

Demonstrates various use cases of test_shapiro().
"""

"""Imports"""
import argparse  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from scitex_stats._logging import getLogger

logger = getLogger(__name__)

"""Main function"""


def main(args):
    """Demonstrate Shapiro-Wilk test functionality."""
    from scitex_stats.tests.normality._test_shapiro import test_normality, test_shapiro

    logger.info("Demonstrating Shapiro-Wilk normality test")

    # Set random seed
    rng = np.random.default_rng(42)

    # Example 1: Normal data
    logger.info("\n=== Example 1: Normal data ===")

    x_normal = rng.normal(0, 1, 100)
    _ = test_shapiro(x_normal, var_x="Normal", verbose=True)

    # Example 2: Non-normal data (exponential)
    logger.info("\n=== Example 2: Non-normal data (exponential) ===")

    x_exp = rng.exponential(2, 100)
    _ = test_shapiro(x_exp, var_x="Exponential", verbose=True)

    # Example 3: With Q-Q plot
    logger.info("\n=== Example 3: Visual assessment with Q-Q plot ===")

    x_mixed = np.concatenate(
        [
            rng.normal(0, 1, 90),
            rng.normal(5, 1, 10),  # Outliers
        ]
    )

    _ = test_shapiro(x_mixed, var_x="Mixed Distribution", plot=True, verbose=True)
    plt.gcf().savefig("./shapiro_example3.jpg")
    plt.close("all")

    # Example 4: Multiple samples check
    logger.info("\n=== Example 4: Check multiple samples ===")

    x1 = rng.normal(0, 1, 50)
    x2 = rng.exponential(2, 50)
    x3 = rng.normal(0, 1, 50)

    check_result = test_normality(
        x1, x2, x3, var_names=["Sample A", "Sample B", "Sample C"], warn=True
    )

    logger.info(f"All normal: {check_result['all_normal']}")
    logger.info(f"Recommendation: {check_result['recommendation']}")

    # Example 5: Different distributions comparison
    logger.info("\n=== Example 5: Distribution comparison ===")

    distributions = {
        "Normal": rng.normal(0, 1, 100),
        "Exponential": rng.exponential(2, 100),
        "Uniform": rng.uniform(-3, 3, 100),
        "Gamma": rng.gamma(2, 2, 100),
        "t-dist (df=3)": rng.standard_t(3, 100),
    }

    results_comp = []
    for name, data in distributions.items():
        result = test_shapiro(data, var_x=name, verbose=True)
        results_comp.append(result)

    # Example 6: Export results
    logger.info("\n=== Example 6: Export results ===")

    from scitex_stats._utils._normalizers import export_summary

    export_summary(
        results_comp,
        "./shapiro_results.csv",
        columns=[
            "var_x",
            "statistic",
            "pvalue",
            "stars",
            "normal",
            "recommendation",
        ],
    )
    logger.info("Results exported to ./shapiro_results.csv")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Demonstrate Shapiro-Wilk normality test"
    )
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
