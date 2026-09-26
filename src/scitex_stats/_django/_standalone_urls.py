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

from django.contrib.staticfiles.views import serve as _serve_static
from django.urls import include, path, re_path

urlpatterns = [
    re_path(r"^static/(?P<path>.*)$", _serve_static, {"insecure": True}),
    path("", include("scitex_stats._django.urls")),
]

# EOF
