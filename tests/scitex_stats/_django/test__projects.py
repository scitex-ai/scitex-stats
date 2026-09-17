#!/usr/bin/env python3
"""Standalone project provider: local folders, the HTTP contract, and its guards.

The projects root is redirected by ENVIRONMENT (the same knob a user sets), not
by patched objects: PA-306 forbids mocks, and this is real process state set and
restored around the case.
"""

from __future__ import annotations

import contextlib
import json
import os
import pathlib

from .test_views import client  # noqa: E402,F401  (shared Django bootstrap + fixture)
from scitex_ui.project_scope import ProjectEntry  # noqa: E402

from scitex_stats._django import _projects


@contextlib.contextmanager
def _projects_root(path):
    previous = os.environ.get(_projects.ROOT_ENV)
    os.environ[_projects.ROOT_ENV] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_projects.ROOT_ENV, None)
        else:
            os.environ[_projects.ROOT_ENV] = previous


def test_projects_root_prefers_the_configured_env(tmp_path):
    # Arrange
    configured = tmp_path / "elsewhere"
    # Act
    with _projects_root(configured):
        root = _projects.projects_root()
    # Assert
    assert root == configured


def test_provider_lists_every_visible_folder(tmp_path):
    # Arrange
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / ".hidden").mkdir()
    # Act
    with _projects_root(tmp_path):
        entries = _projects.provider().list_projects()
    # Assert
    assert [entry.id for entry in entries] == ["alpha", "beta"]


def test_project_scope_endpoint_serves_the_projects_and_current(tmp_path, client):  # noqa: F811
    # Arrange
    (tmp_path / "project_one").mkdir()
    # Act
    with _projects_root(tmp_path):
        body = json.loads(client.get("/api/project-scope").content.decode())
    # Assert
    assert [p["id"] for p in body["projects"]] == ["project_one"] and body["current"] is None


def test_project_scope_endpoint_refuses_an_unknown_project(tmp_path, client):  # noqa: F811
    # Arrange
    payload = json.dumps({"id": "not-a-project"})
    # Act
    with _projects_root(tmp_path):
        response = client.post("/api/project-scope", data=payload, content_type="application/json")
    # Assert
    assert response.status_code == 403


def test_project_scope_endpoint_remembers_an_accessible_project(tmp_path, client):  # noqa: F811
    # Arrange
    (tmp_path / "project_two").mkdir()
    payload = json.dumps({"id": "project_two"})
    # Act
    with _projects_root(tmp_path):
        response = client.post("/api/project-scope", data=payload, content_type="application/json")
    # Assert
    assert json.loads(response.content.decode())["current"] == "project_two"


def test_picker_guard_treats_a_user_scope_as_no_picker():
    # Arrange
    from scitex_ui.templatetags.scitex_project_picker import is_project_scope
    # Act
    user_scoped = is_project_scope("user")
    # Assert
    assert user_scoped is False


def test_picker_tag_renders_nothing_for_a_user_scoped_app():
    # Arrange
    from scitex_ui.templatetags.scitex_project_picker import scitex_project_picker
    # Act
    rendered = scitex_project_picker({}, scope="user")
    # Assert
    assert rendered == ""



# ---------------------------------------------------------------------------
# Project-default mode: authorized data listing, import, and write-back.
# ---------------------------------------------------------------------------


def _project_with_data(tmp_path, csv_text="a,b\n5.1,6.3\n4.9,6.8\n"):
    project = tmp_path / "cohort"
    project.mkdir()
    (project / "measurements.csv").write_text(csv_text)
    (project / "notes.txt").write_text("not data")
    return project


def test_list_data_files_lists_only_csv_and_tsv(tmp_path):
    # Arrange
    project = _project_with_data(tmp_path)
    (project / "extra.tsv").write_text("a\tb\n1\t2\n")
    # Act
    with _projects_root(tmp_path):
        names = [f["name"] for f in _projects.list_data_files("cohort")]
    # Assert
    assert names == ["extra.tsv", "measurements.csv"]


def test_list_data_files_is_none_for_an_unauthorized_project(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        listed = _projects.list_data_files("does-not-exist")
    # Assert
    assert listed is None


def test_read_data_file_returns_the_text_for_an_authorized_file(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "measurements.csv")
    # Assert
    assert text.startswith("a,b")


def test_read_data_file_refuses_a_traversal_name(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    (tmp_path / "secret.csv").write_text("nope")
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "../secret.csv")
    # Assert
    assert text is None


def test_read_data_file_refuses_a_symlink_that_escapes_the_project(tmp_path):
    # Arrange
    project = _project_with_data(tmp_path)
    outside = tmp_path / "outside.csv"
    outside.write_text("a,b\n9,9\n")
    (project / "link.csv").symlink_to(outside)
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "link.csv")
    # Assert
    assert text is None


