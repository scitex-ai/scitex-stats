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

# scitex-app ships `scitex_app/app_shell.html`, the base template stats.html
# EXTENDS, and its templatetags provide the workbench directives inside it.
# APP_DIRS only searches installed apps, so leaving scitex_app out of
# INSTALLED_APPS made every standalone page 500 with
# `TemplateDoesNotExist: scitex_app/app_shell.html` — invisible to the app
# tests, which configure their own INSTALLED_APPS (that list has it).
import scitex_app  # noqa: F401,E402

INSTALLED_APPS.append("scitex_app")

from scitex_app.i18n import i18n_settings, with_locale_middleware  # noqa: E402

MIDDLEWARE = with_locale_middleware(
    [
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.common.CommonMiddleware",
        # CSRF on writes: saving an artifact into a project is a state-changing
        # POST, so the token the page carries must be verified. Without this
        # middleware the marker in the template is decorative.
        "django.middleware.csrf.CsrfViewMiddleware",
    ]
)
globals().update(i18n_settings())

ROOT_URLCONF = "scitex_stats._django._standalone_urls"

# Project scope (SDK contract, scitex-ui): the app renders the picker, the HOST
# supplies the project list. A hub mount overrides both settings with its own
# provider; standalone falls back to local folders (see _projects.py). The
# dotted path must name a CLASS: `host_project_provider()` imports it and calls
# a class, while a factory FUNCTION is mistaken for an already-built instance.
SCITEX_PROJECT_PROVIDER = "scitex_stats._django._projects.StandaloneProjectProvider"
# A URL NAME, not a path: reverse() resolves it against the active urlconf, so
# the same setting works standalone ("/api/project-scope") and under a hub
# prefix. It must be the APPLICATION-namespaced name — urls.py declares
# `app_name = "stats"`, and Django then exposes the name only as
# "stats:api_project_scope" (the bare name raises NoReverseMatch, which the SDK
# guard turns into "no picker" silently — measured, not assumed).
SCITEX_PROJECT_PROVIDER_URL = "stats:api_project_scope"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                # The app declares "scope": "project" in its manifest, so the
                # templates need `app_scope` to decide whether the shared
                # project picker renders (SDK contract, scitex-app).
                "scitex_app._app_scope.app_scope_context",
            ],
        },
    },
]

DATABASES = {}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

# EOF
