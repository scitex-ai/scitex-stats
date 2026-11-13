---
description: |
  [TOPIC] Django App Env Vars
  [DETAILS] SCITEX_STATS_* variables read by the standalone Statistics app
  (scitex_stats._django) — the Django server launcher and settings.
tags: [scitex-stats-env-vars, scitex-stats]
---


# scitex-stats — Django App Environment Variables

SK-111: these variables are read via `os.environ` in `scitex_stats._django`
(the standalone Statistics app / `scitex-stats gui`). They are distinct from
the CLI destination and completion variables in [14_env-vars.md](14_env-vars.md).
Hub deployments supply their own Django settings instead of loading this module.

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_STATS_DJANGO_SECRET` | Django `SECRET_KEY` for the standalone server. When unset, a random key is generated per process (fine for local dev; set it for reproducible sessions across restarts). | unset (random) | str |
| `SCITEX_STATS_ALLOWED_HOSTS` | Comma-separated extra `ALLOWED_HOSTS` entries for the standalone server (reverse-proxy DNS name, MagicDNS name, etc.). Appended to the default host allowlist in `settings.py`; the bind address is auto-contributed by `_server.py`. | unset | str (csv) |
| `SCITEX_STATS_APP_MODE` | Browser-tab application mode; takes precedence over the deprecated `SCITEX_APP_MODE` fallback, which emits a warning when used. | `standalone` | str |
| `SCITEX_STATS_PROJECTS_ROOT` | Local-folder project root used by the standalone project provider. | `~/.scitex/stats/projects/` | str (path) |

## Related

- `DJANGO_DEBUG` (fleet convention, read by `settings.py`) — `true` widens
  `ALLOWED_HOSTS` to `*` and enables static serving via runserver; `false`
  (the default) uses the default host allowlist plus configured extra hosts.
  Fleet-wide, not scitex-stats-specific.
- `SCITEX_STATS_CONFIG` is not currently consumed as a package-wide YAML
  configuration path; see [14_env-vars.md](14_env-vars.md).

## Notes

- The app has **no models**, so no database URL is required
  (`DATABASES={}` in `scitex_stats._django.settings`).
- The standalone port defaults to `31299`; `gui serve --port` and
  `gui open --port` override it (see `scitex_stats._django._server.DEFAULT_PORT`),
  the scitex-stats slot in the ecosystem 3129X block (scholar 31297, writer 31298).

## Audit

```bash
rg -n 'SCITEX_STATS_|DJANGO_DEBUG' src/scitex_stats/_django/
```

## Source and behavioral checks

`_django/settings.py`, `_django/_projects.py::projects_root` and
`_env.py::resolve_env` define these values. Existing owning controls include
`tests/scitex_stats/_django/test_settings.py` and
`tests/scitex_stats/_django/test__projects.py`. CLI port options are defined
in `_cli/gui.py`; a help or settings check does not prove a running GUI.