def test_read_data_file_refuses_a_non_data_extension(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "notes.txt")
    # Assert
    assert text is None


def test_read_data_file_refuses_an_oversized_file(tmp_path):
    # Arrange: one byte over the import cap, written for real (no patching).
    project = _project_with_data(tmp_path)
    oversized = project / "big.csv"
    oversized.write_bytes(b"a,b\n" + b"1,2\n" * (_projects.MAX_IMPORT_BYTES // 4))
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "big.csv")
    # Assert
    assert text is None


def test_save_artifact_writes_under_the_stats_kind_directory(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "results", "result.json", {"pvalue": 0.01})
    # Assert
    assert saved["path"] == "stats/results/result.json" and (tmp_path / "cohort" / saved["path"]).is_file()


def test_save_artifact_refuses_an_unknown_kind(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "evil", "x.json", {})
    # Assert
    assert saved is None


def test_save_artifact_refuses_an_unauthorized_project(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("nope", "results", "x.json", {})
    # Assert
    assert saved is None


def test_save_artifact_refuses_a_traversal_name(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "results", "../escape.json", {})
    # Assert
    assert saved is None


def test_project_files_endpoint_lists_the_authorized_files(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        body = json.loads(client.get("/api/project-files?project=cohort").content.decode())
    # Assert
    assert [f["name"] for f in body["files"]] == ["measurements.csv"]


def test_project_files_endpoint_refuses_an_unknown_project(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        status = client.get("/api/project-files?project=ghost").status_code
    # Assert
    assert status == 403


def test_project_import_endpoint_returns_the_file_text(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        body = json.loads(
            client.get("/api/project-import?project=cohort&name=measurements.csv").content.decode()
        )
    # Assert
    assert body["text"].startswith("a,b")


def test_project_import_endpoint_refuses_a_traversal_name(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        status = client.get("/api/project-import?project=cohort&name=../secret.csv").status_code
    # Assert
    assert status == 403


def test_project_save_endpoint_writes_the_artifact(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    payload = json.dumps({"project": "cohort", "kind": "provenance", "name": "provenance.json", "payload": {"seed": 42}})
    # Act
    with _projects_root(tmp_path):
        response = client.post("/api/project-save", data=payload, content_type="application/json")
    # Assert
    assert response.status_code == 201 and (tmp_path / "cohort" / "stats" / "provenance" / "provenance.json").is_file()


def test_project_save_endpoint_refuses_an_unknown_kind(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    payload = json.dumps({"project": "cohort", "kind": "evil", "name": "x.json", "payload": {}})
    # Act
    with _projects_root(tmp_path):
        status = client.post("/api/project-save", data=payload, content_type="application/json").status_code
    # Assert
    assert status == 403



def test_index_lists_the_active_projects_files_in_project_mode(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        html = client.get("/?project=cohort").content.decode()
    # Assert
    assert 'data-stats-project="cohort"' in html and "measurements.csv" in html


def test_index_hides_the_project_panel_without_an_active_project(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "data-stats-project-panel hidden" in html


def test_index_has_exactly_one_header_picker_and_mode_toggle(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert (
        html.count('<header class="stats-app-header"') == 1
        and html.count('class="stx-app-header__slot--project-selector"') == 1
        and html.count('id="statsModeToggle"') == 1
    )


def test_index_offers_quick_analysis_as_the_explicit_alternative(client):  # noqa: F811
    # Arrange
    # Act
    html = client.get("/").content.decode()
    # Assert
    assert "Quick analysis" in html and 'id="statsSaveRow"' in html



def test_save_artifact_writes_decoded_base64_bytes(tmp_path):
    # Arrange: a real PNG signature, so the file proves bytes and not text.
    import base64 as b64

    _project_with_data(tmp_path)
    png = b"\x89PNG\r\n\x1a\n" + b"payload"
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "plots", "plot.png", None, payload_base64=b64.b64encode(png).decode())
    # Assert
    assert (tmp_path / "cohort" / saved["path"]).read_bytes() == png


def test_save_artifact_refuses_invalid_base64(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "plots", "plot.png", None, payload_base64="not base64 !!")
    # Assert
    assert saved is None


def test_save_artifact_refuses_an_oversized_binary(tmp_path):
    # Arrange: base64 of one byte over the write cap.
    import base64 as b64

    _project_with_data(tmp_path)
    oversized = b64.b64encode(b"x" * (_projects.MAX_ARTIFACT_BYTES + 1)).decode()
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "plots", "plot.png", None, payload_base64=oversized)
    # Assert
    assert saved is None


def test_project_save_endpoint_stores_a_rendered_plot(tmp_path, client):  # noqa: F811
    # Arrange
    import base64 as b64

    _project_with_data(tmp_path)
    png = b"\x89PNG\r\n\x1a\n" + b"pixels"
    payload = json.dumps(
        {
            "project": "cohort",
            "kind": "plots",
            "name": "plot.png",
            "payload_base64": b64.b64encode(png).decode(),
        }
    )
    # Act
    with _projects_root(tmp_path):
        response = client.post("/api/project-save", data=payload, content_type="application/json")
    # Assert
    assert response.status_code == 201 and (tmp_path / "cohort" / "stats" / "plots" / "plot.png").read_bytes() == png



def test_quick_analysis_mode_hides_every_project_write_control():
    # Arrange: Quick analysis is the STATELESS alternative — no project file
    # listing and no write-back buttons, so the mode cannot half-write.
    js = (
        pathlib.Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/static/stats/js/app.js"
    ).read_text(encoding="utf-8")
    # Act
    apply_mode = js.split("function applyMode()", 1)[1].split("function setSaveStatus", 1)[0]
    # Assert
    assert "statsProjectFiles" in apply_mode and "statsSaveRow" in apply_mode and "statsSavePlot" in apply_mode


def test_plot_save_prefers_the_rendered_figure_then_the_spec():
    # Arrange
    js = (
        pathlib.Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/static/stats/js/app.js"
    ).read_text(encoding="utf-8")
    # Act
    save_plot = js.split("async function savePlot()", 1)[1].split("\n  }", 1)[0]
    # Assert
    assert "saveRenderedPlot()" in save_plot and "plot-spec.json" in save_plot


# ---------------------------------------------------------------------------
# Host-provider precedence: in a hub mount the HOST owns project scope, so the
# file routes must ask the host's provider — not the local standalone root.
# ---------------------------------------------------------------------------


class _EnvRootHostProvider:
    """Host-shaped provider whose single project root comes from an env var.

    Defined here (and registered by dotted path below) because
    ``host_project_provider()`` resolves ``SCITEX_PROJECT_PROVIDER`` with
    ``import_string`` at request time — this module is importable as
    ``tests.scitex_stats._django.test__projects``.
    """

    def list_projects(self, request=None):
        root = pathlib.Path(os.environ["SCITEX_STATS_TEST_HOST_ROOT"])
        if not root.is_dir():
            return []
        return [ProjectEntry(id="host-cohort", name="host-cohort", detail=str(root))]

    def last_visited(self, request=None):
        return None

    def remember(self, request, project_id):
        return None


_host_provider = _EnvRootHostProvider()
HOST_PROVIDER_PATH = "tests.scitex_stats._django.test__projects._host_provider"


@contextlib.contextmanager
def _host_root(path):
    previous = os.environ.get("SCITEX_STATS_TEST_HOST_ROOT")
    os.environ["SCITEX_STATS_TEST_HOST_ROOT"] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SCITEX_STATS_TEST_HOST_ROOT", None)
        else:
            os.environ["SCITEX_STATS_TEST_HOST_ROOT"] = previous


def test_host_provider_decides_the_listing_when_registered(tmp_path):
    # Arrange: a LOCAL project of the same name exists, and must be ignored.
    local_root = tmp_path / "local"
    local_project = local_root / "host-cohort"
    local_project.mkdir(parents=True)
    (local_project / "local-file.csv").write_text("a\n1\n")
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "host-file.csv").write_text("a\n1\n")
    # Act
    from django.test import override_settings

    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH), _projects_root(local_root), _host_root(host_root):
        listed = _projects.list_data_files("host-cohort")
    # Assert
    assert [f["name"] for f in listed] == ["host-file.csv"]


def test_local_provider_is_the_standalone_fallback(tmp_path):
    # Arrange
    root = tmp_path / "local-only"
    project = root / "cohort"
    project.mkdir(parents=True)
    (project / "only-here.csv").write_text("a\n1\n")
    # Act
    from django.test import override_settings

    with override_settings(SCITEX_PROJECT_PROVIDER=""), _projects_root(root):
        listed = _projects.list_data_files("cohort")
    # Assert
    assert [f["name"] for f in listed] == ["only-here.csv"]


# EOF
