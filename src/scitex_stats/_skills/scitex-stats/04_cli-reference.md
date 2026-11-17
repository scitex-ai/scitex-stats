---
description: |
  [TOPIC] CLI Reference
  [DETAILS] Current tests, verification, report, GUI, MCP, skills and introspection commands.
tags: [scitex-stats-cli-reference, scitex-stats]
---


# CLI Reference

```bash
scitex-stats --help
scitex-stats --help-recursive   # full tree (root + every subcommand)
scitex-stats --version
```

Base groups: `tests`, `mcp`, `python-api`, `skills`, `gui`, `completion`.
Top-level leaves: `list-python-apis`, `format-pvalue`, `validate-apa`,
`verify`, `generate-report`, `print-shell-completion`, `install-shell-completion`.
Optional Dev integrations can add commands when their registration API is
available. Use `--help-recursive` for the installed full tree;
the sections below cover common entry points.

## tests — run / describe / recommend statistical tests

```bash
scitex-stats tests list                            # registered test names
scitex-stats tests execute ttest_ind data.csv \
    --x group_a --y group_b
scitex-stats tests execute anova data.csv --groups col1,col2,col3
scitex-stats tests execute pearson data.csv --x x --y y
scitex-stats tests describe data.csv -c group_a
scitex-stats tests recommend --n-groups 2 --sample-sizes 30,28
```

`--alternative {two-sided,greater,less}` and `--popmean FLOAT` available
where the underlying test supports them. All commands accept
`--json/--no-json` (default JSON).

For data-based design checks and recommendations, use:

```bash
scitex-stats tests check-applicability data.csv --groups group_a,group_b --design independent
scitex-stats tests recommend-test data.csv --groups group_a,group_b --design independent
scitex-stats tests execute-all data.csv --groups group_a,group_b --design independent
```

These `--design` choices differ from `tests recommend`, which describes a
study using `--n-groups`, `--sample-sizes` and `--design {between,within,mixed}`.

## Verification, reporting and GUI

```bash
scitex-stats verify result.json
scitex-stats verify report.json --source-result original-result.json
scitex-stats validate-apa --help
scitex-stats generate-report --help
scitex-stats gui --help
```

`verify` exits 0 only when verified, 1 otherwise. Full reports need their
original source result for recomputation; see [17_provenance-verify.md](17_provenance-verify.md).
For reproducible CSV execution/verification, see [12_cli-reference.md](12_cli-reference.md).
GUI help describes options; it does not establish that a GUI is running.

## mcp — MCP server commands

```bash
scitex-stats mcp list-tools           # enumerate registered MCP tools
scitex-stats mcp doctor               # verify deps + tool count + CLI
scitex-stats mcp install              # Claude Desktop config snippet
scitex-stats mcp start                # stdio (default) — long-running
scitex-stats mcp start -t sse         # SSE for HTTP clients
scitex-stats mcp start --dry-run      # preview launch plan
```

MCP support is included in the base install. `start` launches a long-running
server; use `--dry-run` to inspect its launch plan.

## python-api / list-python-apis — package introspection

```bash
scitex-stats python-api list scitex_stats
scitex-stats python-api list scitex_stats.correct --json
scitex-stats list-python-apis -v --max-depth 3
```

`list-python-apis` is a convenience alias for
`python-api list scitex_stats`.
Discovery descends into the requested module's namespace. Explicitly exported
third-party callables and modules remain listed, but dependency module internals
are not recursively enumerated. Request a dependency directly to inspect its API.


## skills — bundled agent-facing skills

```bash
scitex-stats skills list
scitex-stats skills get 02_quick-start
scitex-stats skills install                  # symlink to ~/.scitex/dev/skills/
scitex-stats skills install --directory /path/to/agent/skills
scitex-stats skills install --no-link --directory /path/to/agent/skills
scitex-stats skills install --dry-run
```

## format-pvalue — p-value to significance stars

```bash
scitex-stats format-pvalue 0.001    # → **
scitex-stats format-pvalue 0.5      # → ns
```

`format-pvalue` calls the public formatter and uses strict default thresholds.
The legacy formatter has different exact-threshold symbols; see [27_star-boundaries.md](27_star-boundaries.md).

## Shell completion

```bash
scitex-stats completion --help
scitex-stats print-shell-completion --help
scitex-stats install-shell-completion --help
```

The completion group is owned by `_cli/_completion.py` and registered through
`_cli/_integrations.py`; see [14_env-vars.md](14_env-vars.md) for its path setting.

## Configuration

Commands use their explicit arguments and built-in defaults. A package-wide
YAML configuration loader is not currently wired into the CLI:
`./config.yaml`, `SCITEX_STATS_CONFIG` and
`~/.scitex/stats/config.yaml` do not supply command defaults.

For skills installation, `--directory` takes precedence over
`SCITEX_STATS_SKILLS_DIR`; otherwise the destination is
`~/.scitex/dev/skills/`. The shared installer protects caller-owned files.
The optional `--claude-symlink` compatibility flag remains available.

See [14_env-vars.md](14_env-vars.md) for the env vars `scitex-stats`
reads at runtime.

## Owning source and checks

`_cli/__init__.py` registers the root commands; `_cli/tests_group.py` defines
statistical argument shapes and `_cli/stats.py` reads/selects data and executes
the owning API. Existing controls include `tests/scitex_stats/_cli/test_tests_group.py`,
`test_stats.py`, `test___init__.py`, `test_recommend.py` and
`tests/scitex_stats/test__verify.py`. Runtime help and installed command
behavior must be checked separately from this reference's syntax.
