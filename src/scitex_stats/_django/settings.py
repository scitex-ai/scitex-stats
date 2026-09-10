#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal standalone Django settings for `scitex-stats gui`.

Used only by the standalone launcher; cloud (scitex-hub) deployments ignore
this module and mount `scitex_stats._django.urls` under their own prefix.

Mirrors the scitex_scholar._django.settings pattern. No models, so
DATABASES is empty and there is nothing to migrate (the launcher still runs
`migrate --run-syncdb` for parity with the sibling apps).
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Fleet env-var convention is SCITEX_STATS_<X>.
SECRET_KEY = os.environ.get("SCITEX_STATS_DJANGO_SECRET") or secrets.token_urlsafe(32)
# DEBUG defaults to FALSE (fleet convention, 2026-09-02): the permissive
# ALLOWED_HOSTS="*" branch is opt-in, not the default.
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "testserver"]
    _extra_hosts = os.environ.get("SCITEX_STATS_ALLOWED_HOSTS", "")
    ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(",") if h.strip()]

# "hub" | "standalone" -- the browser tab alone must distinguish the two
# (fleet convention; scitex-hub reads the same setting and defaults to "hub").
# These settings only boot the STANDALONE server, so standalone is the default.
SCITEX_APP_MODE = os.environ.get("SCITEX_APP_MODE", "standalone")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "scitex_stats._django.apps.StatsCalculatorConfig",
]

# scitex-ui supplies the shared workspace shell partial that stats.html
# extends. It is a REQUIRED member of the `server` extra, so this import is
# hard on purpose: a try/except would swallow a broken install and resurface
# it later as TemplateDoesNotExist pointing at scitex-ui's shell.
import scitex_ui  # noqa: F401

INSTALLED_APPS.append("scitex_ui")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "scitex_stats._django._standalone_urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

DATABASES = {}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

# EOF
