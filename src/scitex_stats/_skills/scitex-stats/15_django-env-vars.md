---
description: |
  [TOPIC] Django App Env Vars
  [DETAILS] SCITEX_STATS_* variables read by the standalone Statistics app
  (scitex_stats._django) — the Django server launcher and settings.
tags: [scitex-stats-django-env-vars, scitex-stats]
---


# scitex-stats — Django App Environment Variables

SK-111: these variables are read via `os.environ` in `scitex_stats._django`
(the standalone Statistics app / `scitex-stats gui`). They are distinct from
the runtime config vars in `14_env-vars.md` (e.g. `SCITEX_STATS_CONFIG`),
which the core package reads for configuration, not for the web server.

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_STATS_DJANGO_SECRET` | Django `SECRET_KEY` for the standalone server. When unset, a random key is generated per process (fine for local dev; set it for reproducible sessions across restarts). | unset (random) | str |
| `SCITEX_STATS_ALLOWED_HOSTS` | Comma-separated extra `ALLOWED_HOSTS` entries for the standalone server (reverse-proxy DNS name, MagicDNS name, etc.). Appended to the loopback defaults in `settings.py`; the bind address is auto-contributed by `_server.py`. | unset | str (csv) |

## Related (not read by this app)

- `DJANGO_DEBUG` (fleet convention, read by `settings.py`) — `true` widens
  `ALLOWED_HOSTS` to `*` and enables static serving via runserver; `false`
  (the default) is loopback-only. Fleet-wide, not scitex-stats-specific.
- `SCITEX_STATS_CONFIG` — see `14_env-vars.md`; the core package's YAML
  config path, unrelated to the Django app.

## Notes

- The app has **no models**, so no database URL is required
  (`DATABASES={}` in `scitex_stats._django.settings`).
- The standalone port is fixed at `31299` (see `scitex_stats._django._server.DEFAULT_PORT`),
  the scitex-stats slot in the ecosystem 3129X block (scholar 31297, writer 31298).

## Audit

```bash
grep -rhoE 'SCITEX_STATS_[A-Z0-9_]+' src/scitex_stats/_django/ | sort -u
```
