---
description: |
  [TOPIC] Python API
  [DETAILS] dispatcher, 25 test_* functions, descriptives, bootstrap CIs, effect sizes, helpers.
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

## Bootstrap confidence interval of a statistic

Report a median (or mean) with an uncertainty interval without reaching into
private modules or calling `scipy.stats.bootstrap` directly:

```python
res = sst.bootstrap_ci(ratios, statistic="median", confidence=0.95,
                       n_resamples=10_000, method="percentile", seed=42,
                       nan_policy="raise")
res["estimate"], res["ci_lower"], res["ci_upper"]   # point estimate + bounds
res["ci_apa"]                                       # "95% CI [0.80, 1.76]"
```

- `statistic`: `"median"`, `"mean"`, or a callable `f(x)` / `f(x, y)` (with
  `data2=`; `paired=True` resamples pairs together, e.g. a correlation).
- `method`: `"percentile"` (default), `"basic"`, `"bca"`.
- Deterministic: a fresh `numpy.random.default_rng(seed)` per call; global
  NumPy state is untouched. Same seed, same interval.
- Explicit errors, never a silent fallback: fewer than 2 observations,
  constant input, infinite values, and NaNs unless `nan_policy="omit"` (the
  count dropped is returned as `n_nan_omitted`).
- Returns a JSON-native dict (`statistic`, `estimate`, `ci_lower`,
  `ci_upper`, `ci_level`, `method`, `ci_method`, `n`, `n_resamples`, `seed`,
  `nan_policy`, `n_nan_omitted`, `ci_apa`; plus `n2`, `paired` for two
  samples) that saves as-is with `stx.io.save(res, "median_ci.json")`.

`full_report(...)` uses the same function for its bootstrap intervals.

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
