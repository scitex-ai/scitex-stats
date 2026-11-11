"""API discovery and NumPy use must not initialize the optional tensor engine."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture(scope="module")
def numpy_only_discovery():
    """Execute real API discovery with tensor imports observed and unavailable."""
    code = textwrap.dedent("""
        import contextlib
        import importlib.abc
        import io
        import json
        import sys

        attempted = []
        class TensorImportObserver(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "torch" or fullname.startswith("torch."):
                    attempted.append(fullname)
                    raise ImportError("NumPy-only discovery fixture")
        sys.meta_path.insert(0, TensorImportObserver())

        from scitex_stats._cli.introspect import cmd_list_python_apis
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cmd_list_python_apis(as_json=True)
        import numpy as np
        from scitex_stats.descriptive import mean
        value = mean(np.array([[1.0, 2.0]]), dim=-1)
        print(json.dumps({
            "exit_code": code,
            "attempted": attempted,
            "names": [row["Name"] for row in json.loads(output.getvalue())],
            "mean": value.tolist(),
        }))
    """)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(result.stdout)


def test_discovery_does_not_attempt_tensor_import(numpy_only_discovery):
    # Arrange
    observed = numpy_only_discovery
    # Act
    imports = observed["attempted"]
    # Assert
    assert imports == []


def test_discovery_keeps_descriptive_public_api(numpy_only_discovery):
    # Arrange
    observed = numpy_only_discovery
    # Act
    names = observed["names"]
    # Assert
    assert "scitex_stats.descriptive.mean" in names


def test_numpy_computation_works_without_tensor_engine(numpy_only_discovery):
    # Arrange
    observed = numpy_only_discovery
    # Act
    value = observed["mean"]
    # Assert
    assert value == [1.5]
