---
description: |
  [TOPIC] Mcp Tools
  [DETAILS] 18 tools accessible via scitex MCP server: 12 statistical
  tools plus report, verify, skills, and APA helpers.
tags: [scitex-stats-mcp-tools, scitex-stats]
---


# MCP Tools (for AI Agents)

All tools are prefixed `stats_` under the scitex MCP server
(`scitex-stats mcp list-tools`: 18 tools, 9 modules).

| Tool | Purpose |
|------|---------|
| `stats_run_test` | Run any statistical test by name |
| `stats_recommend_tests` | Auto-recommend appropriate tests for given data |
| `stats_describe` | Compute descriptive statistics (mean, std, CI, etc.) |
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
