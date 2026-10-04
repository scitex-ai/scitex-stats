#!/usr/bin/env python3
"""Stats app report endpoints: capabilities, PDF download, Save to Files (`_django/_report_views.py`)."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_sdk")
importlib.import_module("scitex_sdk.app")
importlib.import_module("scitex_sdk.ui")

from django.test import RequestFactory, override_settings  # noqa: E402

from scitex_stats._django import _report_views  # noqa: E402
from scitex_stats.reporting._pdf import pdf_renderer  # noqa: E402

from .test_views import (  # noqa: E402,F401  (shared Django bootstrap + fixture)
    _post,
    client,
)

SAMPLE = {
    "groups": [[5.1, 4.9, 5.6, 5.8, 6.0, 5.4, 5.2, 5.7], [6.3, 6.8, 6.1, 7.0, 6.6, 6.9, 6.4, 7.2],
               [5.9, 6.2, 6.0, 5.8, 6.4, 6.1, 6.3, 6.0]],
    "group_names": ["Group 1", "Group 2", "Group 3"],
    "design": "between",
}
SAVED: dict = {}


class _User:
    is_authenticated = True
    pk = 1


def fake_save(user, filename, data):
    """Host Files service stand-in: writes the bytes where the test can read them."""
    root = Path(SAVED["root"])
    target = root / "Downloads" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def fake_root(user):
    return Path(SAVED["root"])


def _save_request(payload):
    request = RequestFactory().post("/api/report/save", data=json.dumps(payload), content_type="application/json")
    request.user = _User()
    return request


def test_capabilities_reports_pdf_availability(client):  # noqa: F811
    # Arrange
    expected = pdf_renderer() is not None
    # Act
    body = client.get("/api/report/capabilities").json()
    # Assert
    assert body["pdf"] is expected


def test_capabilities_hides_save_for_anonymous_users(client):  # noqa: F811
    # Arrange
    path = "/api/report/capabilities"
    # Act
    body = client.get(path).json()
    # Assert
    assert body["save_to_files"] is False


def test_report_pdf_needs_two_groups(client):  # noqa: F811
    # Arrange
    payload = {"groups": [[1.0, 2.0, 3.0]]}
    # Act
    resp = _post(client, "/api/report/pdf", payload)
    # Assert
    assert resp.status_code == 400


@pytest.mark.skipif(pdf_renderer() is None, reason="WeasyPrint not installed")
def test_report_pdf_returns_a_pdf_attachment(client):  # noqa: F811
    # Arrange
    payload = SAMPLE
    # Act
    resp = _post(client, "/api/report/pdf", payload)
    # Assert
    assert resp["Content-Type"] == "application/pdf" and resp.content.startswith(b"%PDF")


def test_save_refuses_anonymous_users(client):  # noqa: F811
    # Arrange
    payload = SAMPLE
    # Act
    resp = _post(client, "/api/report/save", payload)
    # Assert
    assert resp.status_code == 401


@pytest.mark.skipif(pdf_renderer() is None, reason="WeasyPrint not installed")
def test_save_writes_pdf_through_the_host_files_service(tmp_path):
    # Arrange
    SAVED["root"] = str(tmp_path)
    request = _save_request(SAMPLE)
    # Act
    with override_settings(SCITEX_APP_SAVE_TO_FILES=f"{__name__}.fake_save", SCITEX_APP_FILES_USER_ROOT=f"{__name__}.fake_root"):
        body = json.loads(_report_views.report_save(request).content)
    # Assert
    assert body["saved"].startswith("Downloads/stats-report_") and (tmp_path / body["saved"]).read_bytes().startswith(b"%PDF")


def test_save_without_host_service_is_501(tmp_path):
    # Arrange
    request = _save_request(SAMPLE)
    # Act
    with override_settings(SCITEX_APP_SAVE_TO_FILES="no.such.module.save"):
        resp = _report_views.report_save(request)
    # Assert
    assert resp.status_code == 501


def test_non_callable_host_service_is_unavailable():
    # Arrange
    request = _save_request({"groups": []})
    capabilities_request = RequestFactory().get("/api/report/capabilities")
    capabilities_request.user = _User()
    # Act
    with override_settings(SCITEX_APP_SAVE_TO_FILES=f"{__name__}.fake_save"):
        callable_service_retained = _report_views.files_saver() is fake_save
    with override_settings(SCITEX_APP_SAVE_TO_FILES=f"{__name__}.SAVED"):
        capabilities = json.loads(_report_views.report_capabilities(capabilities_request).content)
        response = _report_views.report_save(request)
    # Assert
    assert {
        "callable_service_retained": callable_service_retained,
        "save_to_files": capabilities["save_to_files"],
        "save_status": response.status_code,
    } == {"callable_service_retained": True, "save_to_files": False, "save_status": 501}


def test_unconfigured_host_does_not_discover_hub_files_service(monkeypatch):
    # Arrange
    module_path = "apps.workspace.files_app.services"
    service = ModuleType(module_path)
    service.save_to_downloads = fake_save
    monkeypatch.setitem(sys.modules, module_path, service)
    monkeypatch.setattr(_report_views, "_pdf_available", lambda: False)
    request = _save_request({"groups": []})
    capabilities_request = RequestFactory().get("/api/report/capabilities")
    capabilities_request.user = request.user
    # Act
    with override_settings(SCITEX_APP_SAVE_TO_FILES=None):
        discoverable = _report_views._import(f"{module_path}.save_to_downloads")
        capabilities = json.loads(_report_views.report_capabilities(capabilities_request).content)
        response = _report_views.report_save(request)
    # Assert
    assert {
        "hub_service_importable": discoverable is fake_save,
        "capabilities": capabilities,
        "save_status": response.status_code,
    } == {
        "hub_service_importable": True,
        "capabilities": {"pdf": False, "save_to_files": False},
        "save_status": 501,
    }


def test_explicit_host_binding_preserves_user_downloads_and_navigation(monkeypatch, tmp_path):
    # Arrange
    request = _save_request(SAMPLE)
    data = b"synthetic report bytes; no PDF renderer or scientific computation"
    calls = {}

    def save(user, filename, contents):
        calls["save"] = (user, filename, contents)
        target = tmp_path / "Downloads" / filename
        target.parent.mkdir()
        target.write_bytes(contents)
        return target

    def root(user):
        calls["root"] = user
        return tmp_path

    monkeypatch.setattr(sys.modules[__name__], "fake_save", save)
    monkeypatch.setattr(sys.modules[__name__], "fake_root", root)
    monkeypatch.setattr(_report_views, "_build_pdf", lambda body: (data, {}))
    monkeypatch.setattr(_report_views, "_filename", lambda: "fixture.pdf")
    # Act
    with override_settings(
        SCITEX_APP_SAVE_TO_FILES=f"{__name__}.fake_save",
        SCITEX_APP_FILES_USER_ROOT=f"{__name__}.fake_root",
        SCITEX_APP_FILES_URL="/portable/user-files/",
    ):
        response = _report_views.report_save(request)
    # Assert
    assert {
        "status": response.status_code,
        "body": json.loads(response.content),
        "calls": calls,
        "saved_bytes": (tmp_path / "Downloads" / "fixture.pdf").read_bytes(),
    } == {
        "status": 200,
        "body": {"saved": "Downloads/fixture.pdf", "files_url": "/portable/user-files/"},
        "calls": {"save": (request.user, "fixture.pdf", data), "root": request.user},
        "saved_bytes": data,
    }


@pytest.mark.parametrize("files_url", [None, ""])
def test_host_without_root_or_url_does_not_discover_hub_defaults(monkeypatch, tmp_path, files_url):
    # Arrange
    SAVED["root"] = str(tmp_path)
    request = _save_request(SAMPLE)
    data = b"synthetic report bytes; no PDF renderer or scientific computation"
    module_path = "apps.workspace.files_app.services"
    service = ModuleType(module_path)
    service.user_root = fake_root
    monkeypatch.setitem(sys.modules, module_path, service)
    monkeypatch.setattr(_report_views, "_build_pdf", lambda body: (data, {}))
    monkeypatch.setattr(_report_views, "_filename", lambda: "fixture.pdf")
    # Act
    with override_settings(
        SCITEX_APP_SAVE_TO_FILES=f"{__name__}.fake_save",
        SCITEX_APP_FILES_USER_ROOT=None,
        SCITEX_APP_FILES_URL=files_url,
    ):
        discoverable = _report_views._import(f"{module_path}.user_root")
        response = _report_views.report_save(request)
    # Assert
    assert {
        "hub_root_importable": discoverable is fake_root,
        "status": response.status_code,
        "body": json.loads(response.content),
        "saved_bytes": (tmp_path / "Downloads" / "fixture.pdf").read_bytes(),
    } == {
        "hub_root_importable": True,
        "status": 200,
        "body": {"saved": "fixture.pdf", "files_url": ""},
        "saved_bytes": data,
    }


# EOF
