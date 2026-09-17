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

from .test_views import client  # noqa: E402,F401  (shared Django bootstrap + fixture)

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


# EOF
