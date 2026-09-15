#!/usr/bin/env python3
"""Stats app: /api/recommend-test, /api/run-all and the enabled Recommend button."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_app")
pytest.importorskip("scitex_ui")

from .test_views import (  # noqa: E402,F401  (shared Django bootstrap + fixture)
    _post,
    client,
)

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


def test_index_places_recommend_action_in_test_header(client):  # noqa: F811
    # Arrange
    template = (
        Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/templates/stats/stats.html"
    ).read_text(encoding="utf-8")
    test_pane = template.index('{% scitex_pane "test"')
    header_end = template.index("</header>", test_pane)
    # Act
    header = template[test_pane:header_end]
    # Assert
    assert 'id="statsRecommend">{% translate "Select recommended test" %}</button>' in header


def test_three_pane_headers_have_one_fixed_height():
    # Arrange
    css = (
        Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/static/stats/css/stats.css"
    ).read_text(encoding="utf-8")
    # Act
    header_rule = css.split(".stats-pane__header {", 1)[1].split("}", 1)[0]
    # Assert
    assert "height: 48px;" in header_rule and "flex: 0 0 48px;" in header_rule


def test_data_actions_keep_sample_and_use_clickable_drop_target(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert (
        "or Load Sample Data" in html
        and "Load from CSV" not in html
        and 'for="statsCsv">Drop a CSV or TSV file here, or click to choose.</label>'
        in html
    )


def test_form_dropdowns_use_scitex_ui_select_primitive():
    # Arrange
    template = (
        Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/templates/stats/stats.html"
    ).read_text(encoding="utf-8")
    # Act
    selects = ["statsDesign", "statsScale", "statsAlt", "statsCorrMethod", "statsPhMethod"]
    # Assert
    assert all(f'<select class="stx-select" id="{select_id}">' in template for select_id in selects)


def test_data_pane_accepts_dropped_csv(client):  # noqa: F811
    # Arrange
    html = client.get("/").content.decode()
    js = (
        Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/static/stats/js/app.js"
    ).read_text(encoding="utf-8")
    # Act
    has_drop_target = 'id="statsDataDrop"' in html
    # Assert
    assert has_drop_target and 'addEventListener("drop"' in js and "loadCsv(file)" in js


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
