#!/usr/bin/env python3
"""Tests for `scitex_stats.verify`: tamper detection and recompute."""

from __future__ import annotations

import asyncio
import copy
import json

import pytest
from click.testing import CliRunner

import scitex_stats as ss
from scitex_stats._cli.verify import verify as verify_cmd
from scitex_stats._mcp.handlers import run_test_handler, verify_result_handler
from scitex_stats._provenance import receipt_hash

X = [5.1, 4.9, 6.2, 5.8, 6.0, 5.5, 5.3, 6.1]
Y = [6.3, 6.9, 7.1, 6.5, 7.4, 6.8, 7.0, 6.6]


def _status(report):
    return {c["name"]: c["status"] for c in report["checks"]}


@pytest.fixture(scope="module")
def ttest_result():
    return ss.run_test("ttest_ind", data=X, data2=Y)


def test_verify_passes_every_check_for_untouched_result(ttest_result):
    # Arrange
    result = copy.deepcopy(ttest_result)
    # Act
    report = ss.verify(result, data=X, data2=Y)
    # Assert
    assert _status(report) == {"receipt": "pass", "result": "pass", "inputs": "pass", "recompute": "pass"}


def test_verify_uses_embedded_data_when_none_supplied():
    # Arrange
    r = ss.run_test("anova", groups=[X, Y, [5.9, 6.4, 6.1, 5.7]])
    # Act
    report = ss.verify(r)
    # Assert
    assert report["verified"] is True


def test_verify_detects_tampered_statistic_hash(ttest_result):
    # Arrange
    forged = copy.deepcopy(ttest_result)
    forged["pvalue"] = 0.001
    # Act
    report = ss.verify(forged, data=X, data2=Y)
    # Assert
    assert (report["verified"], _status(report)["result"]) == (False, "fail")


def test_verify_names_the_tampered_field(ttest_result):
    # Arrange
    forged = copy.deepcopy(ttest_result)
    forged["pvalue"] = 0.001
    # Act
    report = ss.verify(forged, data=X, data2=Y)
    # Assert
    assert [d["field"] for d in report["checks"][3]["differences"]] == ["pvalue"]


def test_verify_detects_tampered_data(ttest_result):
    # Arrange
    other = list(X)
    other[0] += 1e-12
    # Act
    report = ss.verify(ttest_result, data=other, data2=Y)
    # Assert
    assert (_status(report)["inputs"], _status(report)["recompute"]) == ("fail", "skip")


def test_verify_detects_tampered_embedded_values(ttest_result):
    # Arrange
    forged = copy.deepcopy(ttest_result)
    forged["provenance"]["inputs"]["data"]["values"][0] = 9.9
    # Act
    report = ss.verify(forged)
    # Assert
    assert (_status(report)["receipt"], _status(report)["inputs"]) == ("fail", "fail")


def test_verify_detects_edited_parameters_even_with_rehashed_receipt(ttest_result):
    # Arrange
    forged = copy.deepcopy(ttest_result)
    forged["provenance"]["test"]["parameters"]["alternative"] = "less"
    forged["provenance"]["receipt_sha256"] = receipt_hash(forged["provenance"])
    # Act
    report = ss.verify(forged, data=X, data2=Y)
    # Assert
    assert (_status(report)["receipt"], _status(report)["recompute"]) == ("pass", "fail")


def test_verify_rejects_result_without_receipt():
    # Arrange
    bare = {"statistic": 1.0, "pvalue": 0.5}
    # Act
    report = ss.verify(bare)
    # Assert
    assert (report["verified"], report["summary"]) == (False, "no provenance receipt")


def test_verify_round_trips_through_json_file(tmp_path, ttest_result):
    # Arrange
    path = tmp_path / "result.json"
    path.write_text(json.dumps(ttest_result))
    # Act
    report = ss.verify(path)
    # Assert
    assert report["verified"] is True


def test_verify_full_report_without_source_result_fails_recompute():
    # Arrange
    rep = ss.full_report(ss.run_test("mannwhitneyu", data=X, data2=Y), data=X, data2=Y, n_bootstrap=400)
    # Act
    report = ss.verify(rep)
    # Assert
    assert _status(report)["recompute"] == "fail"


def test_verify_full_report_with_source_result_passes():
    # Arrange
    base = ss.run_test("mannwhitneyu", data=X, data2=Y)
    rep = ss.full_report(base, data=X, data2=Y, n_bootstrap=400)
    # Act
    report = ss.verify(rep, source_result=base)
    # Assert
    assert report["verified"] is True


@pytest.fixture(scope="module")
def mcp_nan_result():
    return asyncio.run(run_test_handler(test_name="ttest_ind", data=[X + [float("nan")], Y]))


def test_mcp_run_test_reports_nan_exclusion(mcp_nan_result):
    # Arrange
    ii = mcp_nan_result["input_integrity"]
    # Act
    excluded = ii["inputs"]["data[0]"]["n_excluded"]
    # Assert
    assert excluded == 1


def test_mcp_verify_result_passes_for_mcp_result(mcp_nan_result):
    # Arrange
    data = [X + [float("nan")], Y]
    # Act
    report = asyncio.run(verify_result_handler(result=mcp_nan_result, data=data))
    # Assert
    assert (report["success"], report["verified"]) == (True, True)


def test_mcp_verify_result_detects_tampering():
    # Arrange
    r = asyncio.run(run_test_handler(test_name="pearson", data=[X, Y]))
    r["statistic"] = 0.99
    # Act
    report = asyncio.run(verify_result_handler(result=r))
    # Assert
    assert report["verified"] is False


def test_cli_verify_exits_zero_when_verified(tmp_path, ttest_result):
    # Arrange
    path = tmp_path / "good.json"
    path.write_text(json.dumps(ttest_result))
    # Act
    out = CliRunner().invoke(verify_cmd, [str(path)])
    # Assert
    assert (out.exit_code, json.loads(out.stdout)["verified"]) == (0, True)


def test_cli_verify_exits_one_when_tampered(tmp_path, ttest_result):
    # Arrange
    forged = copy.deepcopy(ttest_result)
    forged["statistic"] = 0.0
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(forged))
    # Act
    out = CliRunner().invoke(verify_cmd, [str(path), "--no-json"])
    # Assert
    assert (out.exit_code, "NOT verified" in out.output) == (1, True)


@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("ttest_rel", {"data": X, "data2": Y}),
        ("kendall", {"data": X, "data2": Y}),
        ("friedman", {"groups": [X, Y, [6.0, 5.2, 6.6, 6.1, 7.0, 6.2, 5.9, 6.8]]}),
        ("fisher", {"groups": [[8, 2], [1, 5]]}),
        ("shapiro", {"data": X + Y}),
        ("ttest_1samp", {"data": X, "popmean": 5.0}),
    ],
)
def test_verify_covers_each_dispatch_family(name, kwargs):
    # Arrange
    r = ss.run_test(name, **kwargs)
    # Act
    report = ss.verify(r)
    # Assert
    assert report["verified"] is True, report
