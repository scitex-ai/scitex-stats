"""Public API discovery must not enumerate an imported dependency's API."""

from __future__ import annotations

import importlib
from types import ModuleType

import pytest

introspect = importlib.import_module("scitex_stats._cli.introspect")


@pytest.fixture
def public_package():
    """An owned module, lazy external backend and explicit callable re-export."""
    reads = []
    backend = ModuleType("external_backend")
    backend.__all__ = ["expensive"]

    def resolve(name):
        reads.append(name)
        return lambda: None

    backend.__getattr__ = resolve
    own = ModuleType("sample_package.methods")
    own.run = lambda: None
    own.__all__ = ["run"]
    root = ModuleType("sample_package")
    root.__all__ = ["backend", "methods", "public_mean"]
    root.backend = backend
    root.methods = own
    root.public_mean = lambda: None
    root.public_mean.__module__ = "external_backend"
    return root, backend, reads


def test_dependency_module_is_not_enumerated(public_package):
    # Arrange
    root, _, reads = public_package
    # Act
    introspect._get_api_tree(root)
    # Assert
    assert reads == []


def test_explicit_dependency_module_remains_a_public_entry(public_package):
    # Arrange
    root, _, _ = public_package
    # Act
    tree = introspect._get_api_tree(root)
    # Assert
    assert {"Name": "sample_package.backend", "Type": "M", "Depth": 1} in tree


def test_owned_submodule_public_members_remain_discoverable(public_package):
    # Arrange
    root, _, _ = public_package
    # Act
    names = {row["Name"] for row in introspect._get_api_tree(root)}
    # Assert
    assert "sample_package.methods.run" in names


def test_explicit_callable_reexport_remains_discoverable(public_package):
    # Arrange
    root, _, _ = public_package
    # Act
    names = {row["Name"] for row in introspect._get_api_tree(root)}
    # Assert
    assert "sample_package.public_mean" in names


def test_dependency_can_be_introspected_when_explicitly_requested(public_package):
    # Arrange
    _, backend, _ = public_package
    # Act
    names = {row["Name"] for row in introspect._get_api_tree(backend)}
    # Assert
    assert "external_backend.expensive" in names
