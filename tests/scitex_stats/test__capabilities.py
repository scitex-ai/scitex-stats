"""Check source capability bindings and references against actual native APIs."""

import importlib
import inspect
import json
from pathlib import Path

import pytest

from scitex_stats._capabilities import get_capabilities

NAMES = ("normality_test", "effect_size", "format_results", "correct_pvalues",
         "check_applicability", "recommend_test", "run_all_applicable", "validate_apa", "verify", "recommend_tests", "p_to_stars")
ROOT = Path(__file__).resolve().parents[2]


def operation(name):
    return next(item for item in get_capabilities()["capabilities"] if item["name"] == name)


def test_declaration_identifies_the_partial_core_operation_scope():
    # Arrange
    payload = get_capabilities()
    # Act
    identity = (payload["schema_version"], payload["distribution"], payload["provider"],
                {item["name"] for item in payload["capabilities"]})
    # Assert
    assert identity == (1, "scitex-stats", "core-operations", set(NAMES))


def test_declaration_roundtrips_as_plain_json_data():
    # Arrange
    payload = get_capabilities()
    # Act
    decoded = json.loads(json.dumps(payload))
    # Assert
    assert decoded == payload


def test_factory_results_do_not_share_mutable_declarations():
    # Arrange
    first = get_capabilities()
    first["distribution"] = "changed"
    first["capabilities"][0]["python"].append("changed")
    # Act
    second = get_capabilities()
    # Assert
    assert (second["distribution"], second["capabilities"][0]["python"]) == (
        "scitex-stats", ["scitex_stats.normality_test"])


@pytest.mark.parametrize("name", NAMES)
def test_declared_native_binding_is_a_synchronous_public_operation(name):
    # Arrange
    item = operation(name)
    module, _, attribute = item["python"][0].rpartition(".")
    # Act
    function = getattr(importlib.import_module(module), attribute)
    # Assert
    assert (item["python"], callable(function), inspect.iscoroutinefunction(function)) == (
        [f"scitex_stats.{name}"], True, False)


@pytest.mark.parametrize("name", NAMES)
def test_declared_purpose_has_owned_existing_test_references(name):
    # Arrange
    item = operation(name)
    # Act
    references = [(ROOT / value).resolve() for value in item["test_references"]]
    # Assert
    assert item["purpose"].strip() and references and all(
        path.is_relative_to(ROOT) and path.is_file() for path in references)
