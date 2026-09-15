#!/usr/bin/env python3
# Timestamp: "2025-10-01 17:30:00 (ywatanabe)"
# File: examples/tests/parametric/demo_anova_2way.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for two-way ANOVA examples.

Run with: python examples/tests/parametric/demo_anova_2way.py
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scitex_stats._logging import getLogger
from scitex_stats.tests.parametric._test_anova_2way import test_anova_2way

logger = getLogger(__name__)


def main(args):
    """Run demonstration."""
    logger.info("=" * 70)
    logger.info("Two-way ANOVA Examples")
    logger.info("=" * 70)

    # Ensure ./.dev exists for figure output.
    os.makedirs("./.dev", exist_ok=True)

    # Example 1: Drug × Gender (with interaction)
    logger.info("\n[Example 1] Drug x Gender (interaction present)")
    logger.info("-" * 70)

    rng = np.random.default_rng(42)

    data = pd.DataFrame(
        {
            "Drug": ["Placebo"] * 30 + ["Active"] * 30,
            "Gender": (["Male"] * 15 + ["Female"] * 15) * 2,
            "Score": np.concatenate(
                [
                    rng.normal(50, 10, 15),  # Placebo, Male
                    rng.normal(55, 10, 15),  # Placebo, Female
                    rng.normal(65, 10, 15),  # Active, Male
                    rng.normal(75, 10, 15),  # Active, Female (interaction)
                ]
            ),
        }
    )

    results, _fig = test_anova_2way(
        data,
        factor_a="Drug",
        factor_b="Gender",
        value="Score",
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./.dev/anova_2way_example1.jpg")
    plt.close("all")

    for effect in results:
        logger.info(
            f"{effect['effect']:20s}: F({effect['df_effect']},{effect['df_error']}) = "
            f"{effect['statistic']:.3f}, p = {effect['pvalue']:.4f} {effect['stars']}, "
            f"eta^2p = {effect['effect_size']:.3f}"
        )

    # Example 2: No interaction (additive effects)
    logger.info("\n[Example 2] Temperature x Time (no interaction)")
    logger.info("-" * 70)

    data2 = pd.DataFrame(
        {
            "Temperature": (["Low"] * 20 + ["Medium"] * 20 + ["High"] * 20),
            "Time": (["Short", "Long"] * 30),
            "Yield": np.concatenate(
                [
                    rng.normal(40, 5, 10)
                    + rng.normal(0, 2, 10),  # Low, Short
                    rng.normal(40, 5, 10)
                    + rng.normal(10, 2, 10),  # Low, Long
                    rng.normal(50, 5, 10)
                    + rng.normal(0, 2, 10),  # Medium, Short
                    rng.normal(50, 5, 10)
                    + rng.normal(10, 2, 10),  # Medium, Long
                    rng.normal(60, 5, 10)
                    + rng.normal(0, 2, 10),  # High, Short
                    rng.normal(60, 5, 10)
                    + rng.normal(10, 2, 10),  # High, Long
                ]
            ),
        }
    )

    results2, _fig2 = test_anova_2way(
        data2,
        factor_a="Temperature",
        factor_b="Time",
        value="Yield",
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./.dev/anova_2way_example2.jpg")
    plt.close("all")

    logger.info("\nMain effects should be significant, interaction should not be:")
    for effect in results2:
        logger.info(
            f"{effect['effect']:25s}: p = {effect['pvalue']:.4f} ({effect['effect_size_interpretation']})"
        )

    # Example 3: DataFrame output
    logger.info("\n[Example 3] DataFrame output format")
    logger.info("-" * 70)

    results_df = test_anova_2way(
        data,
        factor_a="Drug",
        factor_b="Gender",
        value="Score",
        return_as="dataframe",
        verbose=True,
    )

    logger.info(
        f"\n{results_df[['effect', 'statistic', 'pvalue', 'effect_size', 'significant']].to_string()}"  # type: ignore[call-overload]
    )

    # Example 4: Export
    logger.info("\n[Example 4] Export results")
    logger.info("-" * 70)

    results_df.to_csv(  # type: ignore[union-attr]
        "./.dev/anova_2way_results.csv", index=False
    )
    logger.info("Saved to: ./.dev/anova_2way_results.csv")

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
