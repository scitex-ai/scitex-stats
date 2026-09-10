#!/usr/bin/env python3
# File: tests/scitex_stats/_django/test_views.py
"""Route tests for the scitex-stats Django app (Statistics calculator UI).

Boots the app via its own app-config + scitex-ui and exercises every view
with Django's test client, proving the app is a real, mountable SciTeX
workspace app (compass §12 / Stats Calculator #207-#209): the thin UI shells
out to the ``scitex_stats`` common package and returns real results.

Requires the [server] extra (django + scitex-ui + scitex-app); skipped
cleanly when absent so a base install's suite still runs.

Test-style notes: each test asserts a SINGLE property and carries
Arrange/Act/Assert markers (the repo's STX-TQ convention, per test_api.py).
"""

from __future__ import annotations

import json
import re

import pytest

# ---------------------------------------------------------------------------
# Django bootstrap (once), from the app's own app-config + scitex-ui.
# ---------------------------------------------------------------------------
django = pytest.importorskip("django")
pytest.importorskip("scitex_app")
pytest.importorskip("scitex_ui")

import numpy as np  # noqa: E402

from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure(
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
                "OPTIONS": {
                    "context_processors": ["django.template.context_processors.request"]
                },
            }
        ],
        DATABASES={},
        STATIC_URL="/static/",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )

django.setup()

import scitex_stats._django.views  # noqa: E402  (runs the install guard, registry now ready)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    # Arrange
    from django.test import Client
    # Act
    return Client()
    # Assert: n/a — fixture, not a test


@pytest.fixture
def two_groups():
    # Arrange
    # Act
    return (
        np.random.default_rng(1).normal(10.0, 2.0, 30),
        np.random.default_rng(2).normal(12.0, 2.0, 30),
    )
    # Assert: n/a — fixture, not a test


