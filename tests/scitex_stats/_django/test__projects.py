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

import pytest

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
        response = client.post("/api/project-save?project=cohort", data=payload, content_type="application/json")
    # Assert
    assert response.status_code == 201 and (tmp_path / "cohort" / "stats" / "provenance" / "provenance.json").is_file()


def test_project_save_endpoint_refuses_an_unknown_kind(tmp_path, client):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    payload = json.dumps({"project": "cohort", "kind": "evil", "name": "x.json", "payload": {}})
    # Act
    with _projects_root(tmp_path):
        status = client.post("/api/project-save?project=cohort", data=payload, content_type="application/json").status_code
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
    # Arrange: base64 of one byte over the CONFIG kind's documented cap.
    import base64 as b64

    _project_with_data(tmp_path)
    oversized = b64.b64encode(b"x" * (_projects.KIND_POLICY["config"][".json"] + 1)).decode()
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "config", "config.json", None, payload_base64=oversized)
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
        response = client.post("/api/project-save?project=cohort", data=payload, content_type="application/json")
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
    """Host-shaped provider whose single project comes from an env var.

    ``detail`` carries DISPLAY metadata, exactly as the SDK defines the field
    (the hub puts the owner's username there) — never a filesystem path. Defined
    here (and registered by dotted path below) because
    ``host_project_provider()`` resolves ``SCITEX_PROJECT_PROVIDER`` with
    ``import_string`` at request time — this module is importable as
    ``tests.scitex_stats._django.test__projects``.
    """

    def list_projects(self, request=None):
        root = pathlib.Path(os.environ["SCITEX_STATS_TEST_HOST_ROOT"])
        if not root.is_dir():
            return []
        return [ProjectEntry(id="host-cohort", name="host-cohort", detail="alice")]

    def last_visited(self, request=None):
        return None

    def remember(self, request, project_id):
        return None


class _EnvRootStorage:
    """The host's storage capability for the fixture above.

    Separate from the provider on purpose: the provider is a listing (the hub
    lists read-only collaborators too), while this decides where the files are
    and who may write them. ``SCITEX_STATS_TEST_WRITE`` makes a read-only member
    exercisable without a second provider.
    """

    def project_path(self, project_id, request=None):
        if project_id != "host-cohort":
            return None
        root = pathlib.Path(os.environ["SCITEX_STATS_TEST_HOST_ROOT"])
        return str(root) if root.is_dir() else None

    def can_write(self, project_id, request=None):
        return os.environ.get("SCITEX_STATS_TEST_WRITE", "yes") == "yes"


_host_provider = _EnvRootHostProvider()
HOST_PROVIDER_PATH = "tests.scitex_stats._django.test__projects._host_provider"
_host_storage = _EnvRootStorage()
HOST_STORAGE_PATH = "tests.scitex_stats._django.test__projects._host_storage"


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

    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=HOST_STORAGE_PATH), _projects_root(local_root), _host_root(host_root):
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


# ---------------------------------------------------------------------------
# Review blockers: request-aware authorization, descriptor-relative IO with
# no-follow, CSRF, server-side binding, strict policy, atomic versioned writes.
# ---------------------------------------------------------------------------


class _CallerScopedHostProvider:
    """A host provider that authorizes PER CALLER, the way a hub would.

    It lists `host-cohort` only when the request carries `as=alice`, so the
    request has to actually reach the provider for the answer to differ.
    """

    def __init__(self):
        self.asked_with = []

    def list_projects(self, request=None):
        self.asked_with.append(request)
        getter = getattr(request, "GET", None)
        if getter is None or getter.get("as") != "alice":
            return []
        root = pathlib.Path(os.environ["SCITEX_STATS_TEST_HOST_ROOT"])
        if not root.is_dir():
            return []
        return [ProjectEntry(id="host-cohort", name="host-cohort", detail=str(root))]

    def last_visited(self, request=None):
        return None

    def remember(self, request, project_id):
        return None


