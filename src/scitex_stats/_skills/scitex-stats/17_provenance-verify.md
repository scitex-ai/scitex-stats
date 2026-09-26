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
