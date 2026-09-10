#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone local-dev launcher for the Statistics GUI.

Delegates to `scitex_app.embed.run_standalone`, which pre-wires scitex-ui
static assets + the workspace shell so the standalone server looks like
scitex.ai/apps/stats. scitex-app is a HARD dependency of the `server`
extra: there is no bare-Django fallback (a fallback that silently drops
the shell AND the ALLOWED_HOSTS derivation is a second, quieter way to
break).

Cloud deployments do NOT use this -- they mount
`scitex_stats._django.urls` into their own Django project.

Stats has no per-invocation project / working-dir concept of its own, so
`run()` takes no `project_dir`; the app just operates on whatever data the
caller passes to the API.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# The single source of truth for the stats GUI port; the CLI imports it from
# here rather than restating the literal (so the launcher and the CLI cannot
# drift apart). DEFAULT_PORT is a bare constant on purpose: importing it must
# NOT require scitex-app, so the base CLI (which reads it to register the
# `gui` group) works without the [server] extra.
#
# 31299 -- the fixed scitex-stats slot in the ecosystem 3129X standalone-GUI
# port block. scholar owns 31297, writer owns 31298 (verified against the
# installed peers); 31299 is the next free slot and avoids the collision a
# naive "31297/31298" guess would cause with writer.
DEFAULT_PORT = 31299


def _require_sdk():
    """Import the scitex-app SDK, or exit with the install hint.

    Only `serve`/`open` actually need the SDK; the import is deferred so a
    base install (no [server]) can still import this module and register the
    `gui` CLI group without it.
    """
    try:
        from scitex_app import hosts_to_allow
        from scitex_app.embed import run_standalone
    except ImportError:
        print(
            "The Statistics GUI requires the [server] extra (scitex-app, "
            "scitex-ui, django). Install it with:\n"
            "  pip install 'scitex-stats[server]'",
            file=sys.stderr,
        )
        sys.exit(1)
    return hosts_to_allow, run_standalone


def run(
    port: int = DEFAULT_PORT,
    host: str = "127.0.0.1",
    open_browser: bool = True,
    desktop: bool = False,
    hot_reload: bool = False,
    working_dir: Optional[str] = None,
) -> None:
    """Launch the Django Statistics GUI server locally on exactly ``port``.

    Runs through `scitex_app.embed.run_standalone` (the full workspace shell
    from scitex-ui). No fallback: scitex-app is required. The requested port
    is bound as given: when it is already in use the server fails instead of
    drifting to the next free port.
    """
    # Serving on a non-loopback address requires that address in
    # ALLOWED_HOSTS, or Django answers 400 to every request while the banner
    # still prints a URL that looks fine. Binding to an address IS the
    # statement that you intend to be reached on it, so contribute it rather
    # than making the caller set an env var to permit what they already
    # asked for. settings.py reads this variable and APPENDS, so an
    # explicitly configured list survives alongside the bind address.
    hosts_to_allow, run_standalone = _require_sdk()
    _contributed = hosts_to_allow(host)
    if _contributed:
        _configured = os.environ.get("SCITEX_STATS_ALLOWED_HOSTS", "")
        _hosts = [h.strip() for h in _configured.split(",") if h.strip()]
        for _h in _contributed:
            if _h not in _hosts:
                _hosts.append(_h)
        os.environ["SCITEX_STATS_ALLOWED_HOSTS"] = ",".join(_hosts)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scitex_stats._django.settings")

    print(f"SciTeX Statistics GUI: http://{host}:{port}")
    print("Press Ctrl+C to stop")

    import django

    django.setup()

    from django.core.management import call_command

    call_command("migrate", "--run-syncdb", verbosity=0)

    run_standalone(
        app_module="scitex_stats._django",
        port=port,
        host=host,
        open_browser=open_browser,
        hot_reload=hot_reload,
        desktop=desktop,
        working_dir=working_dir,
    )


# EOF
