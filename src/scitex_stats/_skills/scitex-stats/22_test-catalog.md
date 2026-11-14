---
description: |
  [TOPIC] Test Catalog
  [DETAILS] parametric, nonparametric, correlation, categorical, normality, agreement.
tags: [scitex-stats-test-catalog, scitex-stats]
---


# Test Catalog (25 Tests)

## Parametric (6)

| Function | Use Case |
|----------|----------|
| `test_ttest_ind` | Independent two-sample t-test |
| `test_ttest_rel` | Paired/related samples t-test |
| `test_ttest_1samp` | One-sample t-test vs. population mean |
| `test_anova` | One-way ANOVA (3+ groups) |
| `test_anova_rm` | Repeated-measures ANOVA |
| `test_anova_2way` | Two-way ANOVA |

## Nonparametric (5)

| Function | Use Case |
|----------|----------|
| `test_brunner_munzel` | Two independent samples (no equal variance assumption) |
| `test_wilcoxon` | Paired samples (signed-rank) |
| `test_kruskal` | 3+ independent groups (Kruskal-Wallis) |
| `test_mannwhitneyu` | Two independent samples (rank-based) |
| `test_friedman` | 3+ related groups (Friedman) |

## Correlation (4)

| Function | Use Case |
|----------|----------|
| `test_pearson` | Linear correlation (parametric) |
| `test_spearman` | Monotonic correlation (rank-based) |
| `test_kendall` | Ordinal association (Kendall's tau) |
| `test_theilsen` | Robust linear regression (Theil-Sen) |

## Categorical (4)

| Function | Use Case |
|----------|----------|
| `test_chi2` | Chi-squared test of independence |
| `test_fisher` | Fisher's exact test (small samples) |
| `test_mcnemar` | McNemar's test (paired categorical) |
| `test_cochran_q` | Cochran's Q test (3+ related binary) |

## Normality (4)

| Function | Use Case |
|----------|----------|
| `test_shapiro` | Shapiro-Wilk normality test |
| `test_normality` | Combined normality assessment |
| `test_ks_1samp` | Kolmogorov-Smirnov (one-sample) |
| `test_ks_2samp` | Kolmogorov-Smirnov (two-sample) |

## Agreement (2)

| Function | Use Case |
|----------|----------|
| `test_kendalls_w` | Inter-rater agreement (Kendall's W) |
| `test_icc` | Intraclass correlation (rater reliability) |

## Dispatcher Coverage

Native `available_tests()` lists 23 accepted selector strings, including five
aliases. MCP `run_test(test_name=...)` has 23 canonical selectors and accepts
the same five aliases. These are test selectors, not separate MCP tools;
discovery alone does not verify every route or study design.

The native named dispatcher does not route `anova_rm`, `anova_2way`,
`theilsen`, `mcnemar`, `cochran_q`, `kendalls_w`, `icc`, or `normality`.
Call their native functions directly, for example `sst.test_theilsen(x, y)`.
The MCP selector registry does not include `kendalls_w` or `icc`. Remaining
dispatcher parity and broader test/design behavior are unfinished work.

The legacy MCP `theilsen` selector delegates to native `test_theilsen` and
returns a regression estimate: slope, intercept and a fixed 95% slope
interval (`low_slope`, `high_slope`). It returns no p-value, significance or
placeholder test statistic. Only the default `alternative="two-sided"` is
accepted; one-sided inference is not implemented. This interval is for the
slope, not the intercept or predicted observations. The native estimator and
this MCP adapter are checked against SciPy, paired missing-data handling,
actual worker calls, CSV input, receipt replay and real stdio in
`tests/integration/test_theilsen_mcp.py`.

## Dispatcher Aliases

The `run_test()` dispatcher accepts aliases:

| Alias | Maps to |
|-------|---------|
| `"ttest"` | `test_ttest_ind` |
| `"ttest_ind"` | `test_ttest_ind` |
| `"ttest_paired"` | `test_ttest_rel` |
| `"mann_whitney"` | `test_mannwhitneyu` |
| `"brunnermunzel"` | `test_brunner_munzel` |
