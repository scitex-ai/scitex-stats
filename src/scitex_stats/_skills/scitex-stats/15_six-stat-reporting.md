---
description: |
  [TOPIC] Six-Stat Reporting
  [DETAILS] the mandatory six-stat reporting doctrine (n, 95% CI, method, p,
  effect size, statistic) and the full_report() bundler that enforces it.
tags: [scitex-stats-six-stat-reporting, scitex-stats]
---


# scitex-stats — Six-Stat Reporting Doctrine

**Convention (mandatory).** Every statistic you report must carry all six of
these fields — partial reporting is incomplete under the operator's six-stat
doctrine (2026-07-05):

| # | Field | Meaning |
|---|-------|---------|
| 1 | **n** | sample size (capital `N` = upper-level unit, e.g. subjects; lowercase `n` = lower-level, e.g. windows; use informative subscripts such as `N_subjects`, `n_windows`) |
| 2 | **95% CI** | confidence interval for the reported effect/estimate |
| 3 | **method** | the statistical test / method name |
| 4 | **p-value** | significance (use `p < .001` convention, no leading zero) |
| 5 | **effect size** | Cohen's d, eta-squared, rank-biserial r, etc., with interpretation |
| 6 | **statistic** | the test statistic with df (e.g. `t(58) = 2.34`) |

Statistical symbols are italicized when rendered (`n`, `N`, `p`, `t`, `F`,
`d`, `r`, `W`, …) via `fmt_sym` (matplotlib mathtext) / `fmt_sym_md`
(markdown plain text).

## Use `full_report` for a complete report

`run_test()` / `test_*()` already emit n, statistic, p-value, effect size and
method, but **not** a CI. To get all six, bundle the result with
`scitex_stats.full_report`:

```python
import scitex_stats as ss
from scitex_stats import full_report

x = ss.run_test("ttest_ind", data=g1, data2=g2)
report = full_report(x, data=g1, data2=g2)

report["formatted"]
# "Welch's t-test (independent): t(58) = -3.21, p = .002, *d* = -0.83,
#  95% CI [-1.30, -0.35], n_x = 30, n_y = 30"
```

`full_report(result, *, data=..., data2=..., ci=..., confidence=0.95,
n_bootstrap=10000, random_state=..., strict=True)` returns a dict bundling all
six fields plus a `formatted` string, and — by default — **raises
`IncompleteReportError` if any of the six cannot be determined**. That makes
partial reporting a checked invariant, not just a style note.

CI is derived with test-appropriate semantics (never a generic mean-difference
interval for a non-mean statistic):

- **t-tests** → analytic mean-difference CI (`scipy.stats.ttest_*.confidence_interval`)
- **Pearson / Spearman** → Fisher-z CI on the correlation (perfect |r| ≥ 1 → `[r, r]`)
- **Mann-Whitney U** → percentile bootstrap of the rank-biserial r (bounded [-1, 1])
- **other tests** (Friedman, RM-ANOVA, Kruskal, chi-square, …) → no generic
  interval; pass an explicit `ci=(lo, hi)` or the report marks `ci` missing

A NaN/inf statistic, p-value or effect size, or a NaN/reversed confidence
interval, is treated as missing (and raises under `strict=True`).

## Strict vs. lenient

- `strict=True` (default) — raise `IncompleteReportError` on any missing field.
  Use when a complete six-stat report is required.
- `strict=False` — log a warning and return the partial report with a
  `missing_fields` list. Use when assembling a report that is intentionally
  incomplete and you want to see which fields are still absent.
