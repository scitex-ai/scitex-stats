---
description: |
  [TOPIC] Bounded sample-size planning
  [DETAILS] ANOVA and goodness-of-fit chi-square MCP search bounds, feasible
  targets, minimum sample sizes and explicit unattained-target errors.
tags: [scitex-stats-bounded-sample-size, scitex-stats]
---

# Bounded sample-size planning

For native `scitex_stats.power_analysis` or standalone MCP `power_analysis`,
omit `n` to request a sample size.
`test_type="anova"` uses Cohen's f and searches 2..1000 observations per
balanced group. `test_type="chi2"` uses Cohen's w and searches 10..10000
observations total. For chi-square, `n_groups` means the number of
goodness-of-fit cells: degrees of freedom are `n_groups - 1`; this is not a
general contingency-table degrees-of-freedom interface.

The target `power` must be finite and strictly between 0 and 1. If the target
is not attained at the existing upper bound, the handler returns
`success: false` and an error identifying the range, without a required sample
size. It does not enlarge the search range or return the cap as a solution.
For feasible targets it returns the first attainable integer within that
supported range, including the lower bound when already sufficient.
ANOVA returns `required_n_per_group` and `total_n`; chi-square returns
`required_n`. These are minimums within the supported ranges.

Supplying `n` retains the existing fixed-sample noncentral-F or noncentral
chi-square calculation and response fields. This correction does not qualify
all invalid effect sizes, alpha values or group counts, other power methods,
or a hosted GUI. The synchronous Python dispatcher returns the same numerical payload, including
`test_type`, without MCP success/timestamp fields. Invalid requests raise
exceptions in Python; MCP retains its `success: false` error envelope.
`scitex_stats.power.power_analysis` exposes the same native function.

Dispatch: `power/_power_analysis.py::power_analysis`; transport:
`_mcp/_handlers/_power.py::power_analysis_handler`. Native/MCP method parity,
namespace exports, errors and transport-free use are exercised by
`tests/integration/test_native_power_api.py`.

Bounded search: `power/_omnibus.py::_minimum_n`, `_power_anova`, `_power_chi2`,
with thin `_mcp/_handlers/_power.py` adapters. Actual handler and independent
statsmodels power controls are in
`tests/integration/test_bounded_power_search.py`: unattained targets, inclusive
bounds, normal minimums, invalid targets and unchanged fixed-sample values.

The native dispatcher supports `ttest`, `anova`, `correlation` and `chi2`.
Supplying `n` calculates power; omitting it plans a sample size. It preserves
the existing t-test and Fisher-z correlation approximations; this extraction
is not new scientific qualification for those methods or arbitrary inputs.

```python
from scitex_stats import power_analysis
result = power_analysis(test_type="anova", effect_size=0.3, n_groups=3)
# result["mode"] == "sample_size_calculation"
```
