#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Root URLconf for the standalone `scitex-stats gui` launcher.

Cloud (scitex-hub) deployments do NOT use this -- they include
`scitex_stats._django.urls` directly under their own prefix. Static files
are served here regardless of DEBUG, because Django's `runserver` only
serves /static/ while DEBUG=True and the SDK's `run_standalone` is
runserver with no `--insecure` passthrough; the staticfiles `serve` view
resolves through the same finders runserver uses and ignores DEBUG.
"""

# PS-233: `django` is a `[server]`-only distribution. This module is a Django
# URLconf — it has no meaning without the framework — so the guard FAILS
# LOUDLY with the extra to install instead of silently degrading.
try:
    from django.contrib.staticfiles.views import serve as _serve_static
    from django.urls import include, path, re_path
except ImportError as exc:
    raise ImportError(
        "scitex_stats._django._standalone_urls needs Django, which is not installed. "
        "Install the optional stack: pip install 'scitex-stats[server]'"
    ) from exc

urlpatterns = [
    re_path(r"^static/(?P<path>.*)$", _serve_static, {"insecure": True}),
    path("", include("scitex_stats._django.urls")),
]

# EOF
