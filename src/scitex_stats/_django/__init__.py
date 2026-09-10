#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django app exposing the scitex-stats Statistics calculator GUI.

Mirrors the scitex_scholar/_django and figrecipe/_django pattern so a single
canonical implementation drives the standalone GUI (`scitex-stats gui`) and
the scitex-hub mount alike. Stats has no per-invocation project/working-dir
concept -- it is a self-contained calculator that operates on the data the
caller sends to its API.

The heavy lifting lives in the `scitex_stats` common package; this app is a
thin UI over it (compass §12 L451/#210).
"""

default_app_config = "scitex_stats._django.apps.StatsCalculatorConfig"

# EOF
