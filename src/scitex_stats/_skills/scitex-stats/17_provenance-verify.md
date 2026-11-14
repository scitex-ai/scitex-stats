---
description: |
  [TOPIC] Provenance receipts and verify()
  [DETAILS] Every run_test / full_report / MCP run_test result carries result["provenance"] (test + parameters, per-input SHA-256 with n, seed, versions, UTC timestamp, result hash) and result["input_integrity"]; verify(result, data) re-checks hashes and recomputes the comparable result fields.
tags: [scitex-stats-provenance-verify]
---

# Provenance receipts and `verify()`

## Rule for agents

Before you report any number from scitex-stats, run `verify` on the result.
Report the number only if `verified` is `True`.

```python
import scitex_stats as ss

x = [5.1, 4.9, 6.2, 5.8, 6.0, 5.5, 5.3, 6.1]
y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7.0, 6.6]
r = ss.run_test("ttest_ind", data=x, data2=y)
check = ss.verify(r, data=x, data2=y)   # or ss.verify(r): uses the embedded copy
assert check["verified"], check["summary"]
```

CLI, after saving the result as `result.json` (valid invocations exit 0 when
verified and 1 otherwise). For the CSV example, `data.csv` has the same input
values in `group_a` and `group_b` columns:

```bash
scitex-stats verify result.json
scitex-stats verify result.json data.csv --x group_a --y group_b
```

MCP: `verify_result(result=...)` or `verify_result(result_file=...)`; provide
exactly one source. The existing adapter maps to `scitex_stats.verify` with
`source_result=None` and `recompute=True`. It accepts optional `data`, `data2`
and `groups` overrides. A returned `success: true` means a report was produced;
require `verified is True` before reporting a number. Tampering or a missing
receipt can produce `success: true` with `verified: false`. Source/file errors
produce `success: false` and an error message.

Python additionally accepts `source_result=base_result` when checking a
`full_report` result. That option is required for its recomputation. The current
MCP adapter does not expose it, so full-report verification requiring a source
result remains an interface gap. Use the native Python option for that case.

Python's `recompute=False` and CLI `--no-recompute` leave the recompute check
with status `skip`. Because `verified` requires every check to pass, these
hash-only reports have `verified: false`; the CLI exits 1. MCP always requests
recomputation and has no hash-only switch.

## What `verify` checks

| check | fails when |
|-------|-----------|
| `receipt` | the receipt was edited (its own SHA-256 no longer matches) |
| `result` | hashed result fields differ from the receipt; top-level `provenance` and `timestamp` are excluded from this result hash |
| `inputs` | the data supplied (or embedded) does not hash to the recorded SHA-256 |
| `recompute` | re-running the recorded test, parameters and seed changes comparable fields; `differences` names them. Comparison excludes top-level provenance/timestamps and caller-format fields `coercion`/`none_as_nan` in input integrity |

Library-version drift is listed under `warnings`. Warnings alone do not change
`verified`; the four check statuses determine that result.

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

## Owning implementation and behavior checks

Native checks: `scitex_stats/_verify.py`. MCP translation and worker delegation:
`scitex_stats/_mcp/_handlers/_verify.py`. Behavioral controls, including source
results, tampering, files, skipped recomputation and transport/default mapping:
`tests/scitex_stats/test__verify.py` and
`tests/integration/test_verify_python_mcp.py`.
