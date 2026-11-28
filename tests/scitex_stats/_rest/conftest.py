#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/conftest.py
"""Serve every test in this package through the host of ``_host``."""

import pytest

pytest.importorskip("scitex_sdk.app.api_tier")


@pytest.fixture(autouse=True)
def _served():
    # Imported here, not at conftest load: pytest loads this file before it
    # collects any module, and _host configures Django if nobody has yet.
    from django.core.cache import caches
    from django.test import override_settings

    from . import _host

    with override_settings(**_host.HOOKS):
        caches["default"].clear()
        yield


# EOF
