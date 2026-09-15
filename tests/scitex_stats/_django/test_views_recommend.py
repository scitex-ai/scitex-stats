#!/usr/bin/env python3
"""Stats app: /api/recommend-test, /api/run-all and the enabled Recommend button."""

from __future__ import annotations

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_app")
pytest.importorskip("scitex_ui")

from .test_views import _post, client  # noqa: E402,F401  (shared Django bootstrap + fixture)

SAMPLE = {
    "groups": [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2]],
    "group_names": ["Group 1", "Group 2"],
    "design": "independent",
    "scale": "continuous",
}


def test_recommend_test_returns_welch_for_sample(client):  # noqa: F811
    # Arrange
    # Act
    body = _post(client, "/api/recommend-test", SAMPLE).json()
    # Assert
    assert body["primary"]["test_id"] == "ttest_welch"


def test_recommend_test_returns_applicability_rows(client):  # noqa: F811
    # Arrange
    # Act
    body = _post(client, "/api/recommend-test", SAMPLE).json()
    # Assert
    assert len(body["applicability"]) == 13


def test_recommend_test_without_groups_is_400(client):  # noqa: F811
    # Arrange
    # Act
    resp = _post(client, "/api/recommend-test", {"design": "independent"})
    # Assert
    assert resp.status_code == 400


def test_run_all_labels_primary_and_sensitivity(client):  # noqa: F811
    # Arrange
    # Act
    body = _post(client, "/api/run-all", SAMPLE).json()
    # Assert
    assert [r["role"] for r in body["results"]][:2] == ["primary", "sensitivity"]


def test_run_all_carries_p_hacking_warning(client):  # noqa: F811
    # Arrange
    # Act
    body = _post(client, "/api/run-all", SAMPLE).json()
    # Assert
    assert "p-hacking" in body["warning"]


def test_index_recommend_button_is_enabled(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsRecommend" disabled' not in html and 'id="statsRecommend"' in html


def test_index_loads_recommend_script(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "stats/js/recommend.js" in html


def test_index_has_plot_slot(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "data-stats-plot-slot" in html