def _post(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


# ---------------------------------------------------------------------------
# SPA shell (index)
# ---------------------------------------------------------------------------
def test_index_returns_http_200(client):
    # Arrange
    # Act
    resp = client.get("/")
    # Assert
    assert resp.status_code == 200


def test_index_contains_stx_mount_marker(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'name="stx-mount"' in html


def test_index_contains_app_header(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "SciTeX Statistics" in html


def test_index_links_app_stylesheet(client):
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "stats/css/stats.css" in html


def test_index_stx_mount_is_root_prefix(client):
    # Arrange — standalone root mount is "" (contract: never a trailing "/")
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'content=""' in html


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------
def test_health_returns_ok_status(client):
    # Arrange
    # Act
    body = client.get("/api/health").json()
    # Assert
    assert body["status"] == "ok"


def test_health_reports_app_name(client):
    # Arrange
    # Act
    body = client.get("/api/health").json()
    # Assert
    assert body["app"] == "scitex-stats"


def test_health_reports_test_count(client):
    # Arrange
    # Act
    body = client.get("/api/health").json()
    # Assert
    assert body["tests"] > 0


# ---------------------------------------------------------------------------
# /api/tests (catalogue)
# ---------------------------------------------------------------------------
def test_tests_catalogue_contains_ttest_ind(client):
    # Arrange
    # Act
    body = client.get("/api/tests").json()
    # Assert
    assert "ttest_ind" in body["tests"]


def test_tests_catalogue_contains_anova(client):
    # Arrange
    # Act
    body = client.get("/api/tests").json()
    # Assert
    assert "anova" in body["tests"]


# ---------------------------------------------------------------------------
# /api/run
# ---------------------------------------------------------------------------
def test_run_ttest_returns_statistic(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    body = _post(client, "/api/run", {"test_name": "ttest_ind", "data": a.tolist(), "data2": b.tolist()}).json()
    # Assert
    assert body["statistic"] != 0


def test_run_ttest_returns_pvalue(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    body = _post(client, "/api/run", {"test_name": "ttest_ind", "data": a.tolist(), "data2": b.tolist()}).json()
    # Assert
    assert 0 < body["pvalue"] < 1


def test_run_ttest_returns_apa_formatted(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    body = _post(client, "/api/run", {"test_name": "ttest_ind", "data": a.tolist(), "data2": b.tolist()}).json()
    # Assert
    assert "t =" in body["formatted"]


def test_run_unknown_test_returns_400(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/run", {"test_name": "not_a_test", "data": a.tolist(), "data2": b.tolist()})
    # Assert
    assert resp.status_code == 400


def test_run_missing_test_name_returns_400(client):
    # Arrange
    # Act
    resp = _post(client, "/api/run", {"data": [1, 2, 3]})
    # Assert
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/recommend
# ---------------------------------------------------------------------------
def test_recommend_returns_recommendation_list(client):
    # Arrange
    # Act
    resp = _post(client, "/api/recommend", {"n_groups": 2, "sample_sizes": [30, 30]})
    # Assert
    assert resp.status_code == 200


def test_recommend_names_are_strings(client):
    # Arrange
    # Act
    recs = _post(client, "/api/recommend", {"n_groups": 2, "sample_sizes": [30, 30]}).json()["recommendations"]
    # Assert
    assert all(isinstance(r, str) for r in recs)


# ---------------------------------------------------------------------------
# /api/effect-size
# ---------------------------------------------------------------------------
def test_effect_size_cohens_d_runs(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    resp = _post(client, "/api/effect-size", {"group1": a.tolist(), "group2": b.tolist()})
    # Assert
    assert resp.status_code == 200


def test_effect_size_returns_nonzero_value(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    body = _post(client, "/api/effect-size", {"group1": a.tolist(), "group2": b.tolist()}).json()
    # Assert
    assert body["value"] != 0


# ---------------------------------------------------------------------------
# /api/power
# ---------------------------------------------------------------------------
def test_power_sample_size_returns_26_26(client):
    # Arrange
    # Act
    n = _post(client, "/api/power", {"which": "sample_size", "effect_size": 0.8}).json()["value"]
    # Assert
    assert n == [26, 26]


# ---------------------------------------------------------------------------
# /api/posthoc
# ---------------------------------------------------------------------------
def test_posthoc_tukey_returns_three_comparisons(client, two_groups):
    # Arrange
    a, b = two_groups
    # Act
    body = _post(client, "/api/posthoc", {"groups": [a.tolist(), b.tolist(), (a + 1).tolist()], "method": "tukey"}).json()
    # Assert
    assert len(body["comparisons"]) == 3


# ---------------------------------------------------------------------------
# /api/correct
# ---------------------------------------------------------------------------
def test_correct_fdr_returns_four_rows(client):
    # Arrange
    # Act
    body = _post(client, "/api/correct", {"pvalues": [0.01, 0.02, 0.03, 0.5], "method": "fdr_bh"}).json()
    # Assert
    assert len(body["results"]) == 4


def test_correct_missing_pvalues_returns_400(client):
    # Arrange
    # Act
    resp = _post(client, "/api/correct", {"method": "bonferroni"})
    # Assert
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/describe
# ---------------------------------------------------------------------------
def test_describe_returns_mean(client):
    # Arrange
    # Act
    resp = _post(client, "/api/describe", {"data": [1.0, 2.0, 3.0, 4.0, 5.0]})
    # Assert
    assert resp.status_code == 200


def test_describe_mean_is_three(client):
    # Arrange
    # Act
    stats = _post(client, "/api/describe", {"data": [1.0, 2.0, 3.0, 4.0, 5.0]}).json()["statistics"]
    # Assert
    assert stats["mean"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# manifest.json + AppConfig
# ---------------------------------------------------------------------------
def test_manifest_declares_all_required_fields():
    # Arrange
    from pathlib import Path

    manifest = Path(scitex_stats._django.__file__).parent / "manifest.json"
    # Act
    data = json.loads(manifest.read_text())
    # Assert
    assert all(data.get(k) for k in ("name", "slug", "label", "version", "icon"))


def test_manifest_slug_is_stats():
    # Arrange
    from pathlib import Path

    manifest = Path(scitex_stats._django.__file__).parent / "manifest.json"
    # Act
    data = json.loads(manifest.read_text())
    # Assert
    assert data["slug"] == "stats"


def test_manifest_marks_standalone_app():
    # Arrange
    from pathlib import Path

    manifest = Path(scitex_stats._django.__file__).parent / "manifest.json"
    # Act
    data = json.loads(manifest.read_text())
    # Assert
    assert data["standalone"] is True


def test_app_config_module_name():
    # Arrange
    from scitex_stats._django.apps import StatsCalculatorConfig
    # Act
    # Assert
    assert StatsCalculatorConfig.name == "scitex_stats._django"


def test_app_config_label():
    # Arrange
    from scitex_stats._django.apps import StatsCalculatorConfig
    # Act
    # Assert
    assert StatsCalculatorConfig.label == "stats_calculator"


# EOF
