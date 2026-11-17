---
description: |
  [TOPIC] MCP Dunnett control comparisons
  [DETAILS] Shared pooled error, single-step family probabilities, reproducible integration and backend/input requirements.
tags: [scitex-stats-mcp-dunnett, scitex-stats]
---

# Dunnett control comparisons

This page covers `posthoc_test` with `method="dunnett"`. The owning native
helper, `posthoc/_control.py::_dunnett_control`, uses SciPy's original
single-step Dunnett procedure, rather than Bonferroni-adjusted pairwise tests.
The MCP adapter only maps labels and result fields.

## Request and assumptions

```json
{
  "groups": [[2.9, 3.0, 2.5, 2.6, 3.2], [3.8, 2.7, 4.0, 2.4], [2.8, 3.4, 3.7, 2.2, 2.0]],
  "group_names": ["control", "A", "B"],
  "method": "dunnett",
  "control_group": 0
}
```

Samples must be non-empty finite 1D groups, with positive finite pooled error
and positive residual degrees of freedom across all groups. There must be at
least one treatment and one control. Dunnett assumes independent observations,
normality within groups and a common finite population variance; input checks
do not establish these study assumptions.

`control_group` is zero-based: `0 <= control_group < len(groups)`. Invalid
indices return `success=false`, an explicit `control_group` error and no
comparisons. Supplied labels must be unique and match the group count. Valid
controls are excluded from their treatment comparisons; treatment order follows
the input order. Omitting labels preserves the automatic `Group_1`, … names.

## Results

| Field | Meaning |
|---|---|
| `group`, `vs_control` | Treatment and control labels. |
| `mean_diff` | Treatment mean minus control mean. |
| `t_statistic` | Signed statistic using the error pooled across all groups. |
| `df` | Shared residual degrees of freedom. |
| `p_value` | Unadjusted two-sided marginal t probability using that statistic/df. |
| `p_adj` | Single-step multiple-to-control Dunnett probability. |
| `reject` | JSON boolean: `p_adj < 0.05`, preserving the strict decision rule. |

Report `p_adj` for family-wise inference. `p_value` is diagnostic, not a second
multiple-comparison correction. The current MCP interface remains two-sided
with its existing 0.05 decision threshold; no alternative/alpha option is added.
This interface does not return simultaneous confidence intervals.

## Backend and repeatability

`scipy.stats.dunnett` (SciPy 1.11+) must be usable. An unavailable backend
returns an explicit method error; no substitute test is labeled Dunnett.
The package's general SciPy floor is unchanged, so an older installation can
still use its other supported methods while this method requires that backend.

SciPy evaluates multivariate-t probabilities with randomized quasi-Monte Carlo
integration. Each call uses a private NumPy Generator seeded with 42, through
`rng` when supported or the older `random_state` keyword. Repeated calls in the
same installed profile are repeatable; bitwise equality across SciPy versions
is not promised. Published-reference controls allow numerical integration error.

## Ownership and verification

Owner: `posthoc/_control.py::_dunnett_control`; adapter:
`_mcp/_handlers/_posthoc.py::_dunnett`. Controls:
`tests/integration/test_dunnett_backend.py`,
`tests/integration/test_posthoc_control_index.py` and
`tests/integration/test_posthoc_group_names.py`.

References: [SciPy Dunnett](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.dunnett.html)
and its [SciPy 1.11.4 example](https://docs.scipy.org/doc/scipy-1.11.4/reference/generated/scipy.stats.dunnett.html).
These describe a numerical single-step procedure, not exact arithmetic.

The separate legacy Python API `posthoc.posthoc_dunnett` and
`dunnett_critical_value` are unchanged and still approximate. MCP checks do not
qualify those functions, every invalid input, other interfaces or hosted UI.
