#!/usr/bin/env python3
# Timestamp: "2025-10-01 21:47:27 (ywatanabe)"
# File: examples/tests/correlation/demo_pearson.py
# ----------------------------------------
from __future__ import annotations

"""
Demo script for Pearson correlation test.

Demonstrates various use cases of test_pearson().
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np

from scitex_stats._logging import getLogger

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

logger = getLogger(__name__)

"""Main function"""


def main(args) -> int:
    """Demonstrate Pearson correlation functionality."""
    from scitex_stats.tests.correlation._test_pearson import test_pearson

    logger.info("Demonstrating Pearson correlation test")

    # Set random seed
    rng = np.random.default_rng(42)

    # Ensure ./.dev exists for figure output.
    os.makedirs("./.dev", exist_ok=True)

    # Example 1: Strong positive correlation
    logger.info("\n=== Example 1: Strong positive correlation ===")

    x1 = rng.normal(0, 1, 50)
    y1 = 2 * x1 + rng.normal(0, 0.5, 50)  # y ~ 2x with noise

    result1 = test_pearson(x1, y1, var_x="X", var_y="Y", verbose=True)

    # Example 2: Negative correlation
    logger.info("\n=== Example 2: Negative correlation ===")

    x2 = rng.normal(0, 1, 50)
    y2 = -1.5 * x2 + rng.normal(0, 0.8, 50)

    result2 = test_pearson(
        x2, y2, var_x="Temperature", var_y="Ice Cream Sales", verbose=True
    )

    # Example 3: No correlation
    logger.info("\n=== Example 3: No correlation ===")

    x3 = rng.normal(0, 1, 50)
    y3 = rng.normal(0, 1, 50)  # Independent

    result3 = test_pearson(x3, y3, var_x="Variable A", var_y="Variable B", verbose=True)

    # Example 4: With visualization
    logger.info("\n=== Example 4: With visualization ===")

    x4 = rng.normal(100, 15, 60)
    y4 = 0.8 * x4 + 20 + rng.normal(0, 10, 60)

    result4 = test_pearson(
        x4,
        y4,
        var_x="Study Hours",
        var_y="Test Score",
        plot=True,
        verbose=True,
    )

    # Save the figure using plt.gcf()
    plt.gcf().savefig("./.dev/pearson_demo.jpg")
    plt.close("all")
    logger.info("Figure saved to ./.dev/pearson_demo.jpg")

    # Example 5: One-sided tests
    logger.info("\n=== Example 5: One-sided tests ===")

    x5 = rng.normal(0, 1, 40)
    y5 = 1.2 * x5 + rng.normal(0, 0.5, 40)

    result_two = test_pearson(x5, y5, alternative="two-sided")
    result_greater = test_pearson(x5, y5, alternative="greater")

    logger.info(f"Two-sided: p = {result_two['pvalue']:.4f}")
    logger.info(f"One-sided (greater): p = {result_greater['pvalue']:.4f}")

    # Example 6: Effect of sample size
    logger.info("\n=== Example 6: Effect of sample size ===")

    # Small sample
    x_small = rng.normal(0, 1, 10)
    y_small = 0.5 * x_small + rng.normal(0, 0.8, 10)

    # Large sample
    x_large = rng.normal(0, 1, 100)
    y_large = 0.5 * x_large + rng.normal(0, 0.8, 100)

    result_small = test_pearson(x_small, y_small)
    result_large = test_pearson(x_large, y_large)

    logger.info(
        f"Small sample (n=10):  r = {result_small['statistic']:.3f}, p = {result_small['pvalue']:.4f}"
    )
    logger.info(
        f"Large sample (n=100): r = {result_large['statistic']:.3f}, p = {result_large['pvalue']:.4f}"
    )
    logger.info("Note: Larger samples provide narrower confidence intervals")

    # Example 7: Effect of outliers
    logger.info("\n=== Example 7: Effect of outliers ===")

    x7 = rng.normal(0, 1, 40)
    y7 = 0.5 * x7 + rng.normal(0, 0.5, 40)

    # Without outliers
    result_clean = test_pearson(x7, y7)

    # With outliers
    x7_outlier = np.append(x7, [5, 5.5])
    y7_outlier = np.append(y7, [-3, -3.5])

    result_outlier = test_pearson(x7_outlier, y7_outlier)

    logger.info(f"Without outliers: r = {result_clean['statistic']:.3f}")
    logger.info(f"With outliers:    r = {result_outlier['statistic']:.3f}")
    logger.info(
        "Note: Pearson correlation is sensitive to outliers. Use Spearman if outliers present."
    )

    # Example 8: Comparison with Spearman
    logger.info("\n=== Example 8: Pearson vs Spearman (non-linear relationship) ===")

    x8 = np.linspace(0, 10, 50)
    y8 = x8**2 + rng.normal(0, 5, 50)  # Quadratic relationship

    pearson_result = test_pearson(x8, y8)

    logger.info(f"Pearson r = {pearson_result['statistic']:.3f}")
    logger.info(
        "Note: For non-linear monotonic relationships, use Spearman correlation"
    )

    # Example 9: Multiple correlations
    logger.info("\n=== Example 9: Multiple correlation analyses ===")

    # Correlation matrix scenario
    data = {
        "Age": rng.normal(40, 10, 50),
        "Income": rng.normal(50000, 15000, 50),
        "Education": rng.normal(16, 3, 50),
    }

    # Income vs Age
    result_ia = test_pearson(data["Income"], data["Age"], var_x="Income", var_y="Age")

    # Income vs Education
    result_ie = test_pearson(
        data["Income"], data["Education"], var_x="Income", var_y="Education"
    )

    # Age vs Education
    result_ae = test_pearson(
        data["Age"], data["Education"], var_x="Age", var_y="Education"
    )

    logger.info(
        f"Income vs Age:       r = {result_ia['statistic']:.3f}, p = {result_ia['pvalue']:.4f}"
    )
    logger.info(
        f"Income vs Education: r = {result_ie['statistic']:.3f}, p = {result_ie['pvalue']:.4f}"
    )
    logger.info(
        f"Age vs Education:    r = {result_ae['statistic']:.3f}, p = {result_ae['pvalue']:.4f}"
    )
    logger.info("Note: For multiple comparisons, apply correction (e.g., Bonferroni)")

    # Example 10: Export results
    logger.info("\n=== Example 10: Export results ===")

    from scitex_stats._utils._normalizers import force_dataframe

    test_results = [
        result1,
        result2,
        result3,
        result4,
        result_small,
        result_large,
    ]

    df = force_dataframe(test_results)
    logger.info(f"\nDataFrame shape: {df.shape}")

    df.to_csv("./pearson_tests.csv", index=False)

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Demonstrate Pearson correlation test")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()


def run_main() -> None:
    """Run main without the scitex umbrella session helpers."""
    import matplotlib

    matplotlib.use("Agg")

    args = parse_args()
    main(args)


if __name__ == "__main__":
    run_main()

# EOF
