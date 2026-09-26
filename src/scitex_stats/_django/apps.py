#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django AppConfig for the scitex-stats Statistics app.

Hard-imports the SDK base on purpose (same ruling that drove scitex-scholar
and scitex-writer): a ``try/except ImportError: use django.apps.AppConfig``
fallback would silently STOP being a scitex-app the moment scitex-app is
missing, so every SDK contract evaporates while everything downstream
believes it is still in force. ``scitex-app`` is a REQUIRED member of the
``server`` extra, so a missing one is a broken install that must fail where
the cause is legible.

The label is ``stats_calculator`` (not ``stats`` / ``scitex_stats``): it is a
self-contained, collision-resistant identifier for the Django app registry
should the hub ever co-mount this with an unrelated app under a similar name.
"""

from scitex_app._django import ScitexAppConfig


class StatsCalculatorConfig(ScitexAppConfig):
    name = "scitex_stats._django"
    label = "stats_calculator"
    verbose_name = "SciTeX Statistics"

    def ready(self) -> None:  # noqa: D401 - parity with sibling apps
        super().ready()


# EOF