_caller_scoped_provider = _CallerScopedHostProvider()
CALLER_SCOPED_PATH = "tests.scitex_stats._django.test__projects._caller_scoped_provider"


def test_host_provider_is_asked_with_the_request(tmp_path, client):  # noqa: F811
    # Arrange: resolve the instance the SDK will import, not this module's local
    # name — pytest may import this file under a different dotted path.
    from django.test import override_settings
    from django.utils.module_loading import import_string

    provider_instance = import_string(CALLER_SCOPED_PATH)
    provider_instance.asked_with = []
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "host-file.csv").write_text("a\n1\n")
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=CALLER_SCOPED_PATH), _host_root(host_root):
        client.get("/api/project-files?project=host-cohort&as=alice")
    # Assert
    assert any(getattr(r, "GET", None) is not None for r in provider_instance.asked_with)


def test_host_provider_refuses_a_caller_it_does_not_authorize(tmp_path, client):  # noqa: F811
    # Arrange
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "host-file.csv").write_text("a\n1\n")
    # Act
    from django.test import override_settings

    with override_settings(SCITEX_PROJECT_PROVIDER=CALLER_SCOPED_PATH), _host_root(host_root):
        status = client.get("/api/project-files?project=host-cohort&as=bob").status_code
    # Assert
    assert status == 403


def test_read_refuses_a_symlink_inside_the_project(tmp_path):
    # Arrange: the link points at a REAL data file in the same project, so only
    # the no-follow open can refuse it.
    project = _project_with_data(tmp_path)
    (project / "alias.csv").symlink_to(project / "measurements.csv")
    # Act
    with _projects_root(tmp_path):
        text = _projects.read_data_file("cohort", "alias.csv")
    # Assert
    assert text is None


def test_listing_skips_symlinked_and_non_regular_entries(tmp_path):
    # Arrange
    project = _project_with_data(tmp_path)
    (project / "alias.csv").symlink_to(project / "measurements.csv")
    (project / "subdir.csv").mkdir()
    # Act
    with _projects_root(tmp_path):
        names = [f["name"] for f in _projects.list_data_files("cohort")]
    # Assert
    assert names == ["measurements.csv"]


def test_save_refuses_a_wrong_extension_for_the_kind(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "results", "result.png", b"x")
    # Assert
    assert saved is None


@pytest.mark.parametrize("name", [".hidden.json", "a/b.json", "a\\b.json", "x" * 65 + ".json", "..json"])
def test_save_refuses_an_out_of_policy_name(tmp_path, name):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "results", name, {"a": 1})
    # Assert
    assert saved is None


