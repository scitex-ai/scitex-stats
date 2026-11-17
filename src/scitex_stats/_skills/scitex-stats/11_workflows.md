---
description: |
  [TOPIC] Workflows
  [DETAILS] design context, group comparisons, correlations, normality, post-hoc, power.
tags: [scitex-stats-workflows, scitex-stats]
---

# Common Workflows

Each example uses synthetic data and can run independently. Choose the analysis
from the study design and declared assumptions; a recommendation is not a
substitute for specifying the scientific question.

## "Compare two groups"

`recommend_tests` takes a `StatContext`, not two data arrays. It returns test
names. This example runs a separately specified independent-samples test.

```python
from scitex_stats import run_test
from scitex_stats.auto import StatContext, recommend_tests

x, y = [1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15]
context = StatContext(
    n_groups=2, sample_sizes=[len(x), len(y)],
    outcome_type="continuous", design="between", paired=False,
)
recommendations = recommend_tests(context)
result = run_test("ttest_ind", x, y, equal_var=False)
# Dict fields include statistic, pvalue, formatted and provenance.
```

Owning sources: `auto/_context.py`, `auto/_selector.py`, `_dispatch.py`.
Controls: `tests/scitex_stats/auto/test__selector.py`,
`tests/scitex_stats/auto/test__context.py` and
`tests/integration/test_owned_dispatcher.py`.

## "Compare multiple groups"

Pass a list of groups. `run_posthoc` computes the omnibus result when its p-value
is omitted and, by default, runs comparisons only when it is significant.
For ANOVA, Games–Howell is selected unless equal variances were declared in
advance with `equal_variances=True`; the reported variance check is diagnostic.

```python
from scitex_stats import run_test
from scitex_stats.posthoc import run_posthoc

groups = [[1, 2, 4, 5, 7], [30, 33, 36, 39, 42, 45], [62, 63, 64, 66, 68, 70, 73]]
omnibus = run_test("anova", groups=groups)
posthoc = run_posthoc(groups, omnibus="anova", group_names=["A", "B", "C"])
# Inspect ran, method, omnibus and comparisons; comparisons may be empty.
```

Owning sources: `_dispatch.py`, `posthoc/_auto.py`.
Controls: `tests/scitex_stats/posthoc/test__auto.py`. This example does not
qualify the separate legacy post-hoc implementations or degenerate inputs.

## "Check correlation"

```python
from scitex_stats import test_kendall, test_pearson, test_spearman

x, y = [1, 2, 3, 4, 5, 6], [2, 1, 4, 3, 6, 5]
pearson = test_pearson(x, y)
spearman = test_spearman(x, y)
kendall = test_kendall(x, y)
# Each dict contains statistic and pvalue; select the method from the design.
```

Owning source: `tests/correlation/`.
Controls: `tests/scitex_stats/tests/correlation/`.

## "Correct for multiple comparisons"

The correction functions consume result dictionaries with `pvalue` fields,
not a bare list of numbers. Read the adjusted probabilities from
`pvalue_adjusted`. Specify the family and correction in the analysis plan.

```python
from scitex_stats.correct import correct_fdr, correct_holm

results = [{"pvalue": p} for p in [0.01, 0.04, 0.03, 0.08]]
fdr_results = correct_fdr(results, method="bh", verbose=False)
holm_results = correct_holm(results, verbose=False)
fdr_probabilities = [row["pvalue_adjusted"] for row in fdr_results]
holm_probabilities = [row["pvalue_adjusted"] for row in holm_results]
```

Owning sources: `correct/_correct_fdr.py`, `correct/_correct_holm.py`.
Controls: `tests/scitex_stats/correct/`. This example covers adjusted
probabilities, not every correction provider's decision metadata.

## "Inspect a normality diagnostic"

```python
from scitex_stats import test_shapiro

data = [-1.4, -0.9, -0.5, -0.2, 0.1, 0.3, 0.7, 1.0, 1.4, 1.8]
normality = test_shapiro(data)
# Dict with statistic and pvalue; retain the study's planned analysis.
```

Owning source: `tests/normality/_test_shapiro.py`.
Controls: `tests/scitex_stats/tests/normality/test__test_shapiro.py`.

## "Calculate power / sample size"

The two-sample sample-size function returns a pair of integers. Power is a
float; these functions do not return a `n_per_group` attribute.

```python
from scitex_stats.power import power_ttest, sample_size_ttest

n1, n2 = sample_size_ttest(effect_size=0.5, power=0.8, alpha=0.05)
achieved_power = power_ttest(effect_size=0.5, n1=n1, n2=n2, alpha=0.05)
```

Owning source: `power/_power.py`.
Controls: `tests/scitex_stats/power/test__power.py`.

## "Format results for publication"

Use the native result's `formatted` field for its report sentence. Do not
assume `run_test(..., return_as="latex")` produces a sentence: output support
varies by the underlying test. Keep provenance alongside the formatted report.

```python
from scitex_stats import run_test

result = run_test("ttest_ind", [1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15])
report = result["formatted"]
```

Owning sources: `_dispatch.py`, `auto/_format_results.py`.
Controls: `tests/integration/test_formatting_values.py`.
