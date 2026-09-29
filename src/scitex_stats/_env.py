#!/usr/bin/env python3
# File: src/scitex_stats/_env.py

"""Read scitex-stats environment variables under the fleet-prefixed name.

Every environment variable scitex-stats OWNS is spelled
``SCITEX_STATS_<X>``. Several call sites read a bare cross-package name
directly (notably ``SCITEX_APP_MODE``, owned by scitex-app), which PS-145
flags: one package must not read another package's user-state env var.
`resolve_env` closes that gap without breaking anyone who is currently
relying on the legacy spelling.

Precedence is canonical-first, and the legacy read is LOUD. A silent
fallback here would be the same defect in a new place: the user would keep
believing the documented name works, and the day the legacy name is removed
their setup breaks with no warning ever having been issued.

Mirrors ``scitex_scholar._utils._env`` (same fleet convention).
"""

from __future__ import annotations

import os
from typing import Sequence

import scitex_logging as slogging

logger = slogging.getLogger(__name__)

__all__ = ["resolve_env"]

_warned: set[str] = set()


def resolve_env(
    canonical: str,
    legacy: str | Sequence[str] | None = None,
    default: str | None = None,
) -> str | None:
    """Return the value of ``canonical``, falling back to ``legacy`` loudly.

    Parameters
    ----------
    canonical
        The ``SCITEX_STATS_*`` name. Always read first, and always wins
        when both are set — the documented name must be the one that works.
    legacy
        A pre-convention spelling still honoured for back-compat, or several
        of them in precedence order (the first one set wins). Using any of
        them emits a warning naming it and the canonical spelling, once per
        process per legacy name.
    default
        Returned when neither name is set.

    Returns
    -------
    str or None
        The resolved value, or ``default`` when neither variable is set.
    """
    value = os.environ.get(canonical)
    if value is not None:
        return value

    legacy_names = (legacy,) if isinstance(legacy, str) else tuple(legacy or ())
    for name in legacy_names:
        legacy_value = os.environ.get(name)
        if legacy_value is not None:
            if name not in _warned:
                _warned.add(name)
                logger.warning(
                    "%s is deprecated and will be removed; set %s instead. "
                    "Using the value from %s for now.",
                    name,
                    canonical,
                    name,
                )
            return legacy_value

    return default


# EOF
