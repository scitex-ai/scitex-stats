---
description: |
  [TOPIC] Workflows
  [DETAILS] group comparisons, correlations, normality, post-hoc, power.
tags: [scitex-stats-workflows, scitex-stats]
---


# Common Workflows

Each example defines its own inputs and uses current Python APIs.

## "Compare two groups"

Recommendations use study-design metadata. The result dictionary uses statistic
and pvalue; the selected test determines the remaining fields.

```python
import scitex_stats as ss

group1 = [1.1, 2.2, 1.8, 3.4, 2.7, 4.1, 3.3, 4.6]
group2 = [2.0, 3.0, 2.5, 4.2, 3.8, 5.0, 4.7, 5.5]

context = ss.StatContext(
    n_groups=2, sample_sizes=[len(group1), len(group2)],
    outcome_type="continuous", design="between", paired=False,
)
recommendations = ss.recommend_tests(context)
result = ss.run_test(recommendations[0], data=group1, data2=group2)
```

## "Compare multiple groups"

Pass the groups as one list. Comparisons run only after a significant omnibus
result by default.

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
import scitex_stats as ss

x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
y = [1.0, 2.8, 2.4, 3.9, 5.6, 5.1, 7.2, 7.4]
pearson = ss.test_pearson(x, y)
spearman = ss.test_spearman(x, y)
kendall = ss.test_kendall(x, y)
```

## "Correct for multiple comparisons"

Use correct_pvalues for raw p-values. Its dictionary includes corrected_pvalues,
rejection flags and the number of tests.

```python
import scitex_stats as ss

p_values = [0.01, 0.04, 0.03, 0.08]
fdr = ss.correct_pvalues(p_values, method="fdr_bh")
bonferroni = ss.correct_pvalues(p_values, method="bonferroni")
holm = ss.correct_pvalues(p_values, method="holm")
adjusted_pvalues = fdr["corrected_pvalues"]
```

## "Check sample distributions"

Shapiro-Wilk checks normality. This KS example compares the observations with
a specified Uniform(0, 1) reference distribution.

```python
import scitex_stats as ss

data = [0.04, 0.15, 0.28, 0.39, 0.52, 0.64, 0.81, 0.95]
shapiro = ss.test_shapiro(data)
normality = ss.test_normality(data, warn=False)
ks = ss.test_ks_1samp(data, cdf="uniform")
```

## "Calculate power / sample size"

The two-sample planner returns a tuple of group sizes; the power calculator
returns a number.

```python
from scitex_stats.power import power_ttest, sample_size_ttest

n1, n2 = sample_size_ttest(effect_size=0.5, power=0.8, alpha=0.05)
achieved_power = power_ttest(effect_size=0.5, n1=n1, n2=n2, alpha=0.05)
```

## "Format results for publication"

Format the calculated statistic, degrees of freedom, p-value and effect size.
The formatter returns a dictionary; formatted contains the text.

```python
import scitex_stats as ss

group1 = [1.1, 2.2, 1.8, 3.4, 2.7, 4.1, 3.3, 4.6]
group2 = [2.0, 3.0, 2.5, 4.2, 3.8, 5.0, 4.7, 5.5]

result = ss.run_test("ttest_ind", data=group1, data2=group2, equal_var=False)
formatted = ss.format_results(
    test_name="ttest_ind", statistic=result["statistic"],
    p_value=result["pvalue"], df=result["df"],
    effect_size=result["effect_size"], style="apa",
)
line = formatted["formatted"]
```

## Source and behavioral checks

The owning Python APIs are in auto, posthoc, tests, power, and the public
correction/formatting operations. Existing controls include:

- tests/scitex_stats/auto/test__selector.py
- tests/scitex_stats/posthoc/test__auto.py
- tests/scitex_stats/power/test__power.py
- tests/integration/test_correction_python_api.py
- tests/integration/test_format_results_python_api.py

Examples are source contracts; installed-package and hosted availability
require separate checks.
