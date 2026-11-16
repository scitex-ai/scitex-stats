"""Numerical/input contracts for real native correction backends."""

import asyncio
import inspect
from functools import partial

import numpy as np
import pytest

from scitex_stats._mcp._handlers._corrections import correct_pvalues_handler

REFERENCES = {
    "bonferroni": [0.03, 0.12, 0.09],
    "holm": [0.03, 0.06, 0.06],
    "fdr_bh": [0.03, 0.04, 0.04],
    "fdr_by": [0.055, 0.07333333333333333, 0.07333333333333333],
    "sidak": [0.029701, 0.115264, 0.087327],
}


@pytest.fixture(params=["statsmodels", "numpy"])
def correction(request):
    """Select real backends, including the retained backend-free path."""
    from scitex_stats import correct_pvalues
    from scitex_stats.correct._correct_pvalues import _correct_pvalues

    operations = {
        "statsmodels": correct_pvalues,
        "numpy": partial(
            _correct_pvalues, method="fdr_bh", alpha=0.05, use_statsmodels=False
        ),
    }
    return operations[request.param]


@pytest.mark.parametrize("method,expected", REFERENCES.items())
def test_native_method_result_contract(correction, method, expected):
    # Arrange
    values = [0.01, 0.04, 0.03]
    flags = [value <= 0.05 for value in expected]
    # Act
    result = correction(values, method=method)
    # Assert
    assert result == {
        "method": method,
        "method_used": method,
        "alpha": 0.05,
        "original_pvalues": values,
        "corrected_pvalues": pytest.approx(expected, abs=1e-12),
        "reject_null": flags,
        "n_significant": sum(flags),
        "n_tests": 3,
    }


def test_public_operation_is_synchronous():
    # Arrange
    from scitex_stats import correct_pvalues

    # Act
    asynchronous = inspect.iscoroutinefunction(correct_pvalues)
    # Assert
    assert asynchronous is False


@pytest.mark.parametrize(
    "pvalues", [[], [float("nan")], [float("inf")], [-0.1], [1.1], [[0.1, 0.2]]]
)
def test_native_rejects_invalid_pvalues(correction, pvalues):
    # Arrange
    # Act
    # Assert
    with pytest.raises(ValueError):
        correction(pvalues)


@pytest.mark.parametrize(
    "pvalues", [[], [float("nan")], [float("inf")], [-0.1], [1.1], [[0.1, 0.2]]]
)
def test_transport_rejects_invalid_pvalues(pvalues):
    # Arrange
    request = correct_pvalues_handler(pvalues)
    # Act
    result = asyncio.run(request)
    # Assert
    assert (result["success"], bool(result["error"])) == (False, True)


@pytest.mark.parametrize("alpha", [-0.1, 1.1, float("nan"), float("inf")])
def test_native_rejects_invalid_alpha(correction, alpha):
    # Arrange
    values = [0.01, 0.02]
    # Act
    # Assert
    with pytest.raises(ValueError):
        correction(values, alpha=alpha)


def test_unknown_method_preserves_fallback_and_names_actual_method(correction):
    # Arrange
    values = [0.01, 0.04, 0.03]
    # Act
    result = correction(values, method="legacy-typo")
    # Assert
    assert (result["method"], result["method_used"], result["corrected_pvalues"]) == (
        "legacy-typo",
        "fdr_bh",
        pytest.approx([0.03, 0.04, 0.04]),
    )


def test_endpoint_pvalues_are_supported(correction):
    # Arrange
    values = [0.0, 1.0]
    # Act
    result = correction(values, method="sidak")
    # Assert
    assert result["corrected_pvalues"] == [0.0, 1.0]


def test_input_array_bytes_are_preserved(correction):
    # Arrange
    values = np.array([0.01, 0.04, 0.03])
    before = values.tobytes()
    # Act
    correction(values)
    # Assert
    assert values.tobytes() == before


@pytest.mark.parametrize("alpha,count", [(0.0, 1), (1.0, 3)])
def test_alpha_endpoints_remain_accepted(correction, alpha, count):
    # Arrange
    values = [0.0, 0.5, 1.0]
    # Act
    result = correction(values, alpha=alpha)
    # Assert
    assert result["n_significant"] == count


@pytest.mark.parametrize("alpha", [-0.1, 1.1, float("nan"), float("inf")])
def test_transport_rejects_invalid_alpha(alpha):
    # Arrange
    request = correct_pvalues_handler([0.01, 0.02], alpha=alpha)
    # Act
    result = asyncio.run(request)
    # Assert
    assert (result["success"], bool(result["error"])) == (False, True)
