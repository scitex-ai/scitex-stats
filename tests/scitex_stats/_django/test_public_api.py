"""Affected public HTTP boundary; no numerical or host activation verdict."""

import importlib.util
import json

import pytest

django = pytest.importorskip("django")
from django.conf import settings
from django.test import Client, override_settings
from django.urls import path

from scitex_stats._django.public_api import stats_recommend

if not settings.configured:
    settings.configure(SECRET_KEY="test", ALLOWED_HOSTS=["testserver"])

urlpatterns = [path("recommend/", stats_recommend)]


@pytest.fixture
def public_client():
    with override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
    ):
        yield Client(enforce_csrf_checks=True)


def test_wrong_method_remains_django_405(public_client):
    # Arrange
    endpoint = "/recommend/"
    # Act
    response = public_client.get(endpoint)
    # Assert
    assert (response.status_code, response["Allow"]) == (405, "POST")


def test_malformed_json_keeps_public_500_envelope(public_client):
    # Arrange
    malformed_body = "{"
    # Act
    response = public_client.post(
        "/recommend/", data=malformed_body, content_type="application/json"
    )
    # Assert
    assert (response.status_code, response.json()) == (
        500,
        {
            "success": False,
            "error": "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
        },
    )


@pytest.mark.skipif(
    importlib.util.find_spec("scitex") is not None,
    reason="This genuine missing-umbrella boundary requires an installation without scitex",
)
def test_anonymous_keyless_post_reaches_missing_umbrella_503(public_client):
    # Arrange: no CSRF token or idempotency key, as in the existing public API.
    body = json.dumps({})
    # Act
    response = public_client.post(
        "/recommend/", data=body, content_type="application/json"
    )
    # Assert
    assert (response.status_code, response.json()) == (
        503,
        {"success": False, "error": "scitex package not available"},
    )
