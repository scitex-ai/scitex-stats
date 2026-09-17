#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL patterns for the scitex-stats Django app.

The hub mounts this module under its own prefix (e.g. ``/apps/u/stats/``);
standalone uses ``_standalone_urls`` which includes this one. ``app_name``
is set so namespace-relative reverse() works from a host urlconf.
"""

from django.urls import path

from scitex_ui.project_scope import project_listing_view

from . import _plot_views, _projects, views

app_name = "stats"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/health", views.health, name="health"),
    # The picker's HTTP contract: GET {projects, current}, POST {id} (403 when
    # the project is not accessible). The provider is the host's when one is
    # registered, else the standalone local-folder one (settings-driven).
    path(
        "api/project-scope",
        project_listing_view(_projects.provider),
        name="api_project_scope",
    ),
    # Project-default mode: list the active project's data, import one file,
    # and write artifacts back into the project.
    path("api/project-files", views.project_files, name="project_files"),
    path("api/project-import", views.project_import, name="project_import"),
    path("api/project-save", views.project_save, name="project_save"),
    path("api/tests", views.tests, name="tests"),
    path("api/recommend", views.recommend, name="recommend"),
    path("api/recommend-test", views.recommend_test, name="recommend_test"),
    path("api/run-all", views.run_all, name="run_all"),
    path("api/run", views.run, name="run"),
    path("api/describe", views.describe, name="describe"),
    path("api/effect-size", views.effect_size, name="effect_size"),
    path("api/power", views.power, name="power"),
    path("api/posthoc", views.posthoc, name="posthoc"),
    path("api/correct", views.correct, name="correct"),
    path("api/plot", _plot_views.plot, name="plot"),
    path("api/integrations", _plot_views.integrations, name="integrations"),
]

# EOF
