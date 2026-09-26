#!/usr/bin/env python3
# File: src/scitex_stats/_cli/gui.py

"""``gui`` command group for the scitex-stats CLI (the Statistics app).

Follows the ecosystem-wide canonical shape (scitex-dev skill
``03_interface/02_cli/19_gui-commands.md``): every browser-based surface a
package ships mounts under one group, ``gui``, with exactly four verbs --
``open``, ``serve``, ``status``, ``stop``.

Lifecycle bookkeeping (pid/port/host state file, liveness, idempotent stop,
orphaned-holder identification) is delegated to ``scitex_app.embed`` rather
than reimplemented here (writer/figrecipe/scholar all did this before it was
generalized). Concretely mirrors the fleet's CORRECTED conventions, learned
from all three:

  * ``serve`` -- foreground, headless (no browser). ``open`` auto-serves in a
    DETACHED background process, capturing stdout/stderr to ``gui.log`` (a
    sibling of the state file), polls up to 30s for the state file, and on
    failure SURFACES the log path rather than blindly opening a dead URL
    (figrecipe ``_autoserve`` / ``gui_open``).
  * ``stop`` -- confirmation-gated: ``--yes``/``-y`` or ``--dry-run``
    (scholar/figrecipe fixed a bare stop that killed a server with no warning).
  * ``status`` -- ``--json`` for machine-readable output.

Default port 31299 (the fixed scitex-stats slot in the ecosystem 3129X
standalone-GUI port block: scholar=31297, writer=31298, stats=31299). It is
imported from ``_django._server`` so the launcher and the CLI cannot drift
apart.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Optional

import click

from .._django._server import DEFAULT_PORT

DEFAULT_HOST = "127.0.0.1"
PACKAGE = "scitex-stats"


def _embed():
    """Return ``scitex_app.embed``, or exit with an actionable message.

    Only the import is guarded: an ImportError raised from INSIDE scitex-app
    is a real bug, not an absent optional dependency, and must not be
    reported as "install scitex-app".
    """
    try:
        import scitex_app.embed as embed
    except ImportError:
        click.secho(
            "scitex-app is not installed -- the GUI lifecycle (serve/status/"
            "stop) is delegated to it. Install it with:\n"
            "  pip install 'scitex-stats[server]'  (needs scitex-app >= 0.11.0)",
            fg="red",
            err=True,
        )
        sys.exit(1)
    return embed


def _state_path():
    """The GUI runtime-state path the SDK derives for this package."""
    embed = _embed()
    return embed._gr.state_path(PACKAGE)


def _log_path():
    """``gui.log``, a sibling of the state file (figrecipe convention)."""
    return _state_path().with_name("gui.log")


def _run_server(port: int, host: str, hot_reload: bool, desktop: bool) -> None:
    """Foreground, blocking server (no browser -- ``open`` owns that)."""
    from .._django._server import run

    run(port=port, host=host, open_browser=False, desktop=desktop, hot_reload=hot_reload)


def _console_script() -> str:
    """The installed ``scitex-stats`` console script (PATH, then co-located).

    The base CLI (which registers this group) must work without the [server]
    extra, so we resolve the executable lazily here.
    """
    import shutil

    return shutil.which("scitex-stats") or os.path.join(
        os.path.dirname(sys.executable), "scitex-stats"
    )


@click.group()
def gui() -> None:
    """The Statistics calculator GUI (standalone workspace app)."""


@gui.command("serve")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int)
@click.option("--host", default=DEFAULT_HOST, show_default=True)
@click.option(
    "--force", is_flag=True,
    help="Stop a previous instance of ours -- recorded OR orphaned -- then serve here.",
)
@click.option("--hot-reload", is_flag=True)
@click.option("--desktop", is_flag=True, help="Launch as a native desktop window (pywebview).")
def gui_serve(port: int, host: str, force: bool, hot_reload: bool, desktop: bool) -> None:
    """Run the Statistics GUI server in the foreground (headless; Ctrl-C to stop).

    \b
    Example:
      $ scitex-stats gui serve --port 31299
      $ scitex-stats gui serve --force
    """
    from functools import partial

    code = _embed().serve_gui(
        package=PACKAGE,
        project_dir=os.getcwd(),
        port=port,
        host=host,
        force=force,
        run_server=partial(_run_server, port=port, host=host, hot_reload=hot_reload, desktop=desktop),
        state_path=_state_path(),
    )
    sys.exit(code)


def _autoserve(port: int, host: str) -> dict:
    """Spawn a detached ``gui serve`` capturing output to ``gui.log``, then
    wait up to 30s for the SDK state file (figrecipe ``_autoserve``)."""
    log_path = _log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_console_script(), "gui", "serve", "--port", str(port), "--host", host]
    with open(log_path, "ab") as log:
        subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)

    embed = _embed()
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        current = embed.gui_status(PACKAGE, state_path=_state_path())
        if current.get("running"):
            return current
        time.sleep(0.3)
    return {"running": False, "log": str(log_path)}


@gui.command("open")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int)
@click.option("--host", default=DEFAULT_HOST, show_default=True)
@click.option("--no-browser", is_flag=True, default=False, help="Don't open the browser.")
@click.option("--desktop", is_flag=True, help="Launch as a native desktop window (pywebview).")
def gui_open(port: int, host: str, no_browser: bool, desktop: bool) -> None:
    """Open the Statistics GUI in a browser, auto-serving if not running.

    \b
    Example:
      $ scitex-stats gui open
    """
    import webbrowser

    embed = _embed()
    current = embed.gui_status(PACKAGE, state_path=_state_path())
    if current.get("running"):
        click.echo(f"Already running at {current['url']} -- opening browser.")
        if not no_browser:
            webbrowser.open(current["url"])
        return

    holder = embed.gui_port_holder(port, PACKAGE)
    if holder.in_use and not holder.ours:
        click.secho(
            f"Refusing to start: {host}:{port} is held by a different process "
            f"(pid {holder.pid}, {holder.name}). Free it, or pass --port.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    if desktop:
        _run_server(port, host, hot_reload=False, desktop=True)
        return

    click.echo(f"Starting Statistics GUI on {host}:{port} ...")
    current = _autoserve(port, host)
    if not current.get("running"):
        click.secho(
            f"Error: server did not come up within 30s; see {current.get('log')}",
            fg="red",
            err=True,
        )
        sys.exit(1)
    url = current["url"]
    if not no_browser:
        webbrowser.open(url)
    click.echo(f"Statistics GUI running at {url}.")


@gui.command("status")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def gui_status(as_json: bool) -> None:
    """Report whether the Statistics GUI server is running.

    \b
    Example:
      $ scitex-stats gui status
    """
    import json as _json

    state = _embed().gui_status(PACKAGE, state_path=_state_path())
    if as_json:
        click.echo(_json.dumps(state, indent=2))
        return
    if state.get("running"):
        click.echo(f"running at {state['url']} (pid {state.get('pid')})")
    else:
        click.echo(f"not running (expected on {DEFAULT_HOST}:{DEFAULT_PORT})")


@gui.command("stop")
@click.option("--dry-run", is_flag=True, help="Print what would happen without stopping.")
@click.option("--yes", "-y", is_flag=True, help="Confirm stopping the server.")
def gui_stop(dry_run: bool, yes: bool) -> None:
    """Stop the running Statistics GUI server.

    \b
    Example:
      $ scitex-stats gui stop -y
      $ scitex-stats gui stop --dry-run
    """
    embed = _embed()
    state_path = _state_path()
    current = embed.gui_status(PACKAGE, state_path=state_path)
    if not current.get("running"):
        click.echo("Not running.")
        return
    if dry_run:
        click.echo(f"DRY RUN -- would stop pid {current.get('pid')} ({current.get('url')})")
        return
    if not yes:
        click.secho(
            "Refusing to stop without --yes/-y (or use --dry-run to preview).",
            fg="yellow",
            err=True,
        )
        sys.exit(1)
    result = embed.gui_stop(PACKAGE, state_path=state_path)
    if result.get("stopped"):
        click.echo(f"Stopped (pid {result.get('pid')}).")
    else:
        click.secho(f"Failed to stop: {result.get('error')}", fg="red", err=True)
        sys.exit(1)


# EOF
