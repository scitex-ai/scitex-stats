#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/_host.py
"""A minimal SciTeX host serving the stats plugin through the real SDK path.

``urlpatterns`` is the SDK's ``api_urlpatterns`` over the installed-style
reference to ``scitex_stats._rest:PLUGIN``; ``HOOKS`` are the host settings
(caller resolution, public tier, idempotency store) a test overrides with.
"""

import json
from types import SimpleNamespace

import django
from django.conf import settings

if not settings.configured:
    # The same apps the _django suite boots with (plus auth), so whichever
    # test module configures Django first, both suites can run in one process.
    settings.configure(
        SECRET_KEY="scitex-stats-rest-tests",
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.staticfiles",
            "scitex_sdk.app",
            "scitex_stats._django.apps.StatsCalculatorConfig",
            "scitex_sdk.ui",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": ["django.template.context_processors.request"]
                },
            }
        ],
        DATABASES={},
        STATIC_URL="/static/",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        SCITEX_PROJECT_PROVIDER_URL="/api/project-scope",
    )
    django.setup()

from django.test import Client  # noqa: E402
from scitex_sdk.app.api_exec import ApiCaller  # noqa: E402
from scitex_sdk.app.api_plugin import ApiPluginRef  # noqa: E402
from scitex_sdk.app.api_serve import api_urlpatterns  # noqa: E402

MEMBER = "member-key"

#: The first-phase public set of API contract v1 §12.4, stats entries.
TIER = {
    "stats.tests.list": {"public": True, "limits": "light"},
    "stats.tests.get": {"public": True, "limits": "light"},
    "stats.tests.recommend": {"public": True, "limits": "light"},
    "stats.tests.run": {"public": True, "limits": "stats-inline"},
    "stats.descriptives.run": {"public": True, "limits": "stats-inline"},
    "stats.effect-sizes.run": {"public": True, "limits": "stats-inline"},
    "stats.power-analyses.run": {"public": True, "limits": "stats-inline"},
    "stats.corrections.run": {"public": True, "limits": "stats-inline"},
    "stats.bootstrap-cis.run": {"public": True, "limits": "stats-bootstrap"},
}


def caller(request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token != MEMBER:
        return None
    user = SimpleNamespace(username=token, pk=token, is_authenticated=True)
    return ApiCaller(
        user=user, scopes=("*",), via="token", token_id=token, tier="member"
    )


HOOKS = dict(
    ROOT_URLCONF=__name__,
    SCITEX_API_CALLER=f"{__name__}.caller",
    SCITEX_API_PUBLIC_TIER=TIER,
    SCITEX_API_IDEMPOTENCY_STORE="scitex_sdk.app.api_serve.InMemoryIdempotencyStore",
    SCITEX_API_RATE_LIMITER=None,
    SCITEX_API_METER=None,
    DATA_UPLOAD_MAX_MEMORY_SIZE=None,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)

REF = ApiPluginRef(name="stats", target="scitex_stats._rest:PLUGIN", distribution="")
urlpatterns = api_urlpatterns([REF])


def post(path, body, token=None, raw=None):
    """POST ``body`` (or the ``raw`` text) as JSON, anonymous unless ``token``."""
    headers = {"REMOTE_ADDR": "203.0.113.7"}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    data = raw if raw is not None else json.dumps(body)
    return Client().post(
        f"/api/v1/stats/{path}", data, content_type="application/json", **headers
    )


def get(path, token=None):
    headers = {"REMOTE_ADDR": "203.0.113.7"}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return Client().get(f"/api/v1/stats/{path}", **headers)


# EOF
