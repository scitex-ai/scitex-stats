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
| `stats_describe` | Compute count, mean, std, percentiles, IQR, skewness and kurtosis |
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

The standalone server exposes `describe`; the table uses the umbrella
`stats_` namespace. Its optional `percentiles` argument accepts numbers from
0 to 100. Omission uses `[25, 50, 75]`; an explicit `[]` returns an empty
`percentiles` object. Fractional labels remain distinct (`"2.5"`, `"2.9"`),
while integral labels retain their existing spelling (`"25"`, including a
request for `25.0`). This handler does not return confidence intervals.
The owning implementation is `_mcp/_handlers/_descriptive.py::describe_handler`;
handler controls and the real stdio-server checks are in
`tests/scitex_stats/_mcp/_handlers/test__descriptive.py` and
`tests/integration/test_mcp_describe_stdio.py`.

Descriptive statistics require at least one non-NaN observation. Empty or
all-NaN input returns `success: false` and `error: "No valid data points"`.

The `effect_size` tool uses the synchronous `scitex_stats.effect_size`
domain API; see [Python API](03_python-api.md#effect-size-dispatch).
Unpooled Cohen/Hedges requests (`pooled=False`) are unsupported and return
`success: false`; they do not silently compute a pooled value. Inputs must
be finite 1-D groups with the measure-specific sample minimums in that API.

The `normality_test` tool uses `scitex_stats.normality_test`; see
[Python API](03_python-api.md#normality-dispatch). Undersized or unusable
samples return `success: false` with an error, never a successful error
object. NaNs are omitted and `n` now counts tested values; `n_input` and
`n_omitted` retain input accounting. Anderson returns a 5% critical value,
not a p-value. The other three methods report p-values.

The `correct_pvalues` tool delegates to `scitex_stats.correct_pvalues`;
see [Python API](03_python-api.md#p-value-correction-dispatch). Non-empty,
finite 1-D p-values and scalar alpha must be in [0,1]; invalid requests
return `success: false`. Unknown method names retain their legacy BH
fallback and echoed `method`; additive `method_used` identifies the actual
calculation. The existing backend-free reference adapter is retained.

The standalone `format_results` transport uses the existing legacy style
presets. `apa` selects `apa_latex`, `nature` selects `nature_latex`, and
`brief` selects `plain`. The returned `style` still echoes the request;
additive `style_used` identifies the actual preset. There is no dedicated
Science preset: `science` and unknown legacy names retain the APA LaTeX
fallback, now reported explicitly. This is not a new journal-compliance
certification or a native root `format_results` API. Confidence-interval
arguments are retained but currently not rendered by this legacy handler;
a dedicated Science preset and interval rendering remain unfinished
capabilities. See the native
[legacy formatter scope](03_python-api.md#legacy-line-formatter-scope).

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
