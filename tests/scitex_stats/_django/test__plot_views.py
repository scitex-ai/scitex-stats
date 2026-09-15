#!/usr/bin/env python3
# File: tests/scitex_stats/_django/test__plot_views.py
"""Plot view + FigRecipe discovery (mirrors src/scitex_stats/_django/_plot_views.py).

Shares the Django bootstrap of test_views.py (settings configure once per process).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_app")
pytest.importorskip("scitex_ui")

from . import test_views  # noqa: E402,F401  (configures settings + django.setup)

from scitex_stats._django import _plot_views  # noqa: E402

A = [5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7]
B = [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]
C = [5.5, 6.0, 5.9, 6.2, 5.8, 6.1, 5.7, 6.0]


@pytest.fixture
def client():
    # Arrange
    from django.test import Client
    # Act
    return Client()
    # Assert: n/a — fixture, not a test


def _post(client, payload):
    return client.post("/api/plot", data=json.dumps(payload), content_type="application/json")


def _hub_urls(names):
    return {
        "figrecipe_app:figrecipe_editor": "/apps/figrecipe/figrecipe/",
        "figrecipe_app:figure_editor": "/apps/figrecipe/",
    }.get(names[0])


def test_plot_ttest_returns_http_200(client):
    # Arrange
    payload = {"test_name": "ttest_ind", "data": A, "data2": B}
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 200


def test_plot_returns_svg_data_uri(client):
    # Arrange
    payload = {"test_name": "ttest_ind", "data": A, "data2": B}
    # Act
    body = _post(client, payload).json()
    # Assert
    assert body["svg"].startswith("data:image/svg+xml;base64,")


def test_plot_returns_png_data_uri(client):
    # Arrange
    payload = {"test_name": "ttest_ind", "data": A, "data2": B}
    # Act
    body = _post(client, payload).json()
    # Assert
    assert body["png"].startswith("data:image/png;base64,")


def test_plot_returns_versioned_spec(client):
    # Arrange
    payload = {"test_name": "ttest_ind", "data": A, "data2": B}
    # Act
    spec = _post(client, payload).json()["plot_spec"]
    # Assert
    assert (spec["schema"], spec["version"]) == ("scitex-stats.plot-spec", 1)


def test_plot_anova_with_posthoc_draws_three_brackets(client):
    # Arrange
    payload = {"test_name": "anova", "groups": [A, B, C], "group_names": ["A", "B", "C"], "posthoc": "tukey"}
    # Act
    spec = _post(client, payload).json()["plot_spec"]
    # Assert
    assert len(spec["annotations"]["brackets"]) == 3


def test_plot_matplotlib_backend_is_honoured(client):
    # Arrange
    payload = {"test_name": "pearson", "data": A, "data2": B, "backend": "matplotlib"}
    # Act
    body = _post(client, payload).json()
    # Assert
    assert body["backend"] == "matplotlib"


def test_plot_missing_test_name_returns_400(client):
    # Arrange
    payload = {"data": A}
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_figrecipe_hidden_when_not_installed():
    # Arrange
    def discover():
        return ["stats"]
    # Act
    info = _plot_views.figrecipe_integration(discover=discover, resolve=_hub_urls)
    # Assert
    assert info == {"available": False}


def test_figrecipe_hidden_when_installed_but_not_mounted():
    # Arrange
    def discover():
        return ["stats", "figrecipe"]
    # Act
    info = _plot_views.figrecipe_integration(discover=discover, resolve=lambda names: None)
    # Assert
    assert info["available"] is False


def test_figrecipe_shown_when_installed_and_mounted():
    # Arrange
    def discover():
        return ["stats", "figrecipe"]
    # Act
    info = _plot_views.figrecipe_integration(discover=discover, resolve=_hub_urls)
    # Assert
    assert info == {
        "available": True,
        "import_url": "/apps/figrecipe/figrecipe/api/import/stats-plot-spec",
        "open_url": "/apps/figrecipe/",
    }


def test_integrations_endpoint_hides_figrecipe_in_standalone(client):
    # Arrange
    url = "/api/integrations"
    # Act
    body = client.get(url).json()
    # Assert
    assert body["figrecipe"]["available"] is False


def test_template_ships_open_in_figrecipe_button_hidden():
    # Arrange
    from pathlib import Path

    template = Path(_plot_views.__file__).parent / "templates" / "stats" / "stats.html"
    # Act
    html = template.read_text(encoding="utf-8")
    # Assert
    assert 'id="statsOpenFigrecipe" hidden' in html


# EOF