def test_save_versions_instead_of_overwriting(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        first = _projects.save_artifact("cohort", "results", "result.json", {"run": 1})
        second = _projects.save_artifact("cohort", "results", "result.json", {"run": 2})
    # Assert
    assert (first["name"], second["name"]) == ("result.json", "result.v2.json")


def test_save_does_not_follow_a_symlink_at_the_artifact_name(tmp_path):
    # Arrange: a symlink where the artifact would go, pointing OUTSIDE the project
    _project_with_data(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("untouched")
    artifact_dir = tmp_path / "cohort" / "stats" / "results"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "result.json").symlink_to(outside)
    # Act
    with _projects_root(tmp_path):
        saved = _projects.save_artifact("cohort", "results", "result.json", {"run": 1})
    # Assert
    assert saved["name"] == "result.v2.json" and outside.read_text() == "untouched"


def test_save_leaves_no_temporary_file_behind(tmp_path):
    # Arrange
    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        _projects.save_artifact("cohort", "config", "config.json", {"a": 1})
    # Assert
    leftovers = [p.name for p in (tmp_path / "cohort" / "stats" / "config").iterdir() if p.name.startswith(".")]
    assert leftovers == []


def test_save_refuses_a_foreign_project_id(tmp_path, client):  # noqa: F811
    # Arrange: the request's ACTIVE project is cohort; the body names another.
    _project_with_data(tmp_path)
    (tmp_path / "other").mkdir()
    payload = json.dumps({"project": "other", "kind": "config", "name": "config.json", "payload": {}})
    # Act
    with _projects_root(tmp_path):
        status = client.post("/api/project-save?project=cohort", data=payload, content_type="application/json").status_code
    # Assert
    assert status == 403


def test_save_refuses_with_no_active_project(tmp_path):  # noqa: F811
    # Arrange: Quick analysis = the stateless state, i.e. no active project.
    _project_with_data(tmp_path)
    from django.test import Client

    client = Client()
    payload = json.dumps({"project": "cohort", "kind": "config", "name": "config.json", "payload": {}})
    # Act
    with _projects_root(tmp_path):
        response = client.post("/api/project-save", data=payload, content_type="application/json")
    # Assert
    assert response.status_code == 403 and not (tmp_path / "cohort" / "stats").exists()


def test_save_requires_the_csrf_token(tmp_path):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    from django.test import Client

    enforcing = Client(enforce_csrf_checks=True)
    payload = json.dumps({"project": "cohort", "kind": "config", "name": "config.json", "payload": {}})
    # Act
    with _projects_root(tmp_path):
        status = enforcing.post("/api/project-save?project=cohort", data=payload, content_type="application/json").status_code
    # Assert
    assert status == 403


def test_save_accepts_the_csrf_token_the_page_carries(tmp_path):  # noqa: F811
    # Arrange
    _project_with_data(tmp_path)
    from django.test import Client

    enforcing = Client(enforce_csrf_checks=True)
    token = enforcing.get("/?project=cohort").content.decode().split('name="csrf-token" content="')[1].split('"')[0]
    payload = json.dumps({"project": "cohort", "kind": "config", "name": "config.json", "payload": {"a": 1}})
    # Act
    with _projects_root(tmp_path):
        status = enforcing.post(
            "/api/project-save?project=cohort",
            data=payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
    # Assert
    assert status == 201


def test_project_mode_hides_the_manual_data_controls():
    # Arrange: project mode imports from the PROJECT; the manual file picker and
    # sample loader belong to Quick analysis, so the mode must hide them.
    js = (
        pathlib.Path(__file__).resolve().parents[3]
        / "src/scitex_stats/_django/static/stats/js/app.js"
    ).read_text(encoding="utf-8")
    # Act
    apply_mode = js.split("function applyMode()", 1)[1].split("function setSaveStatus", 1)[0]
    # Assert
    assert "statsManualData" in apply_mode


def test_quick_mode_writes_nothing_server_side(tmp_path, client):  # noqa: F811
    # Arrange: the same body that succeeds WITH an active project.
    _project_with_data(tmp_path)
    payload = json.dumps({"project": "cohort", "kind": "results", "name": "result.json", "payload": {"run": 1}})
    # Act
    with _projects_root(tmp_path):
        quick_status = client.post("/api/project-save", data=payload, content_type="application/json").status_code
        project_status = client.post("/api/project-save?project=cohort", data=payload, content_type="application/json").status_code
    # Assert
    assert (quick_status, project_status) == (403, 201)


def test_quick_query_param_forces_stateless_mode(tmp_path, client):  # noqa: F811
    # Arrange: a project WAS visited (the provider stores it), and the page asks
    # for Quick analysis explicitly.
    root = tmp_path / "projects"
    project = root / "cohort"
    project.mkdir(parents=True)
    (project / "measurements.csv").write_text("a\n1\n")
    (root / ".scitex").mkdir()
    (root / ".scitex" / "last_project.json").write_text('{"project": "cohort"}')
    # Act
    with _projects_root(root):
        status = client.post(
            "/api/project-save?quick=1",
            data=json.dumps({"project": "cohort", "kind": "config", "name": "config.json", "payload": {}}),
            content_type="application/json",
        ).status_code
    # Assert
    assert status == 403


def test_quick_mode_hides_the_project_panel_server_side(tmp_path, client):  # noqa: F811
    # Arrange: same stored project as above.
    root = tmp_path / "projects"
    project = root / "cohort"
    project.mkdir(parents=True)
    (project / "measurements.csv").write_text("a\n1\n")
    (root / ".scitex").mkdir()
    (root / ".scitex" / "last_project.json").write_text('{"project": "cohort"}')
    # Act
    with _projects_root(root):
        html = client.get("/?quick=1").content.decode()
    # Assert
    assert "data-stats-project-panel hidden" in html and 'data-stats-project="None"' in html


# ---------------------------------------------------------------------------
# Second review round: hub-provider compatibility (detail is metadata), no-follow
# ROOT opening, exclusive version reservation, content validity, write gate.
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _write_capability(value):
    previous = os.environ.get("SCITEX_STATS_TEST_WRITE")
    os.environ["SCITEX_STATS_TEST_WRITE"] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SCITEX_STATS_TEST_WRITE", None)
        else:
            os.environ["SCITEX_STATS_TEST_WRITE"] = previous


@contextlib.contextmanager
def _cwd(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def test_hub_detail_is_metadata_and_a_same_named_directory_is_never_read(tmp_path):
    """The hub's detail is the owner's username, and a folder of that name can sit
    in the process's working directory: a relative read of it would be another
    project's files. Without a storage capability the app refuses instead."""
    # Arrange
    workdir = tmp_path / "cwd"
    (workdir / "alice").mkdir(parents=True)
    (workdir / "alice" / "decoy.csv").write_text("a\n1\n")
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    from django.test import override_settings

    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=""), _host_root(host_root), _cwd(workdir):
        without_storage = _projects.list_data_files("host-cohort")
        with override_settings(SCITEX_PROJECT_STORAGE=HOST_STORAGE_PATH):
            with_storage = _projects.list_data_files("host-cohort")
    # Assert
    assert (without_storage, [f["name"] for f in with_storage]) == (None, ["real.csv"])


def test_a_symlinked_project_root_is_refused(tmp_path):
    # Arrange: the project under the root is a symlink to a sibling project.
    root = tmp_path / "root"
    real = root / "real-cohort"
    real.mkdir(parents=True)
    (real / "secret.csv").write_text("a\n1\n")
    (root / "cohort").symlink_to(real, target_is_directory=True)
    # Act
    with _projects_root(root):
        listed = _projects.list_data_files("cohort")
        read = _projects.read_data_file("cohort", "secret.csv")
    # Assert
    assert (listed, read) == (None, None)


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 32


def test_save_refuses_bytes_that_are_not_what_the_extension_promises(tmp_path):
    # Arrange: right names, wrong bytes — text claiming to be JSON, and a PNG name
    # holding text.
    import base64

    _project_with_data(tmp_path)
    # Act
    with _projects_root(tmp_path):
        as_json = _projects.save_artifact(
            "cohort", "results", "result.json", None, payload_base64=base64.b64encode(b"not json").decode()
        )
        as_png = _projects.save_artifact(
            "cohort", "plots", "plot.png", None, payload_base64=base64.b64encode(b"just text").decode()
        )
        real_png = _projects.save_artifact(
            "cohort", "plots", "plot.png", None, payload_base64=base64.b64encode(PNG_BYTES).decode()
        )
    # Assert
    assert (as_json, as_png, real_png["name"]) == (None, None, "plot.png")


def test_save_refuses_a_name_with_no_room_for_a_version_suffix(tmp_path):
    # Arrange: 65 characters fit the pattern, but versioning would exceed the bound
    # and the SECOND save would have nowhere to go.
    _project_with_data(tmp_path)
    too_long = "r" * 55 + ".json"  # 60 characters: fits the pattern, no room to version
    fits = "r" * 54 + ".json"      # 59: ".v2" still lands inside the 64-character bound
    # Act
    with _projects_root(tmp_path):
        refused = _projects.save_artifact("cohort", "results", too_long, {"a": 1})
        first = _projects.save_artifact("cohort", "results", fits, {"a": 1})
        second = _projects.save_artifact("cohort", "results", fits, {"a": 2})
    # Assert
    assert (refused, first["name"], second["name"]) == (None, fits, "r" * 54 + ".v2.json")


def test_concurrent_saves_keep_every_payload(tmp_path):
    # Arrange: four writers race for the same artifact name, released together.
    import threading

    _project_with_data(tmp_path)
    barrier = threading.Barrier(4)
    names = []
    lock = threading.Lock()

    def writer(index):
        barrier.wait()
        saved = _projects.save_artifact("cohort", "results", "race.json", {"writer": index})
        with lock:
            names.append(saved["name"] if saved else None)

    # Act
    with _projects_root(tmp_path):
        threads = [threading.Thread(target=writer, args=(index,)) for index in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    # Assert
    directory = tmp_path / "cohort" / "stats" / "results"
    written = sorted(path.name for path in directory.iterdir())
    contents = {path.read_text() for path in directory.iterdir()}
    expected = {json.dumps({"writer": index}, indent=2, sort_keys=True) for index in range(4)}
    assert (sorted(names), written, contents == expected) == (
        ["race.json", "race.v2.json", "race.v3.json", "race.v4.json"],
        ["race.json", "race.v2.json", "race.v3.json", "race.v4.json"],
        True,
    )


def test_a_read_only_member_lists_the_project_but_cannot_save(tmp_path):
    # Arrange: the host lists the project for this caller, who may only read.
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    from django.test import override_settings

    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=HOST_STORAGE_PATH), _host_root(host_root), _write_capability("no"):
        listed = _projects.list_data_files("host-cohort")
        saved = _projects.save_artifact("host-cohort", "results", "result.json", {"a": 1})
    # Assert
    assert ([f["name"] for f in listed], saved, (host_root / "stats").exists()) == (["real.csv"], None, False)


def test_save_endpoint_refuses_a_read_only_member(tmp_path, client):  # noqa: F811
    # Arrange: the read-only caller does carry a valid CSRF token, so a refusal is
    # the write gate's, not the middleware's.
    from django.test import Client, override_settings

    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    enforcing = Client(enforce_csrf_checks=True)
    token = enforcing.get("/?project=host-cohort").content.decode().split('name="csrf-token" content="')[1].split('"')[0]
    payload = json.dumps({"project": "host-cohort", "kind": "config", "name": "config.json", "payload": {}})
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=HOST_STORAGE_PATH), _host_root(host_root), _write_capability("no"):
        status = enforcing.post(
            "/api/project-save?project=host-cohort", data=payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
    # Assert
    assert status == 403


# ---------------------------------------------------------------------------
# Third review round: fail-closed host storage, class registrations, real SVG
# validation, and no-follow at EVERY path component.
# ---------------------------------------------------------------------------


class _ReadOnlyCohortProvider:
    """Lists a single project for this caller, and nothing about writing."""

    def list_projects(self, request=None):
        return [ProjectEntry(id="cohort", name="cohort", detail="alice")]

    def last_visited(self, request=None):
        return None

    def remember(self, request, project_id):
        return None


_readonly_provider = _ReadOnlyCohortProvider()
READONLY_PROVIDER_PATH = "tests.scitex_stats._django.test__projects._readonly_provider"


class _StatefulClassStorage:
    """Registered as a CLASS (the documented form): the state only exists once
    instantiated, so handing callers the class object breaks every call."""

    def __init__(self):
        self.calls = 0

    def project_path(self, project_id, request=None):
        self.calls += 1
        return str(pathlib.Path(os.environ["SCITEX_STATS_TEST_HOST_ROOT"]))

    def can_write(self, project_id, request=None):
        return True


class _UninstantiableStorage:
    def __init__(self, required):  # no arg-free construction: a broken registration
        self.required = required

    def project_path(self, project_id, request=None):
        return None

    def can_write(self, project_id, request=None):
        return False


STATE_FUL_CLASS_PATH = "tests.scitex_stats._django.test__projects._StatefulClassStorage"
UNINSTANTIABLE_PATH = "tests.scitex_stats._django.test__projects._UninstantiableStorage"


def test_a_host_without_storage_fails_closed_instead_of_using_the_local_root(tmp_path):
    """The exact fall-through: the host lists one project, and a same-named,
    writable folder exists under the standalone root."""
    # Arrange
    local_root = tmp_path / "local"
    local_project = local_root / "cohort"
    local_project.mkdir(parents=True)
    (local_project / "local-only.csv").write_text("a\n1\n")
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    from django.test import override_settings

    # Act: host provider registered, NO storage capability of any kind.
    with override_settings(SCITEX_PROJECT_PROVIDER=READONLY_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=""), _projects_root(local_root):
        listed = _projects.list_data_files("cohort")
        saved = _projects.save_artifact("cohort", "results", "result.json", {"a": 1})
    # Assert
    assert (listed, saved, (local_project / "stats").exists()) == (None, None, False)


def test_a_storage_class_registration_is_instantiated(tmp_path):
    # Arrange: the dotted path names a class, not an instance.
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    from django.test import override_settings

    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=STATE_FUL_CLASS_PATH), _host_root(host_root):
        # Act
        capability = _projects.storage()
        listed = _projects.list_data_files("host-cohort", None)
    # Assert
    assert (type(capability).__name__, [f["name"] for f in listed]) == ("_StatefulClassStorage", ["real.csv"])


def test_an_uninstantiable_storage_registration_refuses_rather_than_crashing(tmp_path):
    # Arrange: the registered class cannot be constructed without arguments.
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / "real.csv").write_text("a\n1\n")
    from django.test import override_settings

    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HOST_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=UNINSTANTIABLE_PATH), _host_root(host_root):
        listed = _projects.list_data_files("host-cohort")
        saved = _projects.save_artifact("host-cohort", "results", "result.json", {"a": 1})
    # Assert
    assert (listed, saved) == (None, None)


