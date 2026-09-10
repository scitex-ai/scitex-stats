#!/usr/bin/env python3
"""Integration tests for the scitex-stats Django app (Statistics calculator).

Boots the app via its own standalone settings (``scitex_stats._django.settings``)
and exercises the routes with Django's test client — proving the app is a real,
mountable SciTeX workspace app (compass §12 / Stats Calculator #207-#209): the
thin UI shells out to the ``scitex_stats`` common package and returns real
results.

These require the [server] extra (django + scitex-ui + scitex-app); they are
skipped cleanly when it is absent so a base install's suite still runs.
"""

from __future__ import annotations

import json

import pytest

django = pytest.importorskip("django")
pytest.importorskip("scitex_app")
pytest.importorskip("scitex_ui")

import numpy as np

import django.conf
from django.test import Client as _Client

# Configure Django once for the whole module, from the app's own settings.
if not django.conf.settings.configured:
    django.conf.settings.configure(
        SECRET_KEY="test",
        DEBUG=True,
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
            "scitex_stats._django.apps.StatsCalculatorConfig",
            "scitex_ui",
        ],
        MIDDLEWARE=["django.middleware.common.CommonMiddleware"],
        ROOT_URLCONF="scitex_stats._django.urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
            }
        ],
        DATABASES={},
        STATIC_URL="/static/",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
django.setup()

import scitex_stats._django.urls  # noqa: F401  (forces the install guard)

APP_URL = "/apps/stats"  # not used by the client; routes are at the root here


@pytest.fixture
def client():
    return _Client()


@pytest.fixture
def two_groups():
    return (
        np.random.default_rng(1).normal(10.0, 2.0, 30),
        np.random.default_rng(2).normal(12.0, 2.0, 30),
    )


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def test_index_renders_spa_shell(client):
    # Arrange
    # Act
    resp = client.get("/")
    html = resp.content.decode()
    # Assert
    assert resp.status_code == 200
    assert 'name="stx-mount"' in html  # the SDK mount contract marker
    assert "SciTeX Statistics" in html
    assert "stats/css/stats.css" in html


def test_index_mount_marker_value(client):
    # Arrange / Act
    html = client.get("/").content.decode()
    # Assert — root standalone mount is "" (the contract: never a trailing "/")
    import re

    m = re.search(r'content="([^"]*)"', re.search(r'<meta name="stx-mount"[^>]*>', html).group(0))
    assert m is not None
    assert m.group(1) == ""


def test_health(client):
    # Arrange
    # Act
    resp = client.get("/api/health")
    body = resp.json()
    # Assert
    assert resp.status_code == 200
    assert body["status"] == "ok"
    assert body["app"] == "scitex-stats"
    assert body["tests"] > 0


def test_tests_catalogue(client):
    # Arrange
    # Act
    body = client.get("/api/tests").json()
    # Assert
    assert "ttest_ind" in body["tests"]
    assert "anova" in body["tests"]


def test_run_ttest_ind_returns_unified_dict(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/run", {"test_name": "ttest_ind", "data": a.tolist(), "data2": b.tolist()})
    body = resp.json()
    # Assert
    assert resp.status_code == 200
    assert body["statistic"] != 0
    assert 0 < body["pvalue"] < 1
    assert "formatted" in body and "t =" in body["formatted"]


def test_run_unknown_test_is_400(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/run", {"test_name": "not_a_test", "data": a.tolist(), "data2": b.tolist()})
    # Assert
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_run_requires_test_name(client):
    # Arrange
    # Act
    resp = _post(client, "/api/run", {"data": [1, 2, 3]})
    # Assert
    assert resp.status_code == 400


def test_recommend(client):
    # Arrange
    # Act
    resp = _post(client, "/api/recommend", {"n_groups": 2, "sample_sizes": [30, 30]})
    recs = resp.json()["recommendations"]
    # Assert
    assert resp.status_code == 200
    assert len(recs) >= 1
    assert all(isinstance(r, str) for r in recs)


def test_effect_size(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/effect-size", {"group1": a.tolist(), "group2": b.tolist()})
    body = resp.json()
    # Assert
    assert resp.status_code == 200
    assert body["value"] != 0


def test_power_sample_size(client):
    # Arrange
    # Act
    resp = _post(client, "/api/power", {"which": "sample_size", "effect_size": 0.8})
    n = resp.json()["value"]
    # Assert
    assert resp.status_code == 200
    assert n == [26, 26]


def test_posthoc_tukey(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/posthoc", {"groups": [a.tolist(), b.tolist(), (a + 1).tolist()], "method": "tukey"})
    comps = resp.json()["comparisons"]
    # Assert
    assert resp.status_code == 200
    assert len(comps) == 3  # C(3,2) pairwise comparisons


def test_correct_fdr(client):
    # Arrange
    # Act
    resp = _post(client, "/api/correct", {"pvalues": [0.01, 0.02, 0.03, 0.5], "method": "fdr_bh"})
    body = resp.json()
    # Assert
    assert resp.status_code == 200
    assert len(body["results"]) == 4


def test_correct_rejects_missing_pvalues(client):
    # Arrange
    # Act
    resp = _post(client, "/api/correct", {"method": "bonferroni"})
    # Assert
    assert resp.status_code == 400


def test_describe(client):
    # Arrange
    # Act
    resp = _post(client, "/api/describe", {"data": [1.0, 2.0, 3.0, 4.0, 5.0]})
    stats = resp.json()["statistics"]
    # Assert
    assert resp.status_code == 200
    assert stats["mean"] == pytest.approx(3.0)


def test_manifest_valid_and_required_fields():
    """The SDK validates manifest.json; required fields must be present."""
    # Arrange
    from pathlib import Path

    manifest = Path(scitex_stats._django.__file__).parent / "manifest.json"
    # Act
    data = json.loads(manifest.read_text())
    # Assert
    for key in ("name", "slug", "label", "version", "icon"):
        assert key in data and data[key]
    assert data["standalone"] is True
    assert data["embedded_package"] is True
    assert data["slug"] == "stats"


def test_app_config_label_and_name():
    # Arrange
    from scitex_stats._django.apps import StatsCalculatorConfig
    # Act / Assert
    assert StatsCalculatorConfig.name == "scitex_stats._django"
    assert StatsCalculatorConfig.label == "stats_calculator"


# EOF
