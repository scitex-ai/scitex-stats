---
name: scitex-stats
description: |
  [WHAT] Publication-ready statistical testing for 25 tests.
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

Publication-ready statistical testing framework with 25 tests, effect sizes, power analysis, and automatic test recommendation.

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
- [03_python-api.md](03_python-api.md) — Public callables (dispatcher + 25 tests)
- [04_cli-reference.md](04_cli-reference.md) — Full CLI command surface

### Workflows
- [10_quick-start.md](10_quick-start.md) — Extended Python patterns (run_test, return_as)
- [11_workflows.md](11_workflows.md) — Common analysis patterns
- [12_cli-reference.md](12_cli-reference.md) — Extended CLI patterns
- [13_mcp-tools.md](13_mcp-tools.md) — MCP tools for AI agents
- [15_six-stat-reporting.md](15_six-stat-reporting.md) — Six-stat reporting doctrine (n, CI, method, p, effect size, statistic) + full_report()
- [16_apa7-reporting.md](16_apa7-reporting.md) — Exact APA 7 line per test (result["apa"]), table/descriptives forms, validate_apa(), with APA 7 section per rule
- [17_provenance-verify.md](17_provenance-verify.md) — Provenance receipts, seed=42 determinism, input integrity, verify() before reporting any number

### Reference
- [22_test-catalog.md](22_test-catalog.md) — All 25 statistical tests with categories
- [21_effect-sizes.md](21_effect-sizes.md) — Effect size measures and interpretation

## CLI

```bash
scitex-stats <command> [options]
```

## MCP Tools

The standalone `scitex-stats mcp start` server has **18 registered MCP tools**:

| Tool | Purpose |
|------|---------|
| `recommend_tests` | Recommend tests from group counts, sample sizes and design. |
| `check_applicability` | Assess applicable tests for grouped data and design. |
| `recommend_test` | Recommend one primary test from grouped data and design. |
| `run_all_applicable` | Run the primary test and applicable sensitivity analyses. |
| `run_test` | Run one named statistical test. |
| `describe` | Calculate descriptive statistics for a numeric sequence. |
| `normality_test` | Run a supported normality check. |
| `posthoc_test` | Request the selected post-hoc comparison procedure. |
| `effect_size` | Calculate a supported two-group effect size. |
| `power_analysis` | Calculate achieved power or required sample size. |
| `correct_pvalues` | Apply a multiple-comparison correction. |
| `format_results` | Format statistical results in a supported journal style. |
| `p_to_stars` | Convert a numeric p-value using strict star thresholds. |
| `validate_apa` | Report statistical-text or HTML formatting violations. |
| `generate_report` | Generate a statistical report from groups or a data file. |
| `verify_result` | Check a result or result file using native default verification options. |
| `skills_list` | List discoverable Stats skill resources. |
| `skills_get` | Read a discoverable Stats skill resource. |

The bare names above belong to the standalone registry. The existing
`allowed-tools` pattern in this skill addresses an umbrella/client namespace;
use the actual names advertised by that configured server when selecting
client-qualified or `stats_*` aliases. Alias availability is separate from
standalone registration. See [13_mcp-tools.md](13_mcp-tools.md) for discovery,
argument/result distinctions and owning tests.

## Environment

- [14_env-vars.md](14_env-vars.md) — SCITEX_* env vars read by scitex-stats at runtime
- [20_env-vars.md](20_env-vars.md) — SCITEX_STATS_* env vars read by the standalone Django app (`scitex-stats gui`)

## App data input

- [23_csv-import.md](23_csv-import.md) — Import dialog, auto/manual separators, column preview, quoted cells, and source-row integrity.
