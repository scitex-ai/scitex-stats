---
name: scitex-stats
description: |
  [WHAT] Publication-ready statistical testing for 23 tests.
  [WHEN] Use when the user asks to "run a t-test / ANOVA / correlation / normality test", "compare two groups", "test if distributions differ", "compute p-value", "compute effect size", "correct for multiple comparisons", "compute required sample size", "pick the right statistical test".
  [HOW] `import scitex_stats` for the Python API; see leaf skills for entry points.
tags: [scitex-stats]
allowed-tools: mcp__scitex__stats_*
primary_interface: python
interfaces:
  python: 3
  cli: 1
  mcp: 2
  skills: 2
  hook: 0
  http: 0
---


# scitex-stats

Publication-ready statistical testing framework with 23 tests, effect sizes, power analysis, and automatic test recommendation.

## Installation & import (two equivalent paths)

The same module is reachable via two install paths. Both forms work at
runtime; which one a user has depends on their install choice.

```python
# Standalone — pip install scitex-stats
import scitex_stats as sst
sst.run_test(...)

# Umbrella — pip install scitex
import scitex.stats as sst
sst.run_test(...)
```

`pip install scitex-stats` alone does NOT expose the `scitex` namespace;
`import scitex.stats` raises `ModuleNotFoundError`. To use the
`scitex.stats` form, also `pip install scitex`.

See [../../general/02_interface-python-api.md] for the ecosystem-wide
rule and empirical verification table.

## Sub-skills

### Mandatory (per ecosystem spec)
- [01_installation.md](01_installation.md) — pip install, extras, verification
- [02_quick-start.md](02_quick-start.md) — Smallest end-to-end t-test example
- [03_python-api.md](03_python-api.md) — Public callables (dispatcher + 23 tests)
- [04_cli-reference.md](04_cli-reference.md) — Full CLI command surface

### Workflows
- [10_quick-start.md](10_quick-start.md) — Extended Python patterns (run_test, return_as)
- [11_workflows.md](11_workflows.md) — Common analysis patterns
- [12_cli-reference.md](12_cli-reference.md) — Extended CLI patterns
- [13_mcp-tools.md](13_mcp-tools.md) — MCP tools for AI agents

### Reference
- [22_test-catalog.md](22_test-catalog.md) — All 23 statistical tests with categories
- [21_effect-sizes.md](21_effect-sizes.md) — Effect size measures and interpretation

## CLI

```bash
scitex-stats <command> [options]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `stats_run_test` | Run a statistical test |
| `stats_recommend_tests` | Auto-recommend tests for data |
| `stats_describe` | Descriptive statistics |
| `stats_effect_size` | Compute effect sizes |
| `stats_correct_pvalues` | Multiple comparison correction |
| `stats_posthoc_test` | Post-hoc pairwise tests |
| `stats_power_analysis` | Power analysis / sample size |
| `stats_normality_test` | Normality testing |
| `stats_format_results` | Format for publication |
| `stats_p_to_stars` | p-value to significance stars |


## Environment

- [14_env-vars.md](14_env-vars.md) — SCITEX_* env vars read by scitex-stats at runtime
- [20_env-vars.md](20_env-vars.md) — SCITEX_STATS_* env vars read by the standalone Django app (`scitex-stats gui`)
