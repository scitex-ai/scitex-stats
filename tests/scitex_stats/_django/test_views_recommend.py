#!/usr/bin/env python3
"""Stats app: /api/recommend-test, /api/run-all and the button-free auto UX."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_sdk")
importlib.import_module("scitex_sdk.app")
importlib.import_module("scitex_sdk.ui")

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


def test_recommend_test_single_group_reports_applicability_with_reasons(client):  # noqa: F811
    # Arrange: one group of numbers — the picker dims from this payload.
    # Act
    body = _post(
        client,
        "/api/recommend-test",
        {"groups": [[5.1, 4.9, 5.6, 5.8, 6.0]], "group_names": ["Group 1"], "design": "independent", "scale": "continuous"},
    ).json()
    # Assert: at least one inapplicable test carries hover reasons.
    assert [r for r in body["applicability"] if not r["applicable"] and r["reason_items"]]


def test_index_has_no_recommend_button(client):  # noqa: F811
    # Arrange: auto-calculate removed the button (CCT 3896/3897).
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsRecommend"' not in html


def test_index_has_no_calculate_button(client):  # noqa: F811
    # Arrange: auto-calculate removed the button (CCT 3896/3897).
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsCalculate"' not in html


def test_index_test_header_carries_no_action_buttons(client):  # noqa: F811
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
    assert "<button" not in header


def test_index_empty_state_describes_auto_calculate(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "runs automatically" in html


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
        and "Try with Sample Data" in html
        and "or Load Sample Data" not in html
        and 'class="stats-btn stats-dropzone__button" id="statsChooseFile"' in html
        # Operator 2026-10-22: the button lives with the data input boxes
        # (Add group / Clear row), always visible regardless of design/scale.
        # Operator 2026-10-23: right-aligned after Clear, separated from the
        # ordinal Add-group/Clear workflow.
        and html.index('id="statsGroups"') < html.index('id="statsClear"')
        and html.index('id="statsClear"') < html.index('id="statsSample"')
        and 'stats-row__right' in html
    )


def test_sample_action_sits_with_the_data_boxes_not_in_the_header(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    # Operator 2026-10-22: input boxes first, then the action row.
    assert html.index('id="statsGroups"') < html.index('id="statsSample"')


def test_sample_action_is_a_labelled_secondary_button_with_a_description(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert (
        'id="statsSample"' in html
        and "Try with Sample Data" in html
        # The explainer rides the native tooltip now that the button sits
        # in the action row (operator 2026-10-22); renamed 2026-10-23 as
        # "Load sample dataset" was ambiguous.
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
    phone = css.split("@media (max-width: 600px), (pointer: coarse) {", 1)[1]
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


def test_alternative_hypothesis_leads_the_test_pane():
    # Operator 2026-10-22: Alternative hypothesis is important and
    # distinct from the other selectors — it renders above the test
    # radio list. (Own test: STX-TQ007 allows one assertion per test.)
    # Arrange
    template = (
        Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/templates/stats/stats.html"
    ).read_text(encoding="utf-8")
    # Act
    alt_pos = template.index('id="statsAlt"')
    tests_pos = template.index('id="statsTests"')
    # Assert
    assert alt_pos < tests_pos


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


def test_column_headers_have_muted_background_with_default_border():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    header_rule = css.split(".stats-pane__header {", 1)[1].split("}", 1)[0]
    # Assert
    # Operator 2026-10-23: stronger contrast for the three column headers
    # (1. Data Input, 2. Test Selection, 3. Results).
    assert "background: var(--bg-muted);" in header_rule and "border-bottom: 1px solid var(--border-default);" in header_rule


def test_column_titles_use_primary_text_color():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    title_rule = css.split(".stats-pane__title {", 1)[1].split("}", 1)[0]
    # Assert
    assert "color: var(--text-primary);" in title_rule


def test_sample_action_is_right_aligned_in_its_row():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    rule = css.split(".stats-row__right {", 1)[1].split("}", 1)[0]
    # Assert
    # Operator 2026-10-23: right-aligned, separated from the ordinal
    # Add-group/Clear workflow on the left.
    assert "margin-left: auto;" in rule


def test_sample_loader_defines_categorical_counts_twin():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    # Operator 2026-10-23: the sample must fit the current measurement scale
    # so results show — categorical needs integer counts.
    assert "var SAMPLE_COUNTS = [" in js


def test_sample_loader_selects_counts_for_categorical_scale():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert '$("statsScale").value === "categorical" ? SAMPLE_COUNTS : SAMPLE' in js


def test_recommend_categorical_counts_are_applicable(client):  # noqa: F811
    # Arrange
    payload = {
        "groups": [[12, 7, 14, 9], [8, 13, 6, 12]],
        "group_names": ["Group 1", "Group 2"],
        "design": "independent",
        "scale": "categorical",
    }
    # Act
    body = _post(client, "/api/recommend-test", payload).json()
    # Assert
    assert any(row.get("applicable") for row in body["applicability"])


def test_recommend_categorical_decimals_return_400(client):  # noqa: F811
    # Arrange
    # Categorical tests require integer counts: the old decimal-only sample
    # is rejected under this scale (operator 2026-10-23) — hence the
    # counts variant the sample button now loads.
    payload = {
        "groups": [[5.1, 4.9, 5.6], [6.3, 6.8, 6.1]],
        "group_names": ["Group 1", "Group 2"],
        "design": "independent",
        "scale": "categorical",
    }
    # Act
    resp = _post(client, "/api/recommend-test", payload)
    # Assert
    assert resp.status_code == 400


def test_recommend_categorical_decimal_error_mentions_counts(client):  # noqa: F811
    # Arrange
    payload = {
        "groups": [[5.1, 4.9, 5.6], [6.3, 6.8, 6.1]],
        "group_names": ["Group 1", "Group 2"],
        "design": "independent",
        "scale": "categorical",
    }
    # Act
    resp = _post(client, "/api/recommend-test", payload)
    # Assert
    assert "counts" in resp.json().get("error", "")


def test_separator_estimation_defines_estimate_sep(client):  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    # Operator 2026-10-23: comma/space/tab/newline/semicolon/pipe, with the
    # in-line delimiter estimated from the input (no vendored sniffer fits
    # the client-side parse path; Python csv.Sniffer cannot apply).
    assert "function estimateSep(sampled)" in js


def test_separator_estimation_used_for_paste_parse(client):  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "splitPattern(estimateSep(raw))" in js


def test_separator_estimation_used_for_first_line_probe(client):  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert 'estimateSep(lines[0] || "")' in js


def test_column_chooser_panel_present_but_hidden(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    # Operator 2026-10-23: CSV upload with column specification — multi
    # numeric columns offer a chooser; one imports directly.
    assert '<section class="stats-colpick" id="statsColPick" hidden>' in html


def test_column_chooser_has_list_container(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsColPickList"' in html


def test_column_chooser_has_import_action(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsColPickImport"' in html and "Import selected" in html


def test_column_chooser_has_cancel_action(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert 'id="statsColPickCancel"' in html


def test_column_chooser_defines_render_function():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "function renderColPick(numeric, integrity)" in js


def test_column_chooser_defines_import_function():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "function importColPick()" in js


def test_column_chooser_imports_single_column_directly():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "numeric.length === 1" in js


def test_column_chooser_list_stacks_vertically():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    pick_list = css.split(".stats-colpick__list {", 1)[1].split("}", 1)[0]
    # Assert
    assert "flex-direction: column;" in pick_list


def test_column_chooser_items_center_align():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    pick_item = css.split(".stats-colpick__item {", 1)[1].split("}", 1)[0]
    # Assert
    assert "align-items: center;" in pick_item


def test_clear_button_wears_alert_danger_class(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    # Operator 2026-10-24: Clear is destructive — the alert red, not ghost.
    assert 'class="stats-btn stats-btn--danger" id="statsClear"' in html


def test_danger_button_uses_alert_status_token():  # noqa: F811
    # Arrange
    css = _stats_css()
    # Act
    danger = css.split(".stats-btn--danger {", 1)[1].split("}", 1)[0]
    # Assert
    # Operator 2026-10-24: the SDK alert token, never a leaf-local hex.
    assert "var(--status-error)" in danger


def test_import_preview_panel_lives_in_data_pane(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert (
        'id="statsPreview"' in html
        and 'id="statsPreviewTitle"' in html
        and 'id="statsPreviewMeta"' in html
        and 'id="statsPreviewTable"' in html
        and html.index('id="statsGroups"') < html.index('id="statsPreview"')
    )


def test_preview_render_function_renders_separator_shape_rows():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "function renderPreview(name, sep, rows, cols)" in js


def test_pending_chooser_states_boxes_stay_active(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    # Operator 2026-10-24: a pending import must not look applied.
    assert "Not imported yet" in html and 'id="statsColPickNote"' in html


def test_chooser_labels_prefer_header_names():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    # Operator 2026-10-24: sin_x, not Column 1 — mapping must be explicit.
    assert 'header ? _("%s (%s values)")' in js


def test_separator_selector_defaults_to_auto(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    # Operator 2026-10-26: hard separator specification, Auto by default
    # so estimation runs untouched until the user overrides.
    assert '<option value="auto" selected>' in html


def test_manual_separator_overrides_estimation_in_loader():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert "var forced = manualSep();" in js


def test_manual_separator_falls_back_to_tsv_contract():  # noqa: F811
    # Arrange
    js = _stats_js()
    # Act
    # Assert
    assert 'forced || ((name || "").toLowerCase().endsWith(".tsv")' in js
