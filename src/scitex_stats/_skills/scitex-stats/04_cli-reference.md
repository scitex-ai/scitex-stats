---
description: |
  [TOPIC] CLI Reference
  [DETAILS] tests / mcp / python-api / skills / format-pvalue command surface.
tags: [scitex-stats-cli-reference, scitex-stats]
---


# CLI Reference

```bash
scitex-stats --help
scitex-stats --help-recursive   # full tree (root + every subcommand)
scitex-stats --version
```

Top-level groups: `tests`, `mcp`, `python-api`, `skills`. Top-level leaves:
`list-python-apis`, `format-pvalue`.

## tests — run / describe / recommend statistical tests

```bash
scitex-stats tests list                            # all 22 test names (aliases included)
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

## mcp — MCP server commands

```bash
scitex-stats mcp list-tools           # enumerate registered MCP tools
scitex-stats mcp doctor               # verify deps + tool count + CLI
scitex-stats mcp install              # Claude Desktop config snippet
scitex-stats mcp start                # stdio (default) — long-running
scitex-stats mcp start -t sse         # SSE for HTTP clients
scitex-stats mcp start --dry-run      # preview launch plan
```

Requires the `[mcp]` extra. `start` is mutating (long-running server) — use
`-y/--yes` to skip the confirmation prompt in scripts.

## python-api / list-python-apis — package introspection

```bash
scitex-stats python-api list scitex_stats
scitex-stats python-api list scitex_stats.correct --json
scitex-stats list-python-apis -v --max-depth 3
```

`list-python-apis` is a convenience alias for
`python-api list scitex_stats`.

## skills — bundled agent-facing skills

```bash
scitex-stats skills list
scitex-stats skills get 02_quick-start
scitex-stats skills install                  # symlink to ~/.scitex/dev/skills/
scitex-stats skills install --claude-symlink # also expose to ~/.claude/skills/scitex/
scitex-stats skills install --no-link --dest /tmp/skills
scitex-stats skills install --dry-run
```

## format-pvalue — p-value to significance stars

```bash
scitex-stats format-pvalue 0.001    # → ***
scitex-stats format-pvalue 0.5      # → ns
```

## Configuration precedence

Highest → lowest:

1. Explicit CLI flags
2. `./config.yaml` (project-local)
3. `$SCITEX_STATS_CONFIG` (path to a YAML file)
4. `~/.scitex/stats/config.yaml` (user-wide)
5. Built-in defaults

See [14_env-vars.md](14_env-vars.md) for the env vars `scitex-stats`
reads at runtime.
