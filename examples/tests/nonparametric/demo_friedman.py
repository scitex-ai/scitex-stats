#!/usr/bin/env python3
# Timestamp: "2025-10-01 22:43:58 (ywatanabe)"
# File: examples/tests/nonparametric/demo_friedman.py

"""
Demo script for Friedman test.

Demonstrates various use cases of test_friedman().
"""

from __future__ import annotations

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)

logger = getLogger(__name__)


def _safe_call(fn, *args, **kwargs):
    """Call ``fn``; on a missing optional plotting dependency, retry with
    plot=False. Keeps the demo runnable when ``figrecipe`` is not installed.
    """
    try:
        return fn(*args, **kwargs)
    except ModuleNotFoundError as exc:
        if "figrecipe" not in str(exc):
            raise
        logger.warning(
            "figrecipe not installed; rerunning %s with plot=False", fn.__name__
        )
        kwargs["plot"] = False
        return fn(*args, **kwargs)


def main(args):  # noqa: C901
    """Demonstrate Friedman test functionality."""
    from scitex_stats.tests.nonparametric._test_friedman import test_friedman

    # Example 1: Pain ratings (ordinal data)
    logger.info("\n[Example 1] Pain ratings across 4 time points (ordinal)")
    logger.info("-" * 70)

    rng = np.random.default_rng(42)
    # Simulate decreasing pain over time
    pain_data = np.array(
        [
            [7, 6, 5, 4],
            [8, 7, 6, 5],
            [6, 5, 4, 3],
            [9, 8, 7, 6],
            [7, 6, 5, 4],
            [8, 7, 6, 5],
            [6, 5, 5, 4],
            [7, 6, 5, 5],
        ]
    )

    result = _safe_call(
        test_friedman,
        pain_data,
        condition_names=["Baseline", "Week 1", "Week 2", "Week 3"],
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./friedman_example1.jpg")
    plt.close("all")

    # Example 2: Likert scale ratings
    logger.info("\n[Example 2] Likert scale ratings (1-5) for 4 products")
    logger.info("-" * 70)

    likert_data = np.array(
        [
            [3, 4, 5, 3],
            [2, 3, 4, 2],
            [4, 5, 5, 4],
            [3, 4, 4, 3],
            [2, 3, 5, 2],
            [3, 4, 4, 3],
            [4, 5, 5, 4],
            [3, 3, 4, 3],
            [2, 4, 5, 3],
            [3, 4, 4, 2],
        ]
    )

    result_likert = _safe_call(
        test_friedman,
        likert_data,
        condition_names=["Product A", "Product B", "Product C", "Product D"],
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./friedman_example2.jpg")
    plt.close("all")

    logger.info(f"chi2({result_likert['df']}) = {result_likert['statistic']:.3f}")
    logger.info(f"p-value = {result_likert['pvalue']:.4f}")
    logger.info(f"Kendall's W = {result_likert['kendall_w']:.3f}")

    # Example 3: Long format DataFrame
    logger.info("\n[Example 3] Long format DataFrame input")
    logger.info("-" * 70)

    subjects = np.repeat(np.arange(8), 4)
    conditions = np.tile(["Pre", "Mid1", "Mid2", "Post"], 8)
    values = rng.integers(1, 11, 32)  # Random scores 1-10

    df_long = pd.DataFrame(
        {"Subject": subjects, "TimePoint": conditions, "Score": values}
    )

    result_long = _safe_call(
        test_friedman,
        df_long,
        subject_col="Subject",
        condition_col="TimePoint",
        value_col="Score",
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./friedman_example3.jpg")
    plt.close("all")

    logger.info(f"chi2 = {result_long['statistic']:.3f}, p = {result_long['pvalue']:.4f}")

    # Example 4: Comparison with RM-ANOVA
    logger.info("\n[Example 4] Comparison: Friedman vs RM-ANOVA")
    logger.info("-" * 70)

    from scitex_stats.tests.parametric import test_anova_rm

    # Data with outliers
    data_outlier = rng.normal(5, 1, (10, 4))
    data_outlier[0, 0] = 20  # Add outlier

    test_friedman(data_outlier, verbose=True)
    result_rm_anova = test_anova_rm(data_outlier, verbose=True)

    logger.info(
        f"RM-ANOVA: F = {result_rm_anova['statistic']:.3f}, p = {result_rm_anova['pvalue']:.4f}"  # type: ignore[call-overload]
    )
    logger.info("Note: Friedman is more robust to outliers")

    # Example 5: Export results
    logger.info("\n[Example 5] Export results")
    logger.info("-" * 70)

    pd.DataFrame([result]).to_csv("./friedman_results.csv", index=False)

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
