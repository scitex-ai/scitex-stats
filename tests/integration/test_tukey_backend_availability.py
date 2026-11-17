"""Unavailable Tukey HSD must not silently become a different procedure."""

import asyncio
import json
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

import scitex_stats
from scitex_stats._mcp._handlers._posthoc import posthoc_test_handler

GROUPS = [[1, 2, 4, 5, 7], [0, 3, 6, 9, 12, 15], [2, 3, 4, 6, 8, 10, 13]]


def _dependency_directory(path, missing):
    """Link real installed dependencies into an owned incomplete environment."""
    path.mkdir()
    for entry in Path(sysconfig.get_path("purelib")).iterdir():
        if entry.name == "statsmodels":
            if missing == "statsmodels.sandbox":
                package = path / entry.name
                package.mkdir()
                for member in entry.iterdir():
                    if member.name != "sandbox":
                        (package / member.name).symlink_to(member)
            continue
        (path / entry.name).symlink_to(entry)
    return path


@pytest.mark.parametrize("missing", ["statsmodels", "statsmodels.sandbox"])
def test_real_backend_import_failure_returns_an_explicit_method_error(tmp_path, missing):
    # Arrange: -S disables global site paths; the owned directory has real deps.
    dependencies = _dependency_directory(tmp_path / "dependencies", missing)
    source = Path(scitex_stats.__file__).resolve().parent.parent
    script = '''import sys,json,asyncio
sys.path[:0]=sys.argv[1:3]
from scitex_stats._mcp._handlers._posthoc import _tukey_hsd,posthoc_test_handler
import numpy as np
groups=json.loads(sys.argv[3]);missing=None
try:
 _tukey_hsd([np.array(g,dtype=float) for g in groups],['A','B','C'])
except ImportError as error:
 missing=getattr(error.__cause__,'name',None)
result=asyncio.run(posthoc_test_handler(groups,['A','B','C'],'tukey'))
print(json.dumps({'missing':missing,'result':result}))
'''
    # Act
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, str(source),
         str(dependencies), json.dumps(GROUPS)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    payload = json.loads(completed.stdout)
    result = payload["result"]
    # Assert
    assert {"exit": completed.returncode, "missing": payload["missing"],
            "success": result["success"], "method_in_error": "Tukey" in result.get("error", ""),
            "comparisons": "comparisons" in result} == {
        "exit": 0, "missing": missing, "success": False,
        "method_in_error": True, "comparisons": False,
    }


def test_available_tukey_retains_reference_values_and_result_contract():
    # Arrange: independent SciPy1.18.1 reference before presentation rounding.
    groups = [list(group) for group in GROUPS]
    # Act
    result = asyncio.run(posthoc_test_handler(groups, ["A", "B", "C"], "tukey"))
    # Assert
    assert {"success": result["success"], "method": result["method"],
            "p": [row["p_adj"] for row in result["comparisons"]],
            "boolean_decisions": [type(row["reject"]) is bool for row in result["comparisons"]],
            "inputs_unchanged": groups == GROUPS} == {
        "success": True, "method": "tukey", "p": pytest.approx([0.3539129796144884, 0.5266372523778904,
                             0.9203741958565332], rel=1e-10, abs=1e-12),
        "boolean_decisions": [True] * 3, "inputs_unchanged": True,
    }
