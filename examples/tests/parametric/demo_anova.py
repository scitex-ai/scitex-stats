#!/usr/bin/env python3
# Timestamp: "2025-10-01 16:30:00 (ywatanabe)"
# File: examples/tests/parametric/demo_anova.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Demo script for one-way ANOVA test.

Demonstrates various use cases of test_anova().
"""

"""Imports"""
import argparse  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from scitex_stats._logging import getLogger

logger = getLogger(__name__)

"""Main function"""


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


def main(args):
    """Demonstrate one-way ANOVA functionality."""
    from scitex_stats.correct._correct_bonferroni import correct_bonferroni
    from scitex_stats.tests.parametric._test_anova import test_anova
    from scitex_stats.tests.parametric._test_ttest import test_ttest_ind

    logger.info("Demonstrating one-way ANOVA")

    # Set random seed
    rng = np.random.default_rng(42)

    # Make sure ./.dev exists for outputs.
    os.makedirs("./.dev", exist_ok=True)

    # Example 1: Three groups with clear differences
    logger.info("\n=== Example 1: Three groups with clear differences ===")

    group1 = rng.normal(5, 1, 30)
    group2 = rng.normal(7, 1, 30)
    group3 = rng.normal(9, 1, 30)

    result1 = test_anova(
        [group1, group2, group3],
        var_names=["Group A", "Group B", "Group C"],
        verbose=True,
    )

    logger.info(
        f"F({result1['df_between']}, {result1['df_within']}) = {result1['statistic']:.3f}"
    )
    logger.info(f"p = {result1['pvalue']:.4f} {result1['stars']}")
    logger.info(
        f"eta^2 = {result1['effect_size']:.3f} ({result1['effect_size_interpretation']})"
    )
    logger.info(f"Assumptions met: {result1['assumptions_met']}")
    logger.info(f"Recommendation: {result1['recommendation']}")

    # Example 2: No significant difference
    logger.info("\n=== Example 2: No significant difference ===")

    group1 = rng.normal(5, 1, 30)
    group2 = rng.normal(5.2, 1, 30)
    group3 = rng.normal(4.9, 1, 30)

    result2 = test_anova(
        [group1, group2, group3],
        var_names=["Control", "Treatment 1", "Treatment 2"],
        verbose=True,
    )

    logger.info(
        f"F({result2['df_between']}, {result2['df_within']}) = {result2['statistic']:.3f}"
    )
    logger.info(f"p = {result2['pvalue']:.4f}")
    logger.info(f"Significant: {result2['significant']}")

    # Example 3: With visualization
    logger.info("\n=== Example 3: Complete analysis with visualization ===")

    group1 = rng.normal(10, 2, 25)
    group2 = rng.normal(12, 2, 25)
    group3 = rng.normal(14, 2, 25)
    group4 = rng.normal(16, 2, 25)

    result3 = _safe_call(
        test_anova,
        [group1, group2, group3, group4],
        var_names=["Dose 0", "Dose 1", "Dose 2", "Dose 3"],
        plot=True,
        verbose=True,
    )
    plt.gcf().savefig("./.dev/anova_example3.jpg")
    plt.close("all")

    # Example 4: Assumption violation - unequal variances
    logger.info("\n=== Example 4: Unequal variances ===")

    group1 = rng.normal(5, 1, 30)  # Small variance
    group2 = rng.normal(7, 3, 30)  # Large variance
    group3 = rng.normal(9, 1, 30)  # Small variance

    result4 = test_anova(
        [group1, group2, group3],
        var_names=["Group A", "Group B", "Group C"],
        check_assumptions=True,
        verbose=True,
    )

    logger.info(f"F = {result4['statistic']:.3f}, p = {result4['pvalue']:.4f}")
    logger.info(f"Assumptions met: {result4['assumptions_met']}")
    if "assumption_warnings" in result4:
        for warning in result4["assumption_warnings"]:
            logger.info(f"Warning: {warning}")

    # Example 5: Non-normal data
    logger.info("\n=== Example 5: Non-normal data (exponential) ===")

    group1 = rng.exponential(2, 30)
    group2 = rng.exponential(3, 30)
    group3 = rng.exponential(4, 30)

    result5 = test_anova(
        [group1, group2, group3],
        var_names=["Exp 1", "Exp 2", "Exp 3"],
        check_assumptions=True,
        verbose=True,
    )

    logger.info(f"F = {result5['statistic']:.3f}, p = {result5['pvalue']:.4f}")
    logger.info(f"Assumptions met: {result5['assumptions_met']}")
    logger.info(f"Recommendation: {result5['recommendation']}")

    # Example 6: Post-hoc pairwise comparisons
    logger.info("\n=== Example 6: Post-hoc pairwise comparisons ===")

    # Use data from Example 1 (assumptions met)
    groups = [group1, group2, group3]
    names = ["Group A", "Group B", "Group C"]

    # Perform overall ANOVA
    overall = test_anova(groups, var_names=names, verbose=True)

    if overall["significant"] and overall["assumptions_met"]:
        logger.info(
            "Overall ANOVA significant. Performing post-hoc pairwise t-tests..."
        )

        # Pairwise comparisons
        pairwise_results = []
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                result = test_ttest_ind(
                    groups[i], groups[j], var_x=names[i], var_y=names[j]
                )
                pairwise_results.append(result)
                logger.info(
                    f"{names[i]} vs {names[j]}: "
                    f"t = {result['statistic']:.3f}, "
                    f"p = {result['pvalue']:.4f} {result['stars']}"
                )

        # Apply Bonferroni correction
        corrected = correct_bonferroni(pairwise_results)

        logger.info("\nAfter Bonferroni correction:")
        for res in corrected:
            logger.info(
                f"{res['var_x']} vs {res['var_y']}: "  # type: ignore[index]
                f"p_adjusted = {res['pvalue_adjusted']:.4f}, "  # type: ignore[index]
                f"significant = {res['significant']}"  # type: ignore[index]
            )

    # Example 7: Comparison with Kruskal-Wallis
    logger.info("\n=== Example 7: ANOVA vs Kruskal-Wallis comparison ===")

    from scitex_stats.tests.nonparametric._test_kruskal import test_kruskal

    # Use non-normal data
    groups_exp = [
        rng.exponential(2, 30),
        rng.exponential(3, 30),
        rng.exponential(4, 30),
    ]

    anova_result = test_anova(groups_exp, check_assumptions=False, verbose=True)
    kruskal_result = test_kruskal(groups_exp, verbose=True)

    logger.info(
        f"ANOVA:   F = {anova_result['statistic']:.3f}, p = {anova_result['pvalue']:.4f}"
    )
    logger.info(
        f"Kruskal: H = {kruskal_result['statistic']:.3f}, p = {kruskal_result['pvalue']:.4f}"
    )
    logger.info("Note: Kruskal-Wallis is more appropriate for non-normal data")

    # Example 8: Export results
    logger.info("\n=== Example 8: Export results ===")

    from scitex_stats._utils._normalizers import force_dataframe

    # Collect multiple test results
    test_results = [result1, result2, result3, result4, result5]

    # Export to DataFrame
    df = force_dataframe(test_results)
    logger.info(f"\nDataFrame shape: {df.shape}")

    # Export to CSV via pandas.
    df.to_csv("./.dev/anova_tests.csv", index=False)
    logger.info("Results exported to CSV")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Demonstrate one-way ANOVA")
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
