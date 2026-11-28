#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/test___init__.py
"""The stats plugin: contract, operation table, import safety, real HTTP."""

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from scitex_sdk.app.api_ops import operations
from scitex_sdk.testing.api_contract import assert_contract

from scitex_stats._rest import PLUGIN


def test_the_plugin_meets_the_api_contract():
    # Arrange: the contract probes a host with no public tier (anonymous -> 401).
    from django.test import override_settings

    target = "scitex_stats._rest:PLUGIN"
    # Act
    with override_settings(SCITEX_API_PUBLIC_TIER={}):
        outcome = assert_contract(PLUGIN, target=target)
    # Assert
    assert outcome is None


def test_every_calculation_is_public_eligible():
    # Arrange
    ops = operations(PLUGIN)
    # Act
    exposures = {op.exposure for op in ops}
    # Assert
    assert exposures == {"public_eligible"}


def test_only_the_catalogue_is_callable_without_a_tier():
    # Arrange
    ops = operations(PLUGIN)
    # Act
    public = sorted(op.operation_id for op in ops if op.public)
    # Assert
    assert public == ["stats.tests.get", "stats.tests.list"]


def test_every_post_is_a_read_only_calculation():
    # Arrange
    ops = [op for op in operations(PLUGIN) if op.method == "POST"]
    # Act
    scopes = {op.scope.rsplit(":", 1)[-1] for op in ops}
    # Assert
    assert scopes == {"read"}


def test_no_operation_answers_with_a_job():
    # Arrange
    ops = operations(PLUGIN)
    # Act
    asynchronous = [op.operation_id for op in ops if op.is_async]
    # Assert
    assert asynchronous == []


def test_importing_the_package_does_not_load_the_api_module():
    # Arrange
    code = "import sys, scitex_stats; print('scitex_stats._rest' in sys.modules)"
    # Act
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    # Assert
    assert out.stdout.strip() == "False"


def test_the_entry_point_names_the_plugin():
    # Arrange
    from importlib.metadata import entry_points

    # Act
    found = {ep.name: ep.value for ep in entry_points(group="scitex.apis")}
    # Assert
    assert found.get("stats") == "scitex_stats._rest:PLUGIN"


# ------------------------------------------------------------------ real HTTP
# An anonymous public-class call over a real socket (wsgiref + urllib).


class _Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def base_url():
    from django.core.handlers.wsgi import WSGIHandler

    server = make_server("127.0.0.1", 0, WSGIHandler(), handler_class=_Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api/v1/stats"
    server.shutdown()


def _post(url, body):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), json.loads(exc.read())


def test_an_anonymous_test_run_over_http_is_public_class(base_url):
    # Arrange
    body = {"data": [5.1, 4.9, 5.6, 5.8], "data2": [6.3, 6.8, 6.1, 7.0]}
    # Act
    status, headers, payload = _post(f"{base_url}/tests/ttest_ind/run", body)
    # Assert
    assert (
        status,
        headers["SciTeX-Priority-Class"],
        payload["data"]["test"] != "",
    ) == (
        200,
        "public",
        True,
    )


def test_an_oversized_anonymous_call_over_http_is_a_413(base_url):
    # Arrange
    body = {"data": [1.0] * 100_001}
    # Act
    status, headers, payload = _post(f"{base_url}/descriptives/run", body)
    # Assert
    assert (status, headers["Content-Type"], payload["code"]) == (
        413,
        "application/problem+json",
        "stats.too_many_values",
    )


# EOF
