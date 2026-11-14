---
description: |
  [TOPIC] MCP tools
  [DETAILS] Names registered by the standalone Stats MCP server, with guidance
  for configured client namespaces and separate interface contracts.
tags: [scitex-stats-mcp-tools, scitex-stats]
---

# MCP tools for AI agents

## Standalone server

`scitex-stats mcp start` provides **18 registered MCP tools** with the bare
names below. Inspect the selected environment with:

```bash
scitex-stats mcp list-tools
scitex-stats mcp list-tools --json
```

The standalone wire name is `run_test`, for example. Client-qualified names
and umbrella aliases depend on the configured server. The parent skill's
`allowed-tools` pattern addresses an umbrella/client namespace; it does not
rename the standalone tools. Discover that configured server's actual tool
list before using aliases such as `stats_run_test`. Availability of every
standalone tool under an umbrella alias is a separate qualification.

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

## Inputs and results

The catalogue describes registration, not interchangeable Python/CLI/MCP
signatures or complete numerical-method qualification. Use each advertised
tool schema for its arguments. `run_test` accepts the test name separately
from the tool name; `ttest` and `fisher` are dispatcher input spellings.

`describe` requires at least one non-NaN observation. Empty or all-NaN input
returns `success: false` and `error: "No valid data points"`.

`p_to_stars` requires a numeric probability in `[0, 1]` and, when supplied,
exactly three finite, strictly increasing numeric thresholds in `[0, 1]`.
Booleans and numeric strings are rejected by standalone argument admission.
Its threshold comparisons remain strict. Type-admission errors and returned
handler domain-error reports are separate protocol outcomes.

`verify_result` takes exactly one of `result` or `result_file`; its native
verification options stay at their defaults. Require `verified is True`
before reporting a number; `success: true` can accompany a failed integrity
check. See [17_provenance-verify.md](17_provenance-verify.md) for supported
inputs, native-only controls and hash-only behavior.

`skills_get` reads resources through the installed owning provider. A source
edit does not establish that an installed or hosted server supplies those
bytes; inspect the returned resource in that environment.

## Owning implementation and checks

The registration source is `scitex_stats/_server.py`. Statistical adapters
mostly delegate through `scitex_stats/_mcp/_handlers/`; data-based
recommendations and APA checks call their native leaf implementations.
Skill tools use Dev dispatch and the owning package's registered resources.

Catalogue controls: `tests/integration/test_mcp_catalogue_documentation.py`.
Real standalone protocol controls include
`tests/integration/test_mcp_star_stdio.py` and
`tests/integration/test_mcp_describe_stdio.py`. These selected controls do not
qualify every tool, client namespace, transport or hosted deployment.
