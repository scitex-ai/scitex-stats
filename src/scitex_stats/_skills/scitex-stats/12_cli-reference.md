---
description: |
  [TOPIC] CLI workflows
  [DETAILS] Reproducible CSV testing, descriptive summaries, recommendations and provenance verification using current commands.
tags: [scitex-stats-cli-reference, scitex-stats]
---

# CLI workflows

The command inventory is in [04_cli-reference.md](04_cli-reference.md).
Use `scitex-stats --help-recursive` for the installed command tree.

## CSV tests and verification

Save this synthetic fixture as `data.csv`:

```csv
group_a,group_b,group_c
1,3,2
2,5,4
4,7,6
5,9,8
```

Run a named test using positional input and explicit columns, then verify its
saved result against its receipt and embedded inputs:

```bash
scitex-stats tests execute ttest_ind data.csv --x group_a --y group_b > ttest.json
scitex-stats verify ttest.json
scitex-stats tests execute anova data.csv --groups group_a,group_b,group_c > anova.json
scitex-stats verify anova.json
```

Both verification commands should report `verified: true` for these unedited
results. A failed verification exits 1. For full-report results, supply the
original source result too; see [17_provenance-verify.md](17_provenance-verify.md).

```bash
scitex-stats tests describe data.csv -c group_a --funcs mean,median
scitex-stats tests recommend --n-groups 2 --sample-sizes 4,4
```

The selected `group_a` has mean 3 and median 3. `tests recommend` uses the stated
study design; it does not read this CSV. For data-based recommendations:

```bash
scitex-stats tests recommend-test data.csv --groups group_a,group_b --design independent
```

Review the returned rationale and design assumptions when selecting a test.

## Installed tools and bundled guides

```bash
scitex-stats mcp list-tools -vv
scitex-stats mcp start --dry-run
scitex-stats mcp start --transport sse --dry-run
scitex-stats skills list
scitex-stats skills get 04_cli-reference
scitex-stats skills get 17_provenance-verify
```

The two `--dry-run` commands preview launch plans without starting a server.
The supported CLI transport values are `stdio` and `sse`; actual server health
and client connectivity require their own checks. Skill retrieval reads the
owning package's bundled guides.

## Owning source and behavior controls

`_cli/tests_group.py` owns command/option names; `_cli/stats.py` owns file
loading, column selection and analysis dispatch; `_cli/verify.py` owns
verification exit status. Existing controls are
`tests/scitex_stats/_cli/test_tests_group.py`, `test_stats.py`,
`test_recommend.py` and `tests/scitex_stats/test__verify.py`.
The CSV workflow is a synthetic reproducibility example, not acceptance of
every data format, study design, hosted GUI or statistical assumption.
