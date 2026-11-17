---
description: |
  [TOPIC] Provenance receipts and verify()
  [DETAILS] Every run_test / full_report / MCP run_test result carries result["provenance"] (test + parameters, per-input SHA-256 with n, seed, versions, UTC timestamp, result hash) and result["input_integrity"]; verify(result, data) re-checks hashes and recomputes bit-for-bit.
tags: [scitex-stats-provenance-verify]
---

# Provenance receipts and `verify()`

## Rule for agents

Before you report any number from scitex-stats, run `verify` on the result.
Report the number only if `verified` is `True`.

```python
import scitex_stats as ss

r = ss.run_test("ttest_ind", data=x, data2=y)
check = ss.verify(r, data=x, data2=y)   # or ss.verify(r): uses the embedded copy
assert check["verified"], check["summary"]
```

CLI (exit code 0 = verified, 1 = not verified):

```bash
scitex-stats verify result.json
scitex-stats verify result.json data.csv --x group_a --y group_b
```

MCP: `verify_result(result=...)` or `verify_result(result_file=...)`.
For `full_report` results, also pass `source_result` as described below.

## What `verify` checks

| check | fails when |
|-------|-----------|
| `receipt` | the receipt was edited (its own SHA-256 no longer matches) |
| `result` | any result field was edited after computation |
| `inputs` | the data supplied (or embedded) does not hash to the recorded SHA-256 |
| `recompute` | re-running the recorded test, parameters and seed does not reproduce every field exactly; `differences` names the fields |

Library-version drift is listed under `warnings`; it is the usual reason a
recompute differs.

## Receipt schema (`scitex-stats/provenance@1`)

```text
provenance
  schema, api ("run_test" | "full_report" | "mcp.run_test")
  test: {name, function, parameters}
  inputs: {<name>: {sha256, n, shape, values?}}   # values embedded up to 100k numbers
  input_sha256            # scitex-clew combine_hashes over the per-input digests
  randomness: {stochastic, seed, generator}
  versions: {scitex-stats, numpy, scipy, pandas, statsmodels, pingouin, scitex-clew, python, platform}
  result_sha256           # canonical JSON of the result minus provenance/timestamp
  hash_algorithm, timestamp_utc, receipt_sha256
  source / source_result_sha256   # MCP data_file hash; full_report's input result
```

## Randomness

Every resampling path takes `seed=42` by default and draws from a fresh
`numpy.random.default_rng(seed)`; nothing touches global numpy state. Today
that is `full_report`'s bootstrap CIs (Mann-Whitney rank-biserial r and
small-n correlations). The analytic tests in `run_test` are deterministic and
record `seed: null`.

## Input integrity

`result["input_integrity"]` reports, per input, `n_input`, `n_used`,
`n_excluded`, `excluded_indices`, `excluded_reason` and `coercion`.
`nan_policy="omit"` (default) excludes NaN (pairwise for paired, correlation
and Friedman designs); `nan_policy="raise"` rejects them. Infinite values,
non-numeric values, empty inputs and NaN in contingency tables always raise
`InputIntegrityError`.

## scitex-clew

Save the result with `scitex_io.save(result, "result.json")` inside a clew
session: clew records the file as an output node (and files read with
`scitex_io.load` as inputs) and hashes it, receipt included.
`scitex-stats verify result.json` then recomputes from the embedded inputs.

## Grouped NumPy inputs

Native receipts accept a 2-D NumPy array in `verify(result, groups=array)`;
for an MCP-origin receipt, pass the grouped array as `data=array`. Supplied
arrays retain the same input-hash and recomputation checks as lists. A changed
value or shape still fails verification. Container selection checks for None
explicitly, so NumPy's ambiguous boolean conversion is not involved.
Owner: `_verify.py::_supplied_inputs`; native/MCP-origin list/array, tamper and
shape controls: `tests/integration/test_verify_array_inputs.py`.

## Verifying a full report

Recomputing `full_report` requires the original `run_test` result as well as
its data (embedded or supplied). The report alone does not embed that source
result. Omitting it leaves `recompute` failed and `verified: false`.

Python: `ss.verify(report, source_result=base)`.
MCP: `verify_result(result=report, source_result=base)`, or use `result_file`
for the saved report while still supplying the source-result object.
CLI accepts the saved source-result JSON:

```bash
scitex-stats verify report.json --source-result base.json
```

CLI retains exit 0 only for verified results and 1 for unverified results.
MCP `success: true` means the verification ran; check `verified` separately.
Supplying a source result does not bypass receipt, result, input-hash or
recomputation checks. A changed report, source statistic or supplied data
remains unverified. This is local recomputation evidence, not proof of the
external origin or scientific validity of the data.

Owners: `_verify.py::verify` / `_recompute`; adapters are
`_cli/verify.py::verify`, `_server.py::verify_result` and
`_mcp/_handlers/_verify.py::verify_result_handler`.
Controls: `tests/integration/test_report_source_input.py` and
`tests/scitex_stats/test__verify.py`.

## Recorded source identity

Full-report recomputation first compares the supplied source with the report's
`source_result_sha256` and `source_receipt_sha256`. A mismatch fails the
existing `recompute` check, even if the changed source would render identical
report fields. The source-result digest uses the existing canonical hash:
`timestamp` and `provenance` are excluded. Its recorded receipt reference is
compared separately. A source originally recorded without a receipt still
works with the same source and absent receipt reference.

These are consistency checks against the report's recorded values. They do
not authenticate authorship, recursively validate every field of a source
receipt, or establish external data origin. Verify the original run-test
result separately when checking its own receipt, inputs and recomputation.
Owners: `_verify.py::_recompute`, `_provenance.py::hash_result` and
`reporting/_full_report.py::full_report`. Controls:
`tests/integration/test_report_source_digest.py`.

## Supplied input slots must match the receipt

For native `run_test` receipts, use `data`, `data2` and `groups` in their
original native slots. For MCP-origin receipts, pass the original list of
groups in `data`; the receipt names those inputs `data[0]`, `data[1]`, etc.
Supplying `data2` or nonempty `groups` for an MCP-origin receipt does not match
its recorded slots: the `inputs` check fails with `not in receipt`, recompute
is skipped, and `verified` is false. Those arguments are not silently ignored,
even when valid `data` is also supplied or embedded data remains available.

The same native verifier backs CLI and MCP. A completed MCP verification still
returns `success: true` when `verified` is false; inspect the check statuses.
Correctly supplied and embedded MCP inputs retain existing behavior.
Owners: `_verify.py::_supplied_inputs` / `_resolve_inputs`.
List/NumPy, explicit/embedded input controls:
`tests/integration/test_verify_supplied_slots.py`.

## CLI diagnostics and exit status

`verify` exits 0 for verified results, 1 for completed but unverified results,
and 2 for invalid command usage or JSON syntax/text-decoding errors in
`RESULT_FILE` or `--source-result`. JSON input errors name the file argument or option in
the CLI diagnostic. Text mode (`--no-json`) also reports a missing receipt as
unverified; it does not require the optional `warnings` list to be present.
These diagnostics do not alter native verification or MCP result envelopes.
Other data-loading failures and invalid receipt structures are separate scope.
Owner: `_cli/verify.py::verify`; controls:
`tests/integration/test_verify_cli_errors.py`.
