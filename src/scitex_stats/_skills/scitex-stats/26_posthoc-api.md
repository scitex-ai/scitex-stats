---
description: |
  [TOPIC] Native explicit post-hoc comparisons
  [DETAILS] Synchronous Python dispatch, MCP delegation, preserved method
  policies, result fields, input/error contracts and scope limits.
tags: [scitex-stats-posthoc-api, scitex-stats]
---

# Explicit post-hoc comparisons

```python
from scitex_stats import posthoc_test
result = posthoc_test([[1., 2., 4.], [3., 5., 7.], [6., 8., 10.]], method="dunn")
# result["method"] == "dunn"; result["n_comparisons"] == 3
```

`scitex_stats.posthoc.posthoc_test` exposes the same synchronous native
function. It returns `method`, `n_groups`, `n_comparisons` and `comparisons`.
Python errors raise normally. Standalone MCP `posthoc_test` delegates to this
function and adds its existing success/error envelope and timestamp.

Methods retain the existing explicit-request policies:

- `tukey`: numeric statsmodels Tukey HSD output, with sorted labels and
  group2-minus-group1 differences. Missing backend imports raise explicitly.
  Groups must be nonempty, finite and 1-D, with positive finite pooled error
  variance and residual degrees of freedom. Undefined requests raise in Python
  and return MCP errors without comparisons. Individual constant/singleton
  groups remain usable when the overall pooled error supports the calculation.
- `dunnett`: shared-error SciPy single-step comparisons against `control_group`.
  See [Dunnett details](24_mcp-dunnett.md) for random-state/backend scope.
- `games_howell`: native studentized-range comparisons and simultaneous 95%
  intervals, retaining signed Welch/raw-probability diagnostics.
- `dunn`: native pooled joint-rank/tie correction, with Bonferroni adjustment.

Decisions retain strict adjusted-p < 0.05. No new alpha, confidence-level,
alternative or correction options are added. Fields within `comparisons`
remain method-specific. Automatic `run_posthoc` and legacy `posthoc_*` retain
their existing APIs and policies; their numerical qualification is separate.

Omitted `group_names` uses `Group_1`, `Group_2`, etc. Supplied names must match
the group count and be unique. Dunnett control indices are zero-based and must
be in range. Inputs are converted into independent numeric arrays; the selected
native/MCP tests verify input preservation. Existing method-specific admission
and errors are retained. This ownership extraction does not establish general
all-input validation, whole-omnibus JSON behavior or hosted GUI adoption.

Owning implementation: `posthoc/_posthoc_test.py::posthoc_test` and its private
method adapters. MCP: `_mcp/_handlers/_posthoc.py::posthoc_test_handler`.
Native/MCP equality, labels, errors, exports and transport-free execution:
`tests/integration/test_native_posthoc_api.py`. Numerical/reference and
backend/error controls remain in `tests/scitex_stats/_mcp/_handlers/test__posthoc.py`
and `tests/integration/test_dunnett_backend.py`, `test_tukey_numeric_precision.py`,
`test_dunn_tie_correction.py`, `test_dunn_large_tie_counts.py` and
`test_tukey_backend_availability.py`. Extraction preserves their formulas;
these controls qualify only the scopes they exercise.

Tukey admission and unchanged positive Tukey-Kramer values/intervals are checked
against independent SciPy studentized-range calculations in
`tests/integration/test_tukey_admission.py`. Zero/nonfinite pooled error is an
explicit error rather than a successful undefined probability or degenerate
confidence interval. This is scoped admission, not general numerical-stability
qualification for every finite magnitude or generated output.
