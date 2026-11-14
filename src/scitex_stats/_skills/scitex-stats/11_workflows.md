---
description: |
  [TOPIC] Workflows
  [DETAILS] group comparisons, correlations, normality, post-hoc, power.
tags: [scitex-stats-workflows, scitex-stats]
---


# Common Workflows

## "Compare two groups"

```python
import scitex_stats as ss

# Auto-recommend the right test
recs = ss.recommend_tests(group1, group2)
# Uses normality check, sample size, paired/independent to suggest

# Then run it
result = ss.run_test("ttest_ind", group1, group2)
# result = {statistic, p_value, effect_size, ci, power, n1, n2, ...}
```

## "Compare multiple groups"

Pass the groups as one list. The post-hoc workflow runs comparisons only
after a significant omnibus result by default.

```python
import scitex_stats as ss
from scitex_stats.posthoc import run_posthoc

groups = [
    [1.0, 2.0, 3.0, 4.0],
    [5.0, 6.0, 7.0, 8.0],
    [9.0, 10.0, 11.0, 12.0],
]
result = ss.test_anova(groups)
posthoc = run_posthoc(
    groups, omnibus="anova", omnibus_pvalue=result["pvalue"]
)
```

Without an advance declaration of equal variances, this workflow selects
Games–Howell. Use `equal_variances=True` only when the study design declares
that assumption in advance; it selects Tukey HSD. The reported Brown–Forsythe
test is diagnostic and does not make that declaration.

The owning operations are `scitex_stats.posthoc.select_posthoc` and
`run_posthoc`. Behavioral controls:
`tests/scitex_stats/posthoc/test__auto.py`, including
`test_anova_without_a_declaration_stays_games_howell_even_when_groups_look_homogeneous`
and `test_anova_with_a_declaration_in_advance_uses_tukey`.

## "Check correlation"

```python
result = ss.test_pearson(x, y)    # parametric
result = ss.test_spearman(x, y)   # nonparametric
result = ss.test_kendall(x, y)    # ordinal
```

## "Correct for multiple comparisons"

```python
from scitex_stats.correct import bonferroni, fdr, holm

p_values = [0.01, 0.04, 0.03, 0.08]
corrected = fdr(p_values)             # Benjamini-Hochberg
corrected = bonferroni(p_values)      # Bonferroni
corrected = holm(p_values)            # Holm-Bonferroni
```

## "Check normality before choosing test"

```python
result = ss.test_shapiro(data)
result = ss.test_normality(data)   # combined normality check
result = ss.test_ks_1samp(data)    # Kolmogorov-Smirnov
```

## "Calculate power / sample size"

```python
from scitex_stats.power import power_analysis

result = power_analysis(
    test="ttest_ind",
    effect_size=0.5,    # Cohen's d
    alpha=0.05,
    power=0.8,
)
# result.n_per_group → required sample size
```

## "Format results for publication"

```python
result = ss.run_test("ttest_ind", g1, g2, return_as="latex")
# → "t(28) = 2.45, p = .021, d = 0.89"
```
