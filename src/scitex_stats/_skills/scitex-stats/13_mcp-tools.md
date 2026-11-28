---
description: |
  [TOPIC] Mcp Tools
  [DETAILS] 19 tools accessible via scitex MCP server: 13 statistical
  tools plus report, verify, skills, and APA helpers.
tags: [scitex-stats-mcp-tools, scitex-stats]
---


# MCP Tools (for AI Agents)

All tools are prefixed `stats_` under the scitex MCP server
(`scitex-stats mcp list-tools`: 19 tools).

| Tool | Purpose |
|------|---------|
| `stats_run_test` | Run any statistical test by name |
| `stats_recommend_tests` | Auto-recommend appropriate tests for given data |
| `stats_describe_data` | Compute descriptive statistics (mean, std, CI, etc.); was `stats_describe` before 1.1.0 |
| `stats_bootstrap_ci` | Seeded bootstrap CI of a median or mean |
| `stats_effect_size` | Calculate effect size between groups |
| `stats_correct_pvalues` | Apply multiple comparison correction |
| `stats_posthoc_test` | Run post-hoc pairwise comparisons |
| `stats_power_analysis` | Power analysis and sample size estimation |
| `stats_normality_test` | Test data for normality |
| `stats_format_results` | Format statistical results for publication |
| `stats_p_to_stars` | Convert p-value to significance stars |
| `stats_generate_report` | Write a bundled statistical report (PDF/HTML) |
| `stats_verify_result` | Verify a result's receipt, data hashes and statistics |
| `stats_validate_apa` | Report APA 7 violations in a results string |
| `stats_skills_list` / `stats_skills_get` | List / fetch bundled agent skills |
| `stats_check_applicability` | Decide per-test applicability for data |
| `stats_recommend_test` | Recommend ONE primary test with reason |
| `stats_run_all_applicable` | Run every applicable test (primary + sensitivity) |

Descriptive statistics require at least one non-NaN observation. Empty or
all-NaN input returns `success: false` and `error: "No valid data points"`.

## Python API behind each tool

Every tool wraps one public synchronous function that returns the same
payload without the MCP envelope (`success`, `timestamp`) and raises
instead of returning `success: false`:

| Tool | Python API |
|------|------------|
| `stats_correct_pvalues` | `scitex_stats.correct_pvalues(pvalues, method, alpha)` |
| `stats_effect_size` | `scitex_stats.effect_size(group1, group2, measure)` |
| `stats_normality_test` | `scitex_stats.normality_test(data, method)` |
| `stats_posthoc_test` | `scitex_stats.posthoc_test(groups, group_names, method, control_group)` |
| `stats_power_analysis` | `scitex_stats.power_analysis(test_type, effect_size, alpha, power, n, n_groups, ratio)` |
| `stats_format_results` | `scitex_stats.format_results(test_name, statistic, p_value, ...)` |
| `stats_describe_data` | `scitex_stats.describe(data)` |
| `stats_bootstrap_ci` | `scitex_stats.bootstrap_ci(data, statistic, ...)` (named statistics only) |
| `stats_verify_result` | `scitex_stats.verify(result, data, data2, groups)` |

Python APIs with no tool yet are recorded in
`.scitex/dev/mcp-parity-baseline.yaml`; the audit fails if a new API
lands without a tool, and the list may only shrink.

## Handler Organization

MCP handlers are in `scitex_stats/_mcp/_handlers/`:
- `_run_test.py` — Main test dispatcher
- `_recommend.py` — Auto test recommendation
- `_descriptive.py` — Descriptive statistics
- `_effect_size.py` — Effect size computation
- `_corrections.py` — Multiple comparison correction
- `_posthoc.py` — Post-hoc tests
- `_power.py` — Power analysis
- `_normality.py` — Normality testing
- `_format.py` — Publication formatting
- `_stars.py` — p-to-stars conversion
- `_report.py` — bundled report generation (PDF/HTML)
- `_verify.py` — result receipt / recompute verification
