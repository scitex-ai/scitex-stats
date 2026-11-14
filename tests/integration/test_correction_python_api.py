"""Native correction values, fallback references and actual MCP delegation."""

import asyncio
import inspect

import pytest
import scitex_stats as ss
from statsmodels.stats.multitest import multipletests

METHODS = ["bonferroni", "holm", "sidak", "fdr_bh", "fdr_by"]


@pytest.fixture
def pvalues():
    return [0.0, 0.001, 0.04, 0.03, 0.20, 0.005, 1.0]


@pytest.mark.parametrize("method", METHODS)
def test_native_correction_matches_reference_backend(pvalues, method):
    # Arrange
    reject, expected, _, _ = multipletests(pvalues, alpha=0.05, method=method)
    # Act
    result = ss.correct_pvalues(pvalues=pvalues, method=method, alpha=0.05)
    # Assert
    assert (inspect.iscoroutinefunction(ss.correct_pvalues),
            set(result) & {"success", "timestamp"}, result["corrected_pvalues"],
            result["reject_null"], result["n_significant"], result["n_tests"]) == (
                False, set(), pytest.approx(expected.tolist()), reject.tolist(),
                int(reject.sum()), len(pvalues),
            )




@pytest.mark.parametrize("method", METHODS)
def test_correction_mcp_payload_matches_native_python(pvalues, method):
    # Arrange
    from scitex_stats._mcp._handlers._corrections import correct_pvalues_handler

    expected = ss.correct_pvalues(pvalues=pvalues, method=method, alpha=0.05)
    # Act
    result = asyncio.run(correct_pvalues_handler(pvalues=pvalues, method=method, alpha=0.05))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (result["success"], payload) == (True, expected)


def test_correction_adapter_delegates_all_arguments(observe_native):
    # Arrange: observe the actual function entry; retain real calculations.
    from scitex_stats._mcp._handlers._corrections import correct_pvalues_handler

    kwargs = dict(pvalues=[0.001, 0.04, 0.2], method="holm", alpha=0.01)
    expected = ss.correct_pvalues(**kwargs)
    # Act
    with observe_native(ss.correct_pvalues) as calls:
        result = asyncio.run(correct_pvalues_handler(**kwargs))
    payload = {key: value for key, value in result.items() if key not in {"success", "timestamp"}}
    # Assert
    assert (calls, result["success"], payload) == ([kwargs], True, expected)


def test_native_correction_preserves_legacy_unknown_method_mapping(pvalues):
    # Arrange
    expected = ss.correct_pvalues(pvalues=pvalues, method="fdr_bh")
    # Act
    result = ss.correct_pvalues(pvalues=pvalues, method="unknown_method")
    # Assert
    assert (result["corrected_pvalues"], result["method"]) == (
        expected["corrected_pvalues"], "unknown_method",
    )
