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

## Effect-size dispatch

`sst.effect_size(group1, group2, measure="cohens_d", pooled=True)` is a
synchronous Python operation owned by `effect_sizes/_effect_size.py`.
It returns a native dict with group counts, measure, value, interpretation
and applicable normal-approximation 95% interval bounds. It carries no MCP
status/timestamp fields. The MCP `effect_size` operation calls this same core.

Supported measures are `cohens_d`, `hedges_g`, `glass_delta` (group2 is the
control) and `cliffs_delta`. Inputs must be finite one-dimensional groups.
Cohen/Hedges need at least two observations in each group; Glass needs one
in group1 and two in group2; Cliff needs one per group. Cliff has no interval.
Unpooled Cohen/Hedges are not implemented: `pooled=False` raises `ValueError`
in Python and returns `success: false` over MCP. Pooling does not apply to
Glass/Cliff. Unknown measures and unusable/undefined groups also fail explicitly.

For example, `sst.effect_size([1, 2, 3], [4, 5, 6])["value"]` is `-3.0`.
Closed-form, input-contract and native-return controls live in
`tests/scitex_stats/effect_sizes/test__effect_size.py`; MCP and real stdio
controls also exercise unsupported pooling requests.

## Normality dispatch

`sst.normality_test(data, method="shapiro")` is a synchronous operation
owned by `tests/normality/_normality_test.py`, also used by MCP.
Methods are `shapiro`, `dagostino`, `anderson`, and `lilliefors`.
NaNs are omitted: `n` counts tested observations, `n_input` the original
sample and `n_omitted` excluded values. For `[1, NaN, 2, 3]`, those counts
are 3, 4 and 1. Inputs must be one-dimensional, finite after NaN omission,
and non-constant. Shapiro/Anderson require three usable observations,
D'Agostino eight and Lilliefors four; invalid inputs raise `ValueError`.

The native dict has no transport success/timestamp fields. Shapiro,
D'Agostino and Lilliefors return a statistic, p-value and `is_normal`
heuristic at alpha 0.05. Failure to reject does not prove normality.
Anderson returns `critical_value_5pct` and `normal`, without a p-value.
For `[1, 2, 3]`, Shapiro returns W=1 and p=1.
Owning numerical/count/input/error controls are in
`tests/scitex_stats/tests/normality/test__normality_test.py`; real MCP
error and valid responses are checked by
`tests/integration/test_mcp_describe_stdio.py`.

## P-value correction dispatch

`sst.correct_pvalues(pvalues, method="fdr_bh", alpha=0.05)` is a synchronous
operation owned by `correct/_correct_pvalues.py`, shared with MCP. Inputs
must be a non-empty finite one-dimensional sequence in [0,1]; alpha is a
finite scalar in [0,1]. Invalid inputs raise `ValueError` before either
backend; MCP reports `success: false`. Input arrays are not modified.

Methods are `bonferroni`, `holm`, `fdr_bh`, `fdr_by`, and `sidak`. For
compatibility with the existing operation, unknown names fall back to
`fdr_bh`. `method` retains the requested name and `method_used` identifies
the actual calculation. The dict includes original/adjusted p-values,
rejection flags, significant/test counts and alpha, without transport
success/timestamp fields. The retained NumPy implementation is used when
the Statsmodels calculation raises `ImportError`.

For `[0.01, 0.04, 0.03]`, BH returns `[0.03, 0.04, 0.04]` and rejects all
three at alpha 0.05; BY returns approximately `[0.055, 0.07333, 0.07333]`
and rejects none. Numerical, fallback, invalid-input and input-preservation
controls live in `tests/scitex_stats/correct/test__correct_pvalues.py`.
Existing fallback-versus-Statsmodels comparisons remain in
`tests/integration/test_correction_fallback_reference.py`; real stdio
invalid/valid behavior is checked in `test_mcp_describe_stdio.py` there.

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
# Native result dict (formatted, stars, style, style_used):
sst.format_results("ttest_ind", 2.0, 0.04, style="brief")
# Lower-level line formatting with explicit adjusted/raw p-value fields:
from scitex_stats.auto import format_test_line
format_test_line({"test_name": "ttest_ind", "stat": 2.0, "p_adj": 0.0}, style="plain")
# "t = 2.00, p < 0.001"
sst.correct_pvalues(pvals, method="fdr_bh")
sst.run_posthoc(groups, equal_variances=True)  # only if declared in advance
sst.power.power_ttest(effect_size=0.5, n1=30, n2=30, alpha=0.05)
```

See [quick start](10_quick-start.md) and [workflows](11_workflows.md).

### Legacy line formatter scope

`auto.format_test_line` preserves a supplied `p_adj`, including zero; only
missing/None adjusted values fall back to `p_raw`. It formats supplied
values and does not calculate a correction. This legacy style-preset line
is separate from the structured `run_test(...)["apa"]` renderer described
in [APA reporting](16_apa7-reporting.md). Do not assume it establishes
complete journal/APA-7 compliance. Owning field-precedence, raw/default
and MCP preset-selection checks: `tests/integration/test_formatting_values.py`
and `tests/integration/test_mcp_describe_stdio.py`.

Supplied bounds render `CI [lower, upper]` at the preset's effect precision:

```python
from scitex_stats.auto import format_test_line
format_test_line({"test_name": "ttest_ind", "stat": 2.0, "p_raw": 0.04},
                 effects=[{"name": "d", "value": 0.5,
                           "ci_lower": -0.25, "ci_upper": 1.25}], style="plain")
# "t = 2.00, p = 0.040, d = 0.50, CI [-0.25, 1.25]"
```

Both supplied endpoints and the effect must be finite and ordered
(`ci_lower <= ci_upper`), otherwise `ValueError` is raised. Omitting both
bounds preserves point-only output. No interval or confidence level is calculated or inferred. See [MCP scope](13_mcp-tools.md) for remaining
Science/journal limitations; actual interval controls:
`tests/integration/test_effect_interval_reporting.py`.

### Native power dispatcher

```python
from scitex_stats import power_analysis
result = power_analysis(test_type="anova", effect_size=0.3, n_groups=3)
# result["mode"] == "sample_size_calculation"
# result["required_n_per_group"] is the bounded planning answer
```

The synchronous function is also `scitex_stats.power.power_analysis`.
`ttest`, `anova`, `correlation` and goodness-of-fit `chi2` retain their existing
method policies and parameters; supplying `n` calculates power instead.
The native numerical payload includes `test_type` and `mode`. Errors raise
normally; MCP delegates to this function and adds its success/error envelope
and timestamp. This does not qualify new formulas or general input validation.
See [bounded planning](25_bounded-sample-size.md) for ANOVA/chi-square limits.
Implementation: `power/_power_analysis.py::power_analysis`; method/error/
transport-free controls: `tests/integration/test_native_power_api.py`.
