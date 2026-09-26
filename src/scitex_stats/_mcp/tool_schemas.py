#!/usr/bin/env python3
# Timestamp: 2026-01-08
# File: src/scitex/stats/_mcp.tool_schemas.py
# ----------------------------------------

"""Tool schemas for the scitex-stats MCP server."""

from __future__ import annotations

import mcp.types as types

__all__ = ["get_tool_schemas"]


def get_tool_schemas() -> list[types.Tool]:
    """Return all tool schemas for the Stats MCP server."""
    from ._report_schema import report_tool_schema

    return [report_tool_schema(),
        # Test Recommendation
        types.Tool(
            name="recommend_tests",
            description=(
                "Recommend the right statistical test given data characteristics — "
                "acts as an expert statistician. Use when the user asks 'which test "
                "should I use?', 't-test or Mann-Whitney?', 'parametric or "
                "non-parametric?', 'how do I compare these groups?', or is unsure "
                "between ANOVA, Kruskal-Wallis, chi-square, etc. Takes n_groups, "
                "sample sizes, outcome type (continuous/ordinal/categorical/binary), "
                "design (between/within/mixed), and paired flag; returns a ranked "
                "list with rationale for each recommendation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "n_groups": {
                        "type": "integer",
                        "description": "Number of groups to compare",
                        "default": 2,
                    },
                    "sample_sizes": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Sample sizes for each group",
                    },
                    "outcome_type": {
                        "type": "string",
                        "description": "Type of outcome variable",
                        "enum": ["continuous", "ordinal", "categorical", "binary"],
                        "default": "continuous",
                    },
                    "design": {
                        "type": "string",
                        "description": "Study design",
                        "enum": ["between", "within", "mixed"],
                        "default": "between",
                    },
                    "paired": {
                        "type": "boolean",
                        "description": "Whether data is paired/matched",
                        "default": False,
                    },
                    "has_control_group": {
                        "type": "boolean",
                        "description": "Whether there is a control group",
                        "default": False,
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of recommendations to return",
                        "default": 3,
                    },
                },
            },
        ),
        # Run Statistical Test
        types.Tool(
            name="run_test",
            description=(
                "Run ANY of 23 statistical tests on data — t-test (independent/"
                "paired/one-sample), ANOVA (one-way/repeated-measures/two-way), "
                "Mann-Whitney U, Wilcoxon signed-rank, Kruskal-Wallis, Friedman, "
                "Brunner-Munzel, Pearson/Spearman/Kendall/Theil-Sen correlation, "
                "chi-square, Fisher's exact, McNemar, Cochran's Q, Shapiro-Wilk, "
                "Kolmogorov-Smirnov. Drop-in replacement for `scipy.stats.ttest_ind`, "
                "`ttest_rel`, `mannwhitneyu`, `wilcoxon`, `f_oneway`, `kruskal`, "
                "`pearsonr`, `spearmanr`, `chi2_contingency`, `shapiro`, `kstest`, "
                "etc. Use whenever the user asks to 'run a t-test', 'compare two "
                "groups', 'test correlation', 'test normality', 'test independence', "
                "'do an ANOVA'. Accepts raw arrays OR a CSV path + column names. "
                "Returns test statistic, p-value, effect size, and confidence "
                "intervals in one call."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Name of test to run",
                        "enum": [
                            # Parametric (6)
                            "ttest_ind",
                            "ttest_paired",
                            "ttest_1samp",
                            "anova",
                            "anova_rm",
                            "anova_2way",
                            # Nonparametric (5)
                            "brunner_munzel",
                            "mannwhitneyu",
                            "wilcoxon",
                            "kruskal",
                            "friedman",
                            # Correlation (4)
                            "pearson",
                            "spearman",
                            "kendall",
                            "theilsen",
                            # Categorical (4)
                            "chi2",
                            "fisher_exact",
                            "mcnemar",
                            "cochran_q",
                            # Normality (4)
                            "shapiro",
                            "normality",
                            "ks_1samp",
                            "ks_2samp",
                        ],
                    },
                    "data": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "Data arrays for each group (alternative to data_file+columns)",
                    },
                    "data_file": {
                        "type": "string",
                        "description": "Path to CSV file (use with columns instead of data)",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Column names to extract from data_file",
                    },
                    "alternative": {
                        "type": "string",
                        "description": "Alternative hypothesis",
                        "enum": ["two-sided", "less", "greater"],
                        "default": "two-sided",
                    },
                },
                "required": ["test_name"],
            },
        ),
        # Format Results
        types.Tool(
            name="format_results",
            description=(
                "Format a statistical result as a publication-ready string in "
                "APA, Nature, Science, or brief style — e.g. "
                "'t(28) = 2.45, p = .021, d = 0.89, 95% CI [0.12, 1.66]'. "
                "Use whenever the user asks to 'format results for a paper', "
                "'write this up in APA', 'give me the stats sentence', 'format "
                "for Nature', or needs manuscript-ready statistics reporting. "
                "Handles italicization of statistic symbols, correct significant "
                "figures, and per-journal conventions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Name of the statistical test",
                    },
                    "statistic": {
                        "type": "number",
                        "description": "Test statistic value",
                    },
                    "p_value": {
                        "type": "number",
                        "description": "P-value",
                    },
                    "df": {
                        "type": "number",
                        "description": "Degrees of freedom (if applicable)",
                    },
                    "effect_size": {
                        "type": "number",
                        "description": "Effect size value",
                    },
                    "effect_size_name": {
                        "type": "string",
                        "description": "Name of effect size measure (d, r, eta2, etc.)",
                    },
                    "style": {
                        "type": "string",
                        "description": "Journal formatting style",
                        "enum": ["apa", "nature", "science", "brief"],
                        "default": "apa",
                    },
                    "ci_lower": {
                        "type": "number",
                        "description": "Lower bound of confidence interval",
                    },
                    "ci_upper": {
                        "type": "number",
                        "description": "Upper bound of confidence interval",
                    },
                },
                "required": ["test_name", "statistic", "p_value"],
            },
        ),
        # Power Analysis
        types.Tool(
            name="power_analysis",
            description=(
                "Compute statistical power OR required sample size for a planned "
                "study — t-test, ANOVA, correlation, or chi-square. Drop-in "
                "replacement for `statsmodels.stats.power` (TTestIndPower, "
                "FTestAnovaPower, NormalIndPower) and G*Power. Use whenever the "
                "user asks 'how many subjects do I need?', 'what sample size for "
                "effect size d=0.5?', 'what's my power with n=30?', 'do a power "
                "analysis', or is planning an experiment. Pass effect_size + alpha "
                "+ power to get n; pass effect_size + alpha + n to get power."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "test_type": {
                        "type": "string",
                        "description": "Type of statistical test",
                        "enum": ["ttest", "anova", "correlation", "chi2"],
                        "default": "ttest",
                    },
                    "effect_size": {
                        "type": "number",
                        "description": "Expected effect size (Cohen's d, f, r, w)",
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Significance level",
                        "default": 0.05,
                    },
                    "power": {
                        "type": "number",
                        "description": "Desired statistical power (for sample size calculation)",
                        "default": 0.8,
                    },
                    "n": {
                        "type": "integer",
                        "description": "Sample size (for power calculation)",
                    },
                    "n_groups": {
                        "type": "integer",
                        "description": "Number of groups (for ANOVA)",
                        "default": 2,
                    },
                    "ratio": {
                        "type": "number",
                        "description": "Ratio of group sizes (n2/n1)",
                        "default": 1.0,
                    },
                },
            },
        ),
        # Correct P-values
        types.Tool(
            name="correct_pvalues",
            description=(
                "Adjust a list of p-values for multiple comparisons — Bonferroni, "
                "FDR (Benjamini-Hochberg / Benjamini-Yekutieli), Holm, or Sidak. "
                "Drop-in replacement for `statsmodels.stats.multitest.multipletests`. "
                "Use whenever the user asks to 'correct for multiple comparisons', "
                "'apply Bonferroni', 'FDR-correct these p-values', 'Benjamini-"
                "Hochberg', 'control family-wise error rate', or has run many "
                "tests and needs adjusted p-values. Returns adjusted p-values and "
                "a reject/accept mask at the specified alpha."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pvalues": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of p-values to correct",
                    },
                    "method": {
                        "type": "string",
                        "description": "Correction method",
                        "enum": ["bonferroni", "fdr_bh", "fdr_by", "holm", "sidak"],
                        "default": "fdr_bh",
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Family-wise error rate",
                        "default": 0.05,
                    },
                },
                "required": ["pvalues"],
            },
        ),
        # Descriptive Statistics
        types.Tool(
            name="describe",
            description=(
                "Compute descriptive statistics on a data array — n, mean, std, "
                "min/max, median, quartiles (or custom percentiles), skewness, "
                "kurtosis. Drop-in replacement for `pandas.Series.describe()`, "
                "`numpy.mean/std/percentile`, `scipy.stats.describe`. Use whenever "
                "the user asks to 'summarize this data', 'describe the "
                "distribution', 'get mean and std', 'compute quartiles', 'check "
                "skewness/kurtosis', or wants a one-glance numeric summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Data array to describe",
                    },
                    "percentiles": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Percentiles to calculate (0-100)",
                        "default": [25, 50, 75],
                    },
                },
                "required": ["data"],
            },
        ),
        # Effect Size Calculation
        types.Tool(
            name="effect_size",
            description=(
                "Compute standardized effect size between two groups — Cohen's d, "
                "Hedges' g (small-sample corrected), Glass's delta, or Cliff's "
                "delta (non-parametric). Drop-in replacement for `pingouin."
                "compute_effsize` and manual Cohen's d calculations. Use whenever "
                "the user asks 'what's the effect size?', 'compute Cohen's d', "
                "'how big is the difference?', 'is this clinically meaningful?', "
                "or needs to report effect size alongside a p-value. A p-value "
                "alone is incomplete — reviewers ask for effect sizes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First group data",
                    },
                    "group2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second group data",
                    },
                    "measure": {
                        "type": "string",
                        "description": "Effect size measure",
                        "enum": ["cohens_d", "hedges_g", "glass_delta", "cliffs_delta"],
                        "default": "cohens_d",
                    },
                    "pooled": {
                        "type": "boolean",
                        "description": "Use pooled standard deviation",
                        "default": True,
                    },
                },
                "required": ["group1", "group2"],
            },
        ),
        # Normality Test
        types.Tool(
            name="normality_test",
            description=(
                "Test whether data follows a normal (Gaussian) distribution — "
                "Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling, or Lilliefors. "
                "Drop-in replacement for `scipy.stats.shapiro`, `normaltest`, "
                "`anderson`, and `statsmodels.stats.diagnostic.lilliefors`. Use "
                "whenever the user asks 'is this data normal?', 'test normality', "
                "'Shapiro-Wilk', 'check Gaussian assumption', 'should I use "
                "parametric or non-parametric?', or before running a t-test/ANOVA "
                "that assumes normality. Returns test statistic and p-value; p<0.05 "
                "rejects normality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Data to test for normality",
                    },
                    "method": {
                        "type": "string",
                        "description": "Normality test method",
                        "enum": ["shapiro", "dagostino", "anderson", "lilliefors"],
                        "default": "shapiro",
                    },
                },
                "required": ["data"],
            },
        ),
        # Post-hoc Tests
        types.Tool(
            name="posthoc_test",
            description=(
                "Run pairwise post-hoc comparisons after a significant ANOVA or "
                "Kruskal-Wallis — Tukey HSD, Dunnett (vs control), Games-Howell "
                "(unequal variances), or Dunn (non-parametric). Drop-in "
                "replacement for `scikit_posthocs.posthoc_*`, "
                "`statsmodels.stats.multicomp.pairwise_tukeyhsd`, and manual "
                "Bonferroni-corrected t-tests. Use whenever the user asks 'which "
                "groups differ?', 'run Tukey HSD', 'compare to control (Dunnett)', "
                "'follow-up after ANOVA', 'pairwise comparisons', or has a "
                "significant omnibus test and needs to localize the differences."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "groups": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "Data arrays for each group",
                    },
                    "group_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names for each group",
                    },
                    "method": {
                        "type": "string",
                        "description": "Post-hoc method",
                        "enum": ["tukey", "dunnett", "games_howell", "dunn"],
                        "default": "tukey",
                    },
                    "control_group": {
                        "type": "integer",
                        "description": "Index of control group (for Dunnett)",
                        "default": 0,
                    },
                },
                "required": ["groups"],
            },
        ),
        # P-value to Stars
        types.Tool(
            name="p_to_stars",
            description=(
                "Convert a p-value to significance stars (ns / * / ** / ***) for "
                "figure annotations and tables. Use whenever the user asks to "
                "'annotate significance on a plot', 'add stars to boxplot', "
                "'convert p to stars', 'mark significant comparisons', or needs "
                "the conventional journal notation (p<0.05 → *, p<0.01 → **, "
                "p<0.001 → ***). Customizable thresholds."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "p_value": {
                        "type": "number",
                        "description": "P-value to convert",
                    },
                    "thresholds": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Significance thresholds",
                        "default": [0.001, 0.01, 0.05],
                    },
                },
                "required": ["p_value"],
            },
        ),
        # Verify a result against its provenance receipt
        types.Tool(
            name="verify_result",
            description=(
                "Check that a scitex-stats result is exactly what scitex-stats "
                "computes: its provenance receipt is intact, the statistics were "
                "not edited, the data hashes to the recorded SHA-256, and a "
                "recompute is bit-identical. Use before reporting any number from "
                "run_test, or to audit a saved result JSON."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "object",
                        "description": "Result dict carrying 'provenance' (e.g. run_test output)",
                    },
                    "result_file": {
                        "type": "string",
                        "description": "Path to a saved result JSON (instead of 'result')",
                    },
                    "data": {
                        "type": "array",
                        "description": (
                            "Data the result was computed from; for an MCP run_test "
                            "result the same list of arrays passed to run_test. "
                            "Omit to use the copy embedded in the receipt."
                        ),
                    },
                    "data2": {"type": "array", "items": {"type": "number"}},
                    "groups": {"type": "array", "items": {"type": "array"}},
                },
            },
        ),
    ]


# EOF
