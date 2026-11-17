"""Explicit native post-hoc dispatch shares its domain behavior with MCP."""

import asyncio
import inspect
import json
import os
import subprocess
import sys
from copy import deepcopy

import pytest

import scitex_stats as stats
from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

GROUPS = [[1., 2., 4., 5.], [3., 5., 7., 9., 10.], [7., 8., 10., 13.]]
METHODS = ["tukey", "dunnett", "games_howell", "dunn"]


def _native():
    native = getattr(stats, "posthoc_test", None)
    assert callable(native), "The native posthoc_test counterpart must exist"
    return native


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("names", [None, ["Z", "A", "M"]])
def test_native_and_mcp_share_methods_labels_and_numerical_results(method, names):
    # Arrange
    native = _native()
    groups = deepcopy(GROUPS)
    before = deepcopy(groups)
    # Act
    result = native(groups, group_names=names, method=method)
    wire = asyncio.run(posthoc_test_handler(groups, group_names=names, method=method))
    success, timestamp = wire.pop("success"), wire.pop("timestamp")
    json.dumps(result, allow_nan=False)
    # Assert
    assert {"payload": result, "method": result["method"],
            "success": success, "timestamp": isinstance(timestamp, str),
            "synchronous": not inspect.isawaitable(result),
            "input_preserved": groups == before,
            "n_groups": result["n_groups"], "n_comparisons": result["n_comparisons"]} == {
        "payload": wire, "method": method, "success": True, "timestamp": True,
        "synchronous": True, "input_preserved": True, "n_groups": 3,
        "n_comparisons": 2 if method == "dunnett" else 3,
    }


INVALID = [({"method": method, "group_names": names}, "group_names")
           for method in METHODS for names in [["A", "A", "C"], ["A", "B"]]] + [
    ({"method": "dunnett", "control_group": -1}, "control_group"),
    ({"method": "dunnett", "control_group": 3}, "control_group"),
    ({"method": "unknown"}, "Unknown method"),
    ({"method": "games_howell", "groups": [[1., 1.], [2., 2.]]}, "constant"),
    ({"method": "dunn", "groups": [[1., 1.], [1., 1.]]}, "variance"),
]


@pytest.mark.parametrize("overrides,message", INVALID)
def test_native_errors_preserve_mcp_failure_contract(overrides, message):
    # Arrange
    native = _native()
    arguments = {"groups": deepcopy(GROUPS), **overrides}
    failure = None
    # Act
    try:
        native(**arguments)
    except Exception as error:
        failure = error
    wire = asyncio.run(posthoc_test_handler(**arguments))
    # Assert
    assert {"type": type(failure), "message": message in str(failure),
            "wire_error": wire["success"] is False and message in wire["error"]} == {
        "type": ValueError, "message": True, "wire_error": True,
    }


def test_root_and_posthoc_namespace_expose_one_native_function():
    # Arrange
    native = _native()
    # Act
    exposure = {"same_native": stats.posthoc.posthoc_test is native,
                "root_export": "posthoc_test" in stats.__all__,
                "posthoc_export": "posthoc_test" in stats.posthoc.__all__,
                "synchronous": not inspect.iscoroutinefunction(native)}
    # Assert
    assert exposure == dict.fromkeys(exposure, True)


def test_native_posthoc_runs_without_mcp_transport_in_a_real_process():
    # Arrange
    script = """import json,sys
from scitex_stats import posthoc_test
r=posthoc_test([[1.,2.,4.],[3.,5.,7.],[6.,8.,10.]],method='dunn')
assert r['n_comparisons']==3
assert not any(n=='scitex_stats._mcp' or n.startswith('scitex_stats._mcp.') for n in sys.modules)
print(json.dumps({'native':True,'transport_loaded':False}))
"""
    # Act
    result = subprocess.run([sys.executable, "-c", script], env=dict(os.environ),
                            text=True, capture_output=True, check=True, timeout=30)
    # Assert
    assert json.loads(result.stdout) == {"native": True, "transport_loaded": False}
