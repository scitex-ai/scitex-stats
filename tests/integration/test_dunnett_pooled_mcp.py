"""Compare the conservative pooled-t approximation with independent OLS contrasts."""

import asyncio
import copy
from datetime import datetime
import json
import re

import numpy as np
import pytest
from statsmodels.regression.linear_model import OLS

from scitex_stats import _server
from scitex_stats.posthoc import posthoc_dunnett

A = [[1., 2., 4., 8., 9.], [3., 4., 5., 7.], [5., 8., 9., 15., 17., 21.]]
B = [[-3., 0., 1., 2.], [1., 3., 7.], [2., 4., 5., 8., 11.], [0., 4., 9., 10., 12., 16.]]
CASES = [(A, 0), (A, 1), (A, 2), (B, 0), (B, 2), ([A[0], A[1]], 0), ([[2.], [3., 4., 6.]], 0)]
INVALID = [([[], [1., 2.]], "nonempty finite one-dimensional"),
           ([[1., 2.], []], "nonempty finite one-dimensional"),
           ([[1., float("nan")], [2., 4.]], "nonempty finite one-dimensional"),
           ([[1., 2.], [2., float("inf")]], "nonempty finite one-dimensional"),
           ([[[1., 2.], [3., 4.]], [1., 2., 3.]], "nonempty finite one-dimensional"),
           ([[1.], [2.]], "positive residual degrees of freedom"),
           ([[1., 1.], [2., 2.]], "positive pooled variance")]


def references(groups, control, alternative="two-sided"):
    design = np.repeat(np.eye(len(groups)), [len(group) for group in groups], axis=0)
    fit = OLS(np.concatenate(groups), design).fit()
    rows = []
    for i in range(len(groups)):
        if i == control:
            continue
        contrast = np.eye(len(groups))[i] - np.eye(len(groups))[control]
        result = fit.t_test(contrast, use_t=True)
        effect = float(np.asarray(result.effect).item())
        statistic = float(np.asarray(result.tvalue).item())
        raw = float(np.asarray(result.pvalue).item())
        if alternative == "greater":
            raw = raw / 2 if statistic >= 0 else 1 - raw / 2
        elif alternative == "less":
            raw = raw / 2 if statistic <= 0 else 1 - raw / 2
        rows.append((i, effect, statistic, raw, min(raw * (len(groups) - 1), 1.)))
    return rows


def call_tool(groups, control=0):
    function = getattr(_server.posthoc_test, "fn", _server.posthoc_test)
    return json.loads(asyncio.run(function(groups=groups, method="dunnett", control_group=control)))


@pytest.mark.parametrize("groups, control", CASES)
def test_mcp_dunnett_uses_unrounded_global_pooled_contrasts(groups, control):
    # Arrange
    before = copy.deepcopy(groups)
    expected = references(groups, control)
    keys = {"group", "vs_control", "mean_diff", "t_statistic", "p_value", "p_adj", "reject"}
    # Act
    report = call_tool(groups, control)
    timestamp = datetime.fromisoformat(report["timestamp"])
    observed = [(row["group"], row["vs_control"], row["mean_diff"], row["t_statistic"], row["p_value"], row["p_adj"], row["reject"]) for row in report["comparisons"]]
    wanted = [(f"Group_{i+1}", f"Group_{control+1}", pytest.approx(diff, abs=1e-12),
               pytest.approx(t, rel=1e-11, abs=1e-12), pytest.approx(raw, rel=1e-10, abs=1e-12),
               pytest.approx(adj, rel=1e-10, abs=1e-12), bool(adj < .05)) for i, diff, t, raw, adj in expected]
    # Assert
    assert (report["success"], report["n_comparisons"], observed, all(set(row) == keys for row in report["comparisons"]),
            isinstance(timestamp, datetime), groups) == (True, len(groups)-1, wanted, True, True, before)


@pytest.mark.parametrize("groups, control", CASES)
@pytest.mark.parametrize("alternative", ["two-sided", "greater", "less"])
def test_native_dunnett_keeps_rounded_pooled_reference_results(groups, control, alternative):
    # Arrange
    expected = references(groups, control, alternative)
    treatments = [group for i, group in enumerate(groups) if i != control]
    # Act
    rows = posthoc_dunnett(groups[control], treatments, alternative=alternative, return_as="dict")
    observed = [(row["mean_diff"], row["t_statistic"], row["pvalue"], row["significant"]) for row in rows]
    # Assert
    assert observed == [(round(diff, 3), round(t, 3), round(adj, 4), bool(adj < .05)) for _, diff, t, _, adj in expected]


@pytest.mark.parametrize("groups, message", INVALID)
def test_native_dunnett_rejects_unsupported_sample_geometry(groups, message):
    # Arrange
    kwargs = {"control": groups[0], "treatments": groups[1:], "return_as": "dict"}
    # Act
    with pytest.raises(ValueError, match=message):
        # Assert
        posthoc_dunnett(**kwargs)


@pytest.mark.parametrize("groups, message", INVALID)
def test_mcp_dunnett_reports_unsupported_sample_geometry(groups, message):
    # Arrange
    # Act
    report = call_tool(groups)
    # Assert
    assert (set(report), report.get("success"), bool(re.search(message, report.get("error", "")))) == ({"success", "error"}, False, True)


def test_identical_constant_groups_preserve_native_zero_difference_policy():
    # Arrange
    groups = [[5., 5., 5.], [5., 5., 5.]]
    native = posthoc_dunnett(groups[0], groups[1:], return_as="dict")[0]
    # Act
    report = call_tool(groups)
    row = report["comparisons"][0]
    # Assert
    assert (native["t_statistic"], native["pvalue"], native["significant"], row["t_statistic"], row["p_adj"], row["reject"]) == (0., 1., False, 0., 1., False)


@pytest.mark.parametrize("groups, control", CASES)
def test_mcp_calls_native_unrounded_core_in_worker(groups, control, observe_native):
    # Arrange
    from importlib import import_module

    operation = import_module("scitex_stats.posthoc._dunnett")._dunnett_statistics
    # Act
    with observe_native(operation) as calls:
        report = call_tool(groups, control)
    observed = [(call["control"].tolist(), [group.tolist() for group in call["treatments"]], call["alternative"]) for call in calls]
    # Assert
    assert (report["success"], observed) == (True, [(groups[control], [group for i, group in enumerate(groups) if i != control], "two-sided")])