def test_save_refuses_an_svg_that_does_not_parse_as_svg(tmp_path):
    # Arrange: a name that promises SVG over content that is not an SVG document.
    import base64

    _project_with_data(tmp_path)
    bad_root = base64.b64encode(b"<svg-not-svg>bad</svg-not-svg>").decode()
    bad_xml = base64.b64encode(b"<svg><unclosed>").decode()
    dtd = base64.b64encode(b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "y">]><svg>&x;</svg>').decode()
    good = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>').decode()
    # Act
    with _projects_root(tmp_path):
        wrong_root = _projects.save_artifact("cohort", "plots", "plot.svg", None, payload_base64=bad_root)
        unparsable = _projects.save_artifact("cohort", "plots", "plot.svg", None, payload_base64=bad_xml)
        with_entities = _projects.save_artifact("cohort", "plots", "plot.svg", None, payload_base64=dtd)
        valid = _projects.save_artifact("cohort", "plots", "plot.svg", None, payload_base64=good)
    # Assert
    assert (wrong_root, unparsable, with_entities, valid["name"]) == (None, None, None, "plot.svg")


def test_a_symlinked_ancestor_of_the_project_is_refused(tmp_path):
    # Arrange: the project dir is real, but the directory holding it is a symlink
    # — refusing only the last component would have followed it.
    real_parent = tmp_path / "real-parent"
    project = real_parent / "cohort"
    project.mkdir(parents=True)
    (project / "secret.csv").write_text("a\n1\n")
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    # Act
    with _projects_root(tmp_path):
        linked = _projects.list_data_files("cohort")
    # Assert
    assert linked is None


