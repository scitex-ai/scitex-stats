---
description: |
  [TOPIC] Environment variables
  [DETAILS] CLI skill destinations and completion paths actually read by Stats.
tags: [scitex-stats-env-vars, scitex-stats]
---

# scitex-stats — Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `SCITEX_STATS_SKILLS_DIR` | Base destination for `skills install`; an explicit `--directory` takes precedence. | `~/.scitex/dev/skills/` |
| `SCITEX_DIR` | Base path for the completion drop-in under `stats/runtime/completion/`. This does not relocate every Stats runtime path. | `~/.scitex/` |

Importing `scitex_stats` calls `scitex_config.PriorityConfig.load_dotenv`.
This loads environment values; it is not a package-wide YAML defaults loader.
The CLI does not currently consume `SCITEX_STATS_CONFIG`,
`./config.yaml` or `~/.scitex/stats/config.yaml` as command defaults.

`_SCITEX_LOGGING_AVAILABLE` is a Python boolean reflecting whether
`scitex_logging` imported successfully; it is not an environment variable.

Standalone GUI variables are documented in [20_env-vars.md](20_env-vars.md).

## Source and behavioral checks

- `_cli/skills_group.py::_default_skills_base` and `skills_install` own
  destination precedence. See `tests/scitex_stats/_cli/test_skills_group.py`
  and `tests/integration/test_skills_install_preservation.py`.
- `_cli/_completion.py` owns the completion path. Its existing controls are in
  `tests/scitex_stats/_cli/test__completion.py`.
- `__init__.py` owns the dotenv call; `_logging.py` owns logger detection.
  These source references do not establish every dependent package's behavior.
