#!/usr/bin/env python3
"""Stats app report endpoints: capabilities, PDF download, Save to Files (`_django/_report_views.py`)."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

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


def _host_probe(tmp_path, probe):
    """Run the actual leaf with an importable filesystem host service fixture."""
    services = tmp_path / "apps" / "workspace" / "files_app" / "services.py"
    services.parent.mkdir(parents=True)
    services.write_text(
        "from pathlib import Path\n"
        "def user_root(user):\n"
        "    return Path(__file__).parent\n"
        "def save_to_downloads(user, filename, data):\n"
        "    target = user_root(user) / 'Downloads' / filename\n"
        "    target.parent.mkdir(exist_ok=True)\n"
        "    target.write_bytes(data)\n"
        "    return target\n"
    )
    env = dict(os.environ)
    # Preserve the caller's PYTHONPATH AFTER the fixture entries. Release CI
    # layers every dependency (--target) on the parent PYTHONPATH only, so
    # dropping it here starves the subprocess (no django) while venv-installed
    # CI stays green. The fixture tmp stays first, so the fixture `apps`
    # package still wins over anything importable behind it.
    entries = [str(tmp_path), str(Path(_report_views.__file__).resolve().parents[2])]
    if os.environ.get("PYTHONPATH"):
        entries.append(os.environ["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(entries)
    script = (
        "import json\n"
        "from django.conf import settings\n"
        "settings.configure(SECRET_KEY='fixture', USE_I18N=False)\n"
        "from django.test import RequestFactory, override_settings\n"
        "from scitex_stats._django import _report_views\n"
        "from apps.workspace.files_app import services\n"
        "class User:\n"
        "    is_authenticated = True\n"
        "user = User()\n"
        + probe
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True,
        check=True, timeout=30,
    )
    return json.loads(result.stdout)


def recording_save(user, filename, data):
    SAVED["save"] = (user, filename, data)
    return fake_save(user, filename, data)


def recording_root(user):
    SAVED["root_user"] = user
    return fake_root(user)


def test_unconfigured_host_does_not_discover_hub_files_service(tmp_path):
    # Arrange
    probe = (
        "request = RequestFactory().post('/api/report/save', data=json.dumps({'groups': []}), content_type='application/json')\n"
        "request.user = user\n"
        "capabilities_request = RequestFactory().get('/api/report/capabilities')\n"
        "capabilities_request.user = user\n"
        "with override_settings(SCITEX_APP_SAVE_TO_FILES=None):\n"
        "    discoverable = _report_views._import('apps.workspace.files_app.services.save_to_downloads')\n"
        "    capabilities = json.loads(_report_views.report_capabilities(capabilities_request).content)\n"
        "    response = _report_views.report_save(request)\n"
        "print(json.dumps({'hub_service_importable': discoverable is services.save_to_downloads, 'save_to_files': capabilities['save_to_files'], 'save_status': response.status_code}))\n"
    )
    # Act
    observations = _host_probe(tmp_path, probe)
    # Assert
    assert observations == {
        "hub_service_importable": True, "save_to_files": False, "save_status": 501,
    }


def test_explicit_host_binding_preserves_user_downloads_and_navigation(tmp_path):
    # Arrange
    SAVED["root"] = str(tmp_path)
    user = _User()
    data = b"synthetic report bytes; no PDF renderer or scientific computation"
    # Act
    with override_settings(
        SCITEX_APP_SAVE_TO_FILES=f"{__name__}.recording_save",
        SCITEX_APP_FILES_USER_ROOT=f"{__name__}.recording_root",
        SCITEX_APP_FILES_URL="/portable/user-files/",
    ):
        response = _report_views._save_to_files(user, _report_views.files_saver(), "fixture.pdf", data)
    # Assert
    assert {
        "status": response.status_code,
        "body": json.loads(response.content),
        "save_call": SAVED["save"],
        "root_user": SAVED["root_user"],
        "saved_bytes": (tmp_path / "Downloads" / "fixture.pdf").read_bytes(),
    } == {
        "status": 200,
        "body": {"saved": "Downloads/fixture.pdf", "files_url": "/portable/user-files/"},
        "save_call": (user, "fixture.pdf", data),
        "root_user": user,
        "saved_bytes": data,
    }


@pytest.mark.parametrize("files_url", [None, ""])
def test_host_without_root_or_url_does_not_discover_hub_defaults(tmp_path, files_url):
    # Arrange
    probe = (
        "data = b'synthetic document bytes'\n"
        "with override_settings(SCITEX_APP_SAVE_TO_FILES='apps.workspace.files_app.services.save_to_downloads', SCITEX_APP_FILES_USER_ROOT=None, SCITEX_APP_FILES_URL=" + repr(files_url) + "):\n"
        "    discoverable = _report_views._import('apps.workspace.files_app.services.user_root')\n"
        "    response = _report_views._save_to_files(user, _report_views.files_saver(), 'fixture.pdf', data)\n"
        "print(json.dumps({'hub_root_importable': discoverable is services.user_root, 'status': response.status_code, 'body': json.loads(response.content), 'saved_bytes_equal': (services.user_root(user) / 'Downloads' / 'fixture.pdf').read_bytes() == data}))\n"
    )
    # Act
    observations = _host_probe(tmp_path, probe)
    # Assert
    assert observations == {
        "hub_root_importable": True,
        "status": 200,
        "body": {"saved": "fixture.pdf", "files_url": ""},
        "saved_bytes_equal": True,
    }


# EOF
