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

_APP_ROOT = Path(__file__).resolve().parents[3] / "src/scitex_stats/_django"


def _stats_css():
    return (_APP_ROOT / "static/stats/css/stats.css").read_text(encoding="utf-8")


def _stats_js():
    return (_APP_ROOT / "static/stats/js/app.js").read_text(encoding="utf-8")


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
        'id="statsSample"' in html
        and "Load sample dataset" in html
        and "or Load Sample Data" not in html
        and 'class="stats-btn stats-dropzone__button" id="statsChooseFile"' in html
    )


def test_sample_action_sits_below_the_drop_zone_not_in_the_header(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert html.index('id="statsChooseFile"') < html.index('id="statsSample"')


def test_sample_action_is_a_labelled_secondary_button_with_a_description(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert (
        '<button type="button" class="stats-btn stats-btn--secondary stats-source__sample" id="statsSample">'
        in html
        and "replacing anything already entered" in html
    )


def test_drop_zone_offers_hover_focus_and_dragover_states():
    # Arrange
    css = _stats_css()
    # Act
    zone = css.split(".stats-dropzone {", 1)[1].split(".stats-hint {", 1)[0]
    # Assert
    assert (
        ".stats-dropzone:hover" in zone
        and ".stats-dropzone:focus-within" in zone
        and ".stats-dropzone--active" in zone
        and ":focus-visible" in zone
        and "var(--stats-accent)" in zone
    )


def test_selected_test_row_is_flat_with_a_straight_accent_line():
    # Arrange
    css = _stats_css()
    # Act
    base = css.split(".stats-test {", 1)[1].split("}", 1)[0]
    selected = css.split(".stats-test:has(input:checked) {", 1)[1].split("}", 1)[0]
    # Assert
    assert (
        "border-radius: 0;" in base
        and "border-left: 4px solid transparent;" in base
        and "border-left-color: var(--stats-accent);" in selected
        and "box-shadow: none;" in selected
    )


def test_phone_layout_keeps_every_touch_target_at_least_44px():
    # Arrange
    css = _stats_css()
    # Act
    phone = css.split("@media (max-width: 480px) {", 1)[1]
    # Assert
    assert "min-height: 44px;" in phone and "grid-template-columns: 1fr;" in phone


def test_sample_loader_confirms_before_replacing_typed_data():
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "function hasUserData()" in js and "window.confirm(" in js and "hasUserData() && !window.confirm(" in js


def test_choose_file_button_and_zone_both_open_the_picker():
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert '$("statsChooseFile").addEventListener("click"' in js and 'dropZone.addEventListener("click"' in js


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


def test_pane_titles_show_the_three_step_workflow(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert all(
        title in html
        for title in ("1. Data Input", "2. Test Selection", "3. Results")
    )


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
