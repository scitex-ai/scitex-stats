#!/usr/bin/env python3
# File: tests/scitex_stats/_rest/test___init__.py
"""The stats plugin declaration: contract, operation table, import safety."""

import subprocess
import sys

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


# EOF
