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

The `power_analysis` transport delegates to native `scitex_stats.power_analysis`;
Python returns numerical fields and raises errors, while MCP retains its envelope.
For ANOVA and chi-square sample-size bounds and target errors, see
[bounded planning](25_bounded-sample-size.md).

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
certification. Native `scitex_stats.format_results` is synchronous and uses
the same argument names/defaults and domain payload (`formatted`, `stars`,
`style`, `style_used`); only MCP adds success/timestamp fields or converts
exceptions to `success: false`. The implementation lives in
`auto/_format_results.py`, independent of MCP. Native tests are in
`tests/scitex_stats/auto/test__format_results.py`; real protocol parity is
checked in `tests/integration/test_mcp_describe_stdio.py`. Broader legacy
scalar validation remains unfinished. Supplied `ci_lower` and `ci_upper`
render as `CI [lower, upper]`
at the selected preset's effect precision. Both bounds and an effect
estimate must be finite; bounds must be ordered. A partial pair, reversed
bounds or missing effect estimate returns `success: false`. Omitting both
bounds preserves point-only output. No interval is calculated and no
confidence level (such as 95%) is inferred. A dedicated Science preset,
confidence-level metadata and complete journal compliance remain unfinished.
See the native
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


## Authoritative metadata discovery

The default server's registered wire catalog owns tool names, descriptions
and input schemas. `_mcp.tool_schemas.get_tool_schemas()` returns the same
MCP Tool models as an in-memory client; the CLI uses this provider too.
`scitex-stats mcp list-tools --json -v` adds full `schemas` by tool name;
plain `--json` retains its existing name/module output. Module filters
also limit the verbose schema map.
Async consumers can await `get_tool_schemas_async()`. The synchronous
bridge also works inside an existing event loop, using an owned portal.
No statistical tools are executed during discovery and no catalog is cached.
The run-test enum comes from the same 23-name map used by MCP execution;
this is distinct from the broader Python test facade. Unknown test names
still reach the existing handler error path; the enum adds metadata only.
This default catalog is not authenticated hosted-session discovery.
Behavior/metadata checks are in `tests/scitex_stats/_mcp/test_tool_schemas.py`;
actual protocol comparison is in `tests/integration/test_mcp_describe_stdio.py`.


`run_test` also forwards the optional file `sep` override to the leaf parser.
Explicit overrides are retained in `provenance.source.sep`; omission keeps
Auto behavior. See [MCP file input](23_csv-import.md#mcp-file-input) for the
actual JSON request. Every successful file result records the chosen token in
`provenance.source.sep_used` (a space token means whitespace runs).


For `posthoc_test` with `method="games_howell"`, report `p_adj`: it is the
Games–Howell studentized-range family-wise probability. `p_value` remains the
unadjusted Welch diagnostic; it is not the post-hoc decision probability.
Comparisons include signed mean differences, Welch t/df, q, 95% simultaneous
`ci_lower`/`ci_upper` with `confidence_level=0.95`, and JSON boolean `reject`.
The implementation delegates to `posthoc._auto._games_howell`; no Bonferroni
multiplier is applied. Finite 1D samples need at least two observations each;
a pair of constant samples is undefined and returns an explicit error.
Reference: [SciPy Games–Howell](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html)
(`equal_var=False`). Numerical/interval/wire controls are in
`tests/scitex_stats/_mcp/_handlers/test__posthoc.py`.


`posthoc_test` requires one unique `group_names` label per input group.
Empty, incomplete, extra or repeated labels return `success=false`, a
`group_names` error and no comparisons. Omitting names (`null`) uses
`Group_1`, `Group_2`, … without merging or dropping groups.
Controls: `tests/integration/test_posthoc_group_names.py` and
`_mcp/_handlers/_posthoc.py::posthoc_test_handler`.


For `method="dunnett"`, see [Dunnett control comparisons](24_mcp-dunnett.md)
for shared-error probabilities, zero-based control indices and backend requirements.


`method="tukey"` requires usable statsmodels. Backend import failures return
`success=false`, a Tukey HSD error and no comparisons; no substitute test
is run. Backend arrays supply probabilities, mean differences and simultaneous
intervals before display rounding. Pairs use sorted labels; `mean_diff` and
its interval are group2 minus group1. `reject` is the backend JSON boolean.
Controls: `tests/integration/test_tukey_numeric_precision.py`,
`tests/integration/test_tukey_backend_availability.py` and
`_mcp/_handlers/_posthoc.py::_tukey_hsd`.


For `method="dunn"`, joint ranks include the pooled tie correction.
`p_value` is the two-sided normal-tail probability; `p_adj` retains the
Bonferroni family adjustment and `reject` is a JSON boolean using the existing
strict 0.05 threshold. Non-empty finite 1D groups are required; a pooled sample
with no rank variance returns an explicit error. The adapter delegates to
`posthoc._auto._dunn`; automatic native `run_posthoc(..., omnibus="kruskal")`
retains its default Holm adjustment. Controls and independent reference values:
`tests/integration/test_dunn_tie_correction.py`.
