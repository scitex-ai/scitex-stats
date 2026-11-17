"""Native power analysis is synchronous and shares MCP domain behavior."""

import asyncio
import inspect
import json
import os
import subprocess
import sys

import pytest

import scitex_stats as stats
from scitex_stats._mcp._handlers._power import power_analysis_handler


def _native():
    native = getattr(stats, "power_analysis", None)
    assert callable(native), "The native power_analysis counterpart must exist"
    return native


@pytest.mark.parametrize("method", ["ttest", "anova", "correlation", "chi2"])
@pytest.mark.parametrize("n", [None, 40])
def test_native_and_mcp_share_all_method_results(method, n):
    # Arrange
    native = _native()
    arguments = dict(test_type=method, effect_size=.3, n=n, n_groups=3)
    # Act
    result = native(**arguments)
    wire = asyncio.run(power_analysis_handler(**arguments))
    # Assert
    assert not inspect.isawaitable(result)
    assert wire.pop("success") is True
    assert isinstance(wire.pop("timestamp"), str)
    assert result == wire
    assert result["test_type"] == method
    assert result["mode"] == ("power_calculation" if n else "sample_size_calculation")
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("arguments,message", [
    ({"test_type": "unknown", "effect_size": .3}, "Unknown test_type"),
    ({"test_type": "ttest"}, "Either n or effect_size"),
    ({"test_type": "anova"}, "effect_size"),
    ({"test_type": "chi2"}, "effect_size"),
    ({"test_type": "correlation"}, "effect_size"),
    ({"test_type": "anova", "effect_size": .001}, "1000"),
    ({"test_type": "chi2", "effect_size": .001}, "10000"),
    ({"test_type": "anova", "effect_size": .3, "power": 1.}, "target power"),
    ({"test_type": "chi2", "effect_size": .3, "power": 0.}, "target power"),
])
def test_native_raises_while_mcp_retains_error_envelope(arguments, message):
    # Arrange
    native = _native()
    # Act / Assert
    with pytest.raises(ValueError, match=message):
        native(**arguments)
    wire = asyncio.run(power_analysis_handler(**arguments))
    assert wire["success"] is False and message in wire["error"]


def test_root_and_power_namespace_expose_one_synchronous_function():
    # Arrange
    native = _native()
    # Act / Assert
    assert stats.power.power_analysis is native
    assert "power_analysis" in stats.__all__
    assert "power_analysis" in stats.power.__all__
    assert not inspect.iscoroutinefunction(native)


def test_native_power_does_not_load_mcp_transport_in_a_real_process():
    # Arrange
    script = """import json,sys
from scitex_stats import power_analysis
r=power_analysis(test_type='anova',effect_size=10,n_groups=3)
assert r['required_n_per_group']==2
assert not any(n=='scitex_stats._mcp' or n.startswith('scitex_stats._mcp.') for n in sys.modules)
print(json.dumps({'native':True,'transport_loaded':False}))
"""
    # Act
    result = subprocess.run([sys.executable, "-c", script], env=dict(os.environ),
                            text=True, capture_output=True, check=True, timeout=30)
    # Assert
    assert json.loads(result.stdout) == {"native": True, "transport_loaded": False}
