#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL patterns for the scitex-stats Django app.

The hub mounts this module under its own prefix (e.g. ``/apps/u/stats/``);
standalone uses ``_standalone_urls`` which includes this one. ``app_name``
is set so namespace-relative reverse() works from a host urlconf.
"""

from django.urls import path

from . import views

app_name = "stats"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/health", views.health, name="health"),
    path("api/tests", views.tests, name="tests"),
    path("api/recommend", views.recommend, name="recommend"),
    path("api/run", views.run, name="run"),
    path("api/describe", views.describe, name="describe"),
    path("api/effect-size", views.effect_size, name="effect_size"),
    path("api/power", views.power, name="power"),
    path("api/posthoc", views.posthoc, name="posthoc"),
    path("api/correct", views.correct, name="correct"),
]

# EOF
