---
description: |
  [TOPIC] Python API
  [DETAILS] dispatcher, 25 test_* functions, descriptives, effect sizes, helpers.
tags: [scitex-stats-python-api, scitex-stats]
---


# Python API

```python
import scitex_stats as sst
```

## Dispatchers

| Callable | Purpose |
|---|---|
| `sst.run_test(name, *groups, **kw)` | Unified entry — runs any `test_*` by name/alias |
| `sst.recommend_tests(n_groups, sample_sizes, outcome, design, ...)` | Pick suitable tests for a design |
| `sst.describe(data, funcs=None)` | Descriptive statistics for a column / array |
| `sst.available_tests()` | List of all `test_*` names |

`run_test` accepts `return_as ∈ {"dict","dataframe","latex","json"}` (default
`"dict"`). All `test_*` functions decorated with `@supports_return_as` accept
the same kwarg.

## Tabular file input (`data=`)

```python
sst.test_ttest_ind(x="before", y="after", data="measurements.csv")
sst.test_anova(data="groups.tsv", value_col="score", group_col="group")
```

The file separator is estimated (tab / comma / semicolon / pipe / whitespace;
`.tsv` keeps tab). The web UI offers the same Auto estimate plus a hard
Separator choice and a column picker; `resolve_columns(..., sep=";")` and the
MCP `run_test` `sep` parameter specify it programmatically.

## Statistical tests (25 callables)

(25 statistical tests; `test_result_to_stats`, the bundle-I/O helper,
is not counted here.)

```python
sst.test_ttest_1samp(x, popmean=0.0)
sst.test_ttest_ind(group_a, group_b)
sst.test_ttest_rel(paired_a, paired_b)

sst.test_anova(*groups)              # 1-way
sst.test_anova_2way(df, dv, factors)
sst.test_anova_rm(df, dv, within)    # repeated-measures

sst.test_mannwhitneyu(a, b)
sst.test_wilcoxon(a, b)              # paired non-parametric
sst.test_kruskal(*groups)
sst.test_friedman(*groups)
sst.test_brunner_munzel(a, b)

sst.test_pearson(x, y)
sst.test_spearman(x, y)
sst.test_kendall(x, y)
sst.test_theilsen(x, y)              # robust slope

sst.test_chi2(contingency)
sst.test_fisher(contingency_2x2)
sst.test_mcnemar(contingency_2x2)
sst.test_cochran_q(*binary_groups)

sst.test_shapiro(x)
sst.test_normality(x)                # composite
sst.test_ks_1samp(x, cdf)
sst.test_ks_2samp(a, b)

sst.test_kendalls_w(ratings)        # inter-rater agreement
sst.test_icc(ratings)               # intraclass correlation
```

See [20_test-catalog.md](20_test-catalog.md) for the categorized catalog.

## Effect sizes

```python
sst.cohens_d(a, b)
sst.hedges_g(a, b)
sst.glass_delta(a, b)
sst.eta_squared(*groups)
sst.cliffs_delta(a, b)               # non-parametric
```

See [21_effect-sizes.md](21_effect-sizes.md) for interpretation thresholds.

## Helpers

```python
sst.p_to_stars(0.003)        # → "**"
sst.format_results(result)   # publication-style string
sst.correct_pvalues(pvals, method="fdr_bh")
sst.posthoc(*groups, method="tukey")
sst.power_analysis(test="ttest_ind", n=30, effect_size=0.5, alpha=0.05)
```

See [10_quick-start.md](10_quick-start.md) for end-to-end usage and
[11_workflows.md](11_workflows.md) for common patterns.