class _HubSlugProvider:
    """Hub-shaped: project ids are ``owner/slug`` and detail is display metadata."""

    def list_projects(self, request=None):
        base = pathlib.Path(os.environ["SCITEX_STATS_TEST_HUB_ROOT"])
        if not (base / "alice" / "cohort").is_dir():
            return []
        return [ProjectEntry(id="alice/cohort", name="cohort", detail="alice")]

    def last_visited(self, request=None):
        return None

    def remember(self, request, project_id):
        return None


class _HubSlugStorage:
    """The hub's write capability: it owns the owner/slug -> path mapping."""

    def project_path(self, project_id, request=None):
        owner, _, slug = str(project_id).partition("/")
        if not owner or not slug:
            return None
        base = pathlib.Path(os.environ["SCITEX_STATS_TEST_HUB_ROOT"])
        return str(base / owner / slug)

    def can_write(self, project_id, request=None):
        return os.environ.get("SCITEX_STATS_TEST_WRITE", "yes") == "yes"


_hub_provider = _HubSlugProvider()
HUB_PROVIDER_PATH = "tests.scitex_stats._django.test__projects._hub_provider"
_hub_storage = _HubSlugStorage()
HUB_STORAGE_PATH = "tests.scitex_stats._django.test__projects._hub_storage"


