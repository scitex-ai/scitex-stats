#!/usr/bin/env python3
# File: src/scitex_stats/_cli/_integrations.py
"""Optional scitex-dev integrations wired onto the root Click group.

Split out of ``_cli/__init__.py`` to keep that module under the repo's
512-line file-size limit. Both integrations are best-effort: scitex-dev
being absent, or older than expected, must never break scitex-stats's own
CLI.
"""

from __future__ import annotations


def attach_scitex_dev_integrations(main) -> None:
    """Attach shell-completion leaves + the optional docs subcommand.

    Called once, at import time, from ``_cli/__init__.py`` after ``main``
    and all of its own subcommands/groups are fully defined.
    """
    # Fleet standard completion drop-in v1: `completion install` writes the
    # click-generated script to $SCITEX_DIR/stats/runtime/completion/
    # scitex-stats atomically (never touches ~/.bashrc / ~/.zshrc).
    # Owns the `completion` name, so scitex-dev's rc-appending variant must
    # NOT be attached (it would collide on that name and reintroduce the
    # rc-edit path this contract deletes).
    from ._completion import register_completion_commands

    register_completion_commands(main)

    # Optional docs/skills subcommands from scitex-dev. scitex-dev exposes
    # argparse-compatible registration functions; only wire in the Click
    # variant when available. Otherwise skip silently — the docs/skills
    # subcommands are non-essential and the canonical API is `scitex-dev`.
    try:
        from scitex_dev.cli import (  # noqa: F401
            register_docs_subcommand,
            register_skills_subcommand,
        )

        try:
            from scitex_dev.cli import (  # type: ignore
                register_docs_click_command,
                register_skills_click_command,  # noqa: F401
            )
        except ImportError:
            return

        register_docs_click_command(main, package="scitex-stats")
        # Skills group is owned locally (skills_group.py) — do not override.
    except ImportError:
        pass


# EOF
