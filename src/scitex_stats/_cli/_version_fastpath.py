#!/usr/bin/env python3
# File: src/scitex_stats/_cli/_version_fastpath.py
"""Fast-path a bare ``-V``/``--version`` CLI invocation.

Must run BEFORE any import in ``_cli/__init__.py`` that transitively pulls
in ``scitex_dev._cli`` (e.g. via ``attach_scitex_dev_integrations`` /
``attach_shell_completion``). scitex-dev's own ``_cli/__init__.py`` has an
identical fast-path: it inspects the process-wide ``sys.argv`` and, if it
looks like a bare ``-V``/``--version``, immediately prints *scitex-dev's
own* version and calls ``sys.exit(0)`` — as an IMPORT-TIME side effect,
with no way to tell whose CLI is actually running.

Without an equally early check here, running ``scitex-stats -V`` (or
``python -m scitex_stats -V``) would import ``scitex_dev._cli`` partway
through this package's own CLI import. That import sees the SAME
``sys.argv`` and hijacks the process: it prints ``scitex-dev X.Y.Z`` and
exits before scitex-stats's own ``click.version_option`` ever runs — the
observed bug (``scitex-stats --version`` printing ``scitex-dev 0.28.0``).

Deliberately narrow — any other combination (extra flags, a subcommand,
``--version --json``) is left alone and falls through to the real Click
group unchanged.
"""

from __future__ import annotations

import sys


def maybe_print_version_and_exit(argv: list) -> None:
    """Print scitex-stats's own version and exit iff ``argv`` is bare."""
    if argv not in (["--version"], ["-V"]):
        return

    from importlib.metadata import PackageNotFoundError, version

    try:
        v = version("scitex-stats")
    except PackageNotFoundError:
        v = "0.0.0+local"
    # `--version` output is machine-readable data transport (scripts parse
    # it), so it goes to stdout via sys.stdout.write, which PS-220 spares.
    sys.stdout.write(f"scitex-stats, version {v}\n")
    raise SystemExit(0)


# EOF