@contextlib.contextmanager
def _hub_root(path):
    previous = os.environ.get("SCITEX_STATS_TEST_HUB_ROOT")
    os.environ["SCITEX_STATS_TEST_HUB_ROOT"] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SCITEX_STATS_TEST_HUB_ROOT", None)
        else:
            os.environ["SCITEX_STATS_TEST_HUB_ROOT"] = previous


def test_a_hub_owner_slug_project_reads_and_writes_through_the_capability(tmp_path):
    """The real Hub shape: ids are `owner/slug`, detail is the owner, and only
    the storage capability knows the path — including for a multi-component id,
    which the standalone name policy would refuse."""
    # Arrange
    base = tmp_path / "hub"
    project = base / "alice" / "cohort"
    project.mkdir(parents=True)
    (project / "measurements.csv").write_text("a,b\n5.1,6.3\n")
    from django.test import override_settings

    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HUB_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=HUB_STORAGE_PATH), _hub_root(base):
        listed = _projects.list_data_files("alice/cohort")
        text = _projects.read_data_file("alice/cohort", "measurements.csv")
        saved = _projects.save_artifact("alice/cohort", "results", "result.json", {"a": 1})
    # Assert
    assert ([f["name"] for f in listed], text.splitlines()[0], saved["path"]) == (
        ["measurements.csv"],
        "a,b",
        "stats/results/result.json",
    )


def test_a_hub_slug_project_is_refused_by_the_endpoint_when_the_storage_says_no(tmp_path, client):  # noqa: F811
    # Arrange: the hub lists the project (read) but the capability refuses writes.
    base = tmp_path / "hub"
    (base / "alice" / "cohort").mkdir(parents=True)
    (base / "alice" / "cohort" / "measurements.csv").write_text("a,b\n5.1,6.3\n")
    from django.test import Client, override_settings

    enforcing = Client(enforce_csrf_checks=True)
    token = enforcing.get("/?project=alice%2Fcohort").content.decode().split('name="csrf-token" content="')[1].split('"')[0]
    payload = json.dumps({"project": "alice/cohort", "kind": "results", "name": "result.json", "payload": {"a": 1}})
    # Act
    with override_settings(SCITEX_PROJECT_PROVIDER=HUB_PROVIDER_PATH, SCITEX_PROJECT_STORAGE=HUB_STORAGE_PATH), _hub_root(base), _write_capability("no"):
        status = enforcing.post(
            "/api/project-save?project=alice%2Fcohort", data=payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
    # Assert
    assert status == 403


# EOF
