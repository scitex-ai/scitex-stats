#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/test__http.py
"""An anonymous public-class call over a real socket (wsgiref + urllib)."""

import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest


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
